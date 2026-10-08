from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.assessment.service import DomainError
from app.jobs import worker


async def test_worker_offline_is_explicit(monkeypatch):
    pool = SimpleNamespace(
        exists=AsyncMock(return_value=False),
        aclose=AsyncMock(),
        enqueue_job=AsyncMock(),
    )
    monkeypatch.setattr(worker, "queue_pool", AsyncMock(return_value=pool))
    with pytest.raises(DomainError, match="worker is offline"):
        await worker.enqueue_batch(["CLM-001"])
    pool.enqueue_job.assert_not_called()
    pool.aclose.assert_awaited_once()


async def test_batches_are_retryable_and_deduplicate_inputs(monkeypatch):
    async def enqueue(*args, **kwargs):
        return SimpleNamespace(job_id=kwargs["_job_id"])

    pool = SimpleNamespace(
        exists=AsyncMock(return_value=True),
        aclose=AsyncMock(),
        enqueue_job=AsyncMock(side_effect=enqueue),
    )
    monkeypatch.setattr(worker, "queue_pool", AsyncMock(return_value=pool))
    first = await worker.enqueue_batch(["CLM-001", "CLM-001"])
    second = await worker.enqueue_batch(["CLM-001"])
    assert len(first["jobs"]) == 1
    assert first["jobs"][0]["job_id"] != second["jobs"][0]["job_id"]


async def test_status_does_not_expose_exception_details(monkeypatch):
    pool = SimpleNamespace(exists=AsyncMock(return_value=True), aclose=AsyncMock())
    monkeypatch.setattr(worker, "queue_pool", AsyncMock(return_value=pool))

    class Job:
        def __init__(self, *args, **kwargs):
            pass

        async def result_info(self):
            return SimpleNamespace(
                success=False, result=RuntimeError("secret driver data")
            )

    monkeypatch.setattr(worker, "Job", Job)
    result = await worker.batch_status(["assess:batch:CLM-001"])
    assert result["jobs"][0]["status"] == "failed"
    assert "secret" not in result["jobs"][0]["error"]
    assert result["jobs"][0]["result"] is None


async def test_recovers_jobs_submitted_by_older_ui(monkeypatch):
    pool = SimpleNamespace(
        zrange=AsyncMock(
            return_value=[b"assess:CLM-001", b"assess:batch:CLM-003", b"other-job"]
        ),
        exists=AsyncMock(return_value=True),
        aclose=AsyncMock(),
    )
    monkeypatch.setattr(worker, "queue_pool", AsyncMock(return_value=pool))

    class Job:
        def __init__(self, job_id, *args, **kwargs):
            self.job_id = job_id

        async def info(self):
            return SimpleNamespace(
                function="assess_claim", args=[self.job_id.rsplit(":", 1)[1]]
            )

    monkeypatch.setattr(worker, "Job", Job)
    result = await worker.active_jobs()
    assert result["worker_available"]
    assert result["jobs"] == [
        {"job_id": "assess:CLM-001", "claim_id": "CLM-001"},
        {"job_id": "assess:batch:CLM-003", "claim_id": "CLM-003"},
    ]
