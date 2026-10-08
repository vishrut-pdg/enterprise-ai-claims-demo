from uuid import uuid4

from arq import Retry, create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

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
    from app.evaluation.suite import run_suite

    return await run_suite()


async def queue_pool():
    settings = get_settings()
    redis = RedisSettings.from_dsn(settings.redis_url)
    redis.conn_retries = 1
    redis.conn_timeout = 2
    return await create_pool(redis, default_queue_name=settings.arq_queue_name)


async def enqueue_batch(claim_ids):
    if not claim_ids or len(claim_ids) > 100:
        raise DomainError("Batch must contain 1 to 100 claim IDs", 422)
    pool = None
    try:
        pool = await queue_pool()
        if not await pool.exists(get_settings().arq_queue_name + ":health-check"):
            raise DomainError(
                "Assessment worker is offline. Start the ARQ worker, then retry batch processing. Use the demo launcher to start the API and worker together.",
                503,
            )
        batch_id = str(uuid4())
        jobs = []
        for claim_id in dict.fromkeys(claim_ids):
            job_id = f"assess:{batch_id}:{claim_id}"
            job = await pool.enqueue_job(
                "assess_claim",
                claim_id,
                correlation_id.get() or batch_id,
                _job_id=job_id,
            )
            if job is None:
                raise DomainError("Unable to queue assessment; refresh and retry.", 503)
            jobs.append({"claim_id": claim_id, "job_id": job.job_id})
        return {"batch_id": batch_id, "jobs": jobs}
    except DomainError:
        raise
    except Exception as exc:
        raise DomainError(
            "Background queue unavailable. Check Redis and restart the demo launcher.",
            503,
        ) from exc
    finally:
        if pool:
            await pool.aclose()


async def active_jobs():
    pool = None
    try:
        pool = await queue_pool()
        jobs = []
        for raw in await pool.zrange(get_settings().arq_queue_name, 0, 99):
            job_id = raw.decode() if isinstance(raw, bytes) else raw
            if not job_id.startswith("assess:"):
                continue
            info = await Job(
                job_id, pool, _queue_name=get_settings().arq_queue_name
            ).info()
            if info and info.function == "assess_claim" and info.args:
                jobs.append({"job_id": job_id, "claim_id": info.args[0]})
        return {
            "jobs": jobs,
            "worker_available": bool(
                await pool.exists(get_settings().arq_queue_name + ":health-check")
            ),
        }
    except Exception as exc:
        raise DomainError(
            "Unable to connect to the assessment queue. Check Redis and the demo launcher.",
            503,
        ) from exc
    finally:
        if pool:
            await pool.aclose()


async def batch_status(job_ids):
    if (
        not job_ids
        or len(job_ids) > 100
        or any(
            not job_id.startswith("assess:") or len(job_id) > 150 for job_id in job_ids
        )
    ):
        raise DomainError("Invalid batch job identifiers", 422)
    pool = None
    try:
        pool = await queue_pool()
        jobs = []
        for job_id in dict.fromkeys(job_ids):
            job = Job(job_id, pool, _queue_name=get_settings().arq_queue_name)
            result = await job.result_info()
            if result:
                jobs.append(
                    {
                        "job_id": job_id,
                        "status": "succeeded" if result.success else "failed",
                        "result": result.result
                        if result.success and isinstance(result.result, dict)
                        else None,
                        "error": None
                        if result.success
                        else "Assessment failed. Open the claim processing history, then start another batch for submitted claims.",
                    }
                )
            else:
                status = await job.status()
                jobs.append(
                    {
                        "job_id": job_id,
                        "status": status.value,
                        "result": None,
                        "error": "Job expired or is no longer available. Refresh the queue and retry."
                        if status.value == "not_found"
                        else None,
                    }
                )
        return {
            "jobs": jobs,
            "worker_available": bool(
                await pool.exists(get_settings().arq_queue_name + ":health-check")
            ),
        }
    except DomainError:
        raise
    except Exception as exc:
        raise DomainError(
            "Unable to read batch progress. Check Redis and refresh.", 503
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
    queue_name = get_settings().arq_queue_name
    health_check_interval = 5
    max_jobs = 2
    keep_result = 86400
    max_tries = 3
    job_timeout = 180
