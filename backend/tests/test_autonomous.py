import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.ai.models import LLMResponse
from app.ai.providers.mock import MockProvider
from app.assessment.service import DomainError
from app.db import models as m
from app.jobs import worker
from app.workflows.process_claim import process_claim


@pytest.mark.parametrize(
    "claim_id,expected",
    [
        ("CLM-001", "accepted"),
        ("CLM-002", "rejected"),
        ("CLM-003", "rejected"),
        ("CLM-004", "accepted"),
        ("CLM-005", "accepted"),
        ("CLM-006", "rejected"),
        ("CLM-007", "rejected"),
    ],
)
async def test_ai_investigates_then_decides_without_review(
    service, settings, claim_id, expected
):
    settings.decision_mode = "autonomous"
    result = await process_claim(service, claim_id, 1, settings)
    assert result["status"] == expected
    assert result["assessment"]["data"]["recommendation"] in ("accept", "reject")
    assert result["assessment"]["data"]["investigation"]["summary"]
    assert result["review"] is None
    assert service.list_reviews() == []
    assert result["outcome"]["final_decision"] == expected
    assert result["executions"][0]["trajectory"][-3:] == [
        "investigate_claim",
        "assess",
        "accept_claim" if expected == "accepted" else "reject_claim",
    ]
    assert any(
        e["event_type"] == "ai_investigation_completed" for e in result["history"]
    )
    assert any(
        e["event_type"] == "autonomous_decision_recorded" for e in result["history"]
    )


class ForcedAcceptance(MockProvider):
    async def generate(self, request):
        response = await super().generate(request)
        data = json.loads(response.content)
        data.update(recommendation="accept", confidence=0.99)
        if request.context.get("task") == "investigation":
            data["limitations"] = []
        else:
            data["unresolved_questions"] = []
        return LLMResponse(
            content=json.dumps(data), provider="mock", model=request.model
        )


async def test_investigator_cannot_invent_missing_receipt(service, settings):
    settings.decision_mode = "autonomous"
    result = await process_claim(
        service, "CLM-003", 1, settings, provider=ForcedAcceptance()
    )
    assert result["status"] == "rejected"
    assert "receipt" in result["assessment"]["data"]["explanation"].lower()
    assert result["assessment"]["data"]["evidence_ids"] == []
    assert result["review"] is None


async def test_low_confidence_does_not_create_human_review(service, settings):
    settings.decision_mode = "autonomous"

    class Uncertain(MockProvider):
        async def generate(self, request):
            response = await super().generate(request)
            data = json.loads(response.content)
            data["confidence"] = 0.2
            response.content = json.dumps(data)
            return response

    result = await process_claim(service, "CLM-001", 1, settings, provider=Uncertain())
    assert result["status"] == "rejected"
    assert "confidence" in result["assessment"]["data"]["explanation"]
    assert result["review"] is None


async def test_invalid_investigation_leaves_claim_undecided(service, settings):
    settings.decision_mode = "autonomous"

    class Invalid(MockProvider):
        async def generate(self, request):
            return LLMResponse(
                content='{"findings":["invented"]}',
                provider="mock",
                model=request.model,
            )

    with pytest.raises(DomainError):
        await process_claim(service, "CLM-001", 1, settings, provider=Invalid())
    result = service.detail("CLM-001")
    assert result["status"] == "submitted"
    assert result["assessment"] is None and result["outcome"] is None
    assert result["executions"][0]["status"] == "failed"


async def test_changed_source_is_not_decided_by_old_investigation(service, settings):
    settings.decision_mode = "autonomous"

    class Changing(MockProvider):
        async def generate(self, request):
            response = await super().generate(request)
            if request.context.get("task") == "investigation":
                evidence = service.repo.get(m.Evidence, "CLM-001-receipt")
                evidence.verified = False
                service.repo.commit()
            return response

    with pytest.raises(DomainError):
        await process_claim(service, "CLM-001", 1, settings, provider=Changing())
    assert service.detail("CLM-001")["outcome"] is None


async def test_existing_human_review_is_resolved_by_ai(service, settings):
    legacy = await process_claim(service, "CLM-003", 1, settings)
    settings.decision_mode = "autonomous"
    result = await process_claim(service, "CLM-003", legacy["version"], settings)
    assert result["status"] == "rejected"
    assert result["review"] is None
    review = service.review_detail(legacy["review"]["id"])
    assert not review["active"]
    assert review["decisions"][-1]["actor"] == "ai_investigator"


async def test_auto_scan_enqueues_versioned_jobs_without_run_button(
    service, settings, monkeypatch
):
    settings.decision_mode = "autonomous"
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(service.repo.session.bind)
    )
    pool = SimpleNamespace(enqueue_job=AsyncMock(return_value=object()))
    monkeypatch.setattr(
        worker,
        "Job",
        lambda *args, **kwargs: SimpleNamespace(
            result_info=AsyncMock(return_value=None)
        ),
    )
    result = await worker.scan_claims({"redis": pool})
    assert result["enqueued"] == 7
    ids = [call.kwargs["_job_id"] for call in pool.enqueue_job.call_args_list]
    assert len(set(ids)) == 7
    assert f"assess:auto:{settings.arq_queue_name}:CLM-003:v1" in ids


async def test_human_decision_endpoint_is_disabled(service, settings, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.main import app

    legacy = await process_claim(service, "CLM-003", 1, settings)
    settings.decision_mode = "autonomous"
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    app.dependency_overrides[routes.service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/reviews/{legacy['review']['id']}/decisions",
                headers={"X-Role": "manager"},
                json={
                    "expected_version": 2,
                    "decision": "accept",
                    "rationale": "Manual acceptance",
                },
            )
        assert response.status_code == 409
        assert service.claim("CLM-003").status == "pending_manager_review"
    finally:
        app.dependency_overrides.clear()


async def test_week4_evals_are_binary_and_guard_invalid_outputs():
    from app.evaluation.autonomous import run_autonomous_evaluation

    report = await run_autonomous_evaluation()
    assert report["passed"] == report["total"] == 10


async def test_failed_auto_job_retries_after_cooldown_without_hot_loop(
    service, settings, monkeypatch
):
    settings.decision_mode = "autonomous"
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(service.repo.session.bind)
    )
    pool = SimpleNamespace(
        enqueue_job=AsyncMock(return_value=None),
        ttl=AsyncMock(return_value=86400),
        expire=AsyncMock(),
    )
    monkeypatch.setattr(
        worker,
        "Job",
        lambda *args, **kwargs: SimpleNamespace(
            result_info=AsyncMock(return_value=SimpleNamespace(success=False))
        ),
    )
    result = await worker.scan_claims({"redis": pool})
    assert result["enqueued"] == 0
    assert pool.expire.await_count == 7
    assert all(c.args[1] == 300 for c in pool.expire.call_args_list)
    assert all(settings.arq_queue_name in c.args[0] for c in pool.expire.call_args_list)
    pool.ttl.return_value = 240
    pool.expire.reset_mock()
    await worker.scan_claims({"redis": pool})
    pool.expire.assert_not_awaited()


async def test_recurring_scan_detects_claims_arriving_after_startup(
    service, settings, monkeypatch
):
    settings.decision_mode = "autonomous"
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(service.repo.session.bind)
    )
    monkeypatch.setattr(
        worker,
        "Job",
        lambda *args, **kwargs: SimpleNamespace(
            result_info=AsyncMock(return_value=None)
        ),
    )
    seen = set()

    async def enqueue(*args, **kwargs):
        key = kwargs["_job_id"]
        if key in seen:
            return None
        seen.add(key)
        return object()

    pool = SimpleNamespace(enqueue_job=AsyncMock(side_effect=enqueue))
    assert (await worker.scan_claims({"redis": pool}))["enqueued"] == 7
    service.repo.add(
        m.Claim(
            id="CLM-008",
            employee_id="employee-1",
            policy_id="expense-policy",
            title="New expense",
            amount=25,
            submitted_date=service.claim("CLM-001").submitted_date,
            currency="USD",
            status="submitted",
        )
    )
    service.repo.commit()
    assert (await worker.scan_claims({"redis": pool}))["enqueued"] == 1
    assert (await worker.scan_claims({"redis": pool}))["enqueued"] == 0


async def test_auto_job_ids_are_isolated_between_queues(service, settings, monkeypatch):
    settings.decision_mode = "autonomous"
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(service.repo.session.bind)
    )
    monkeypatch.setattr(
        worker,
        "Job",
        lambda *args, **kwargs: SimpleNamespace(
            result_info=AsyncMock(return_value=None)
        ),
    )
    pool = SimpleNamespace(enqueue_job=AsyncMock(return_value=object()))
    await worker.scan_claims({"redis": pool})
    first = {c.kwargs["_job_id"] for c in pool.enqueue_job.call_args_list}
    pool.enqueue_job.reset_mock()
    settings.arq_queue_name = "separate-week4-test"
    await worker.scan_claims({"redis": pool})
    second = {c.kwargs["_job_id"] for c in pool.enqueue_job.call_args_list}
    assert not first & second


async def test_autonomous_memory_does_not_depend_on_human_reviews(service, settings):
    settings.decision_mode = "autonomous"
    await process_claim(service, "CLM-001", 1, settings)
    outcomes = service.get_previous_outcomes("CLM-007", autonomous=True)
    assert outcomes[0]["claim_id"] == "CLM-001"
    assert not outcomes[0]["reviewed"]
    assert service.get_previous_outcomes("CLM-007") == []
