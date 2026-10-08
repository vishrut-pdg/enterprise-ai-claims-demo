"""Opt-in integration tests use an isolated PostgreSQL schema, never demo data."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.ai.providers.mock import MockProvider
from app.assessment.service import ClaimService, DomainError
from app.db.models import Base
from app.db.repositories.claims import ClaimRepository
from app.seed import seed
from app.workflows.process_claim import process_claim


@pytest.fixture
def postgres_engine():
    url = os.environ.get("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TEST_POSTGRES_URL to run isolated PostgreSQL checks")
    schema = "test_claims_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text("CREATE SCHEMA " + schema))
    engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text("DROP SCHEMA " + schema + " CASCADE"))
        admin.dispose()


class Rendezvous(MockProvider):
    def __init__(self):
        self.count = 0
        self.ready = asyncio.Event()

    async def generate(self, request):
        self.count += 1
        if self.count == 2:
            self.ready.set()
        await asyncio.wait_for(self.ready.wait(), 5)
        return await super().generate(request)


@pytest.mark.parametrize(
    "claim_id,expected_status",
    [("CLM-001", "accepted"), ("CLM-003", "pending_manager_review")],
)
async def test_concurrent_processing(
    postgres_engine, settings, claim_id, expected_status
):
    provider = Rendezvous()

    async def process():
        with Session(postgres_engine, expire_on_commit=False) as session:
            service = ClaimService(ClaimRepository(session))
            return await process_claim(
                service, claim_id, 1, settings, provider=provider
            )

    results = await asyncio.gather(process(), process(), return_exceptions=True)
    assert sum(isinstance(result, DomainError) for result in results) == 1
    success = next(result for result in results if isinstance(result, dict))
    assert success["status"] == expected_status
    with Session(postgres_engine) as session:
        service = ClaimService(ClaimRepository(session))
        assert len(service.list_reviews()) == (1 if claim_id == "CLM-003" else 0)
        detail = service.detail(claim_id)
        assert len(detail["executions"]) == 2
        assert {e["status"] for e in detail["executions"]} == {"succeeded", "failed"}


async def test_arq_batch_job(postgres_engine, settings, monkeypatch):
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("Set TEST_REDIS_URL to verify real ARQ execution")
    from arq import create_pool
    from arq.connections import RedisSettings
    from arq.worker import Worker

    from app.jobs import worker as jobs

    monkeypatch.setattr(
        jobs, "SessionLocal", lambda: Session(postgres_engine, expire_on_commit=False)
    )
    monkeypatch.setattr(jobs, "get_settings", lambda: settings)
    queue = "test-claims-" + uuid4().hex
    pool = await create_pool(
        RedisSettings.from_dsn(redis_url), default_queue_name=queue
    )
    job = await pool.enqueue_job("assess_claim", "CLM-001")
    worker = Worker(
        functions=[jobs.assess_claim],
        redis_pool=pool,
        queue_name=queue,
        burst=True,
        handle_signals=False,
    )
    try:
        await worker.async_run()
        result = await job.result(timeout=5)
        assert result == {"claim_id": "CLM-001", "status": "accepted"}
        assert worker.jobs_complete == 1 and worker.jobs_failed == 0
        await pool.delete("arq:result:" + job.job_id)
    finally:
        await worker.close()
