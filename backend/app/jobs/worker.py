from uuid import uuid4

from arq import Retry, create_pool
from arq.connections import RedisSettings

from app.assessment.service import ClaimService, DomainError
from app.config import get_settings
from app.db.repositories.claims import ClaimRepository
from app.db.session import SessionLocal
from app.telemetry import configure, correlation_id
from app.workflows.process_claim import process_claim


async def assess_claim(ctx, claim_id, run_id=None):
    with SessionLocal() as session:
        svc = ClaimService(ClaimRepository(session))
        claim = svc.claim(claim_id)
        if claim.status != "submitted":
            return {"claim_id": claim_id, "status": claim.status}
        try:
            result = await process_claim(
                svc, claim_id, claim.version, get_settings(), run_id=run_id
            )
            return {"claim_id": claim_id, "status": result["status"]}
        except DomainError as exc:
            if exc.status == 502 and ctx["job_try"] < 3:
                raise Retry(defer=10 * ctx["job_try"]) from exc
            raise


async def evaluate(ctx):
    from app.evaluation.run import run_evaluation

    return await run_evaluation()


async def enqueue_batch(claim_ids):
    if not claim_ids or len(claim_ids) > 100:
        raise DomainError("Batch must contain 1 to 100 claim IDs", 422)
    pool = None
    try:
        pool = await create_pool(
            RedisSettings.from_dsn(get_settings().redis_url),
            default_queue_name="claims",
        )
        jobs = []
        for claim_id in dict.fromkeys(claim_ids):
            job = await pool.enqueue_job(
                "assess_claim",
                claim_id,
                correlation_id.get() or str(uuid4()),
                _job_id="assess:" + claim_id,
            )
            jobs.append(
                {
                    "claim_id": claim_id,
                    "job_id": job.job_id if job else "already_enqueued",
                }
            )
        return {"jobs": jobs}
    except Exception as exc:
        raise DomainError(
            "Background queue unavailable; synchronous processing remains available",
            503,
        ) from exc
    finally:
        if pool:
            await pool.aclose()


async def startup(ctx):
    configure(get_settings())


class WorkerSettings:
    on_startup = startup
    functions = [assess_claim, evaluate]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    queue_name = "claims"
    max_tries = 3
    job_timeout = 180
