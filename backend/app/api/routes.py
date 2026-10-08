from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.assessment.service import ClaimService, DomainError
from app.config import get_settings
from app.db.repositories.claims import ClaimRepository
from app.db.session import get_session
from app.schemas.assessment import ManagerRequest, ProcessRequest
from app.telemetry import correlation_id
from app.workflows.process_claim import process_claim

router = APIRouter(prefix="/api")


def service(session: Annotated[Session, Depends(get_session)]):
    return ClaimService(ClaimRepository(session))


Service = Annotated[ClaimService, Depends(service)]


def analyst(x_role: str = Header(default="analyst")):
    if x_role not in ("analyst", "manager"):
        raise DomainError("Analyst or manager role required", 403)


def manager(
    x_role: str = Header(default="analyst"),
    x_actor: str = Header(default="local-manager"),
):
    if x_role != "manager":
        raise DomainError("Manager role required", 403)
    if not x_actor.strip():
        raise DomainError("Reviewer identity required", 422)
    return x_actor


@router.get("/claims", dependencies=[Depends(analyst)])
def claims(svc: Service):
    return svc.list_claims()


@router.get("/claims/{claim_id}", dependencies=[Depends(analyst)])
def detail(claim_id: str, svc: Service):
    return svc.detail(claim_id)


@router.post("/claims/{claim_id}/process", dependencies=[Depends(analyst)])
async def process(claim_id: str, request: ProcessRequest, svc: Service):
    return await process_claim(
        svc, claim_id, request.expected_version, get_settings(), correlation_id.get()
    )


@router.get("/claims/{claim_id}/memory", dependencies=[Depends(analyst)])
def memory(claim_id: str, svc: Service):
    return svc.get_previous_outcomes(claim_id)


@router.get("/reviews", dependencies=[Depends(analyst)])
def reviews(svc: Service):
    return svc.list_reviews()


@router.get("/reviews/{review_id}", dependencies=[Depends(analyst)])
def review_detail(review_id: str, svc: Service):
    return svc.review_detail(review_id)


@router.post("/reviews/{review_id}/decisions")
def decision(
    review_id: str,
    request: ManagerRequest,
    svc: Service,
    actor: Annotated[str, Depends(manager)],
):
    return svc.manager_decision(review_id, request, actor, correlation_id.get())


@router.post("/jobs/assess", dependencies=[Depends(analyst)], status_code=202)
async def batch(request: list[str]):
    from app.jobs.worker import enqueue_batch

    return await enqueue_batch(request)


@router.get("/health")
def health():
    return {"status": "ok", "provider": get_settings().llm_provider}
