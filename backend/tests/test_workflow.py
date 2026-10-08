import pytest

from app.ai.models import LLMResponse, ProviderError
from app.assessment.service import DomainError
from app.db import models as m
from app.schemas.assessment import ManagerRequest
from app.workflows.process_claim import process_claim


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claim_id,status,action",
    [
        ("CLM-001", "pending_manager_review", "create_review_task"),
        ("CLM-002", "pending_manager_review", "create_review_task"),
        ("CLM-003", "pending_manager_review", "create_review_task"),
    ],
)
async def test_workflows(service, settings, claim_id, status, action):
    result = await process_claim(service, claim_id, 1, settings)
    assert result["status"] == status
    assert result["version"] == 2
    assert result["executions"][0]["trajectory"] == [
        "get_claim",
        "get_policy",
        "get_evidence",
        "calculate_policy_checks",
        "get_previous_outcomes",
        "assess",
        action,
    ]
    assert result["history"]
    with pytest.raises(DomainError):
        await process_claim(service, claim_id, 1, settings)
    assert len(service.list_reviews()) == 1


@pytest.mark.asyncio
async def test_manager_review_memory(service, settings):
    claim = await process_claim(service, "CLM-003", 1, settings)
    task = claim["review"]
    result = service.manager_decision(
        task["id"],
        ManagerRequest(
            expected_version=2,
            decision="accept",
            rationale="Verified original receipt in person",
        ),
        "manager-1",
        "run-2",
    )
    assert result["claim"]["status"] == "accepted"
    assert len(result["decisions"]) == 1
    assert result["claim"]["outcome"]["reviewed"]
    assert service.repo.find_previous_outcomes("travel", "other")[0].reviewer_rationale
    with pytest.raises(DomainError):
        service.manager_decision(
            task["id"],
            ManagerRequest(
                expected_version=4, decision="reject", rationale="Repeated action"
            ),
            "manager-1",
            "run-3",
        )


@pytest.mark.asyncio
async def test_stale(service, settings):
    service.claim("CLM-001").title = "Changed"
    service.repo.commit()
    with pytest.raises(DomainError):
        await process_claim(service, "CLM-001", 1, settings)
    assert service.claim("CLM-001").status == "submitted"


class Invalid:
    async def generate(self, request):
        return LLMResponse(
            content='{"recommendation":"accept"}', provider="mock", model="invalid"
        )


class Unavailable:
    async def generate(self, request):
        raise ProviderError("unavailable")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", [Invalid(), Unavailable()])
async def test_failed_model(service, settings, provider):
    with pytest.raises(DomainError):
        await process_claim(service, "CLM-001", 1, settings, provider=provider)
    detail = service.detail("CLM-001")
    assert (
        detail["status"] == "submitted"
        and detail["assessment"] is None
        and detail["review"] is None
    )
    assert detail["executions"][0]["status"] == "failed"


class Unsafe:
    async def generate(self, request):
        import json

        return LLMResponse(
            content=json.dumps(
                dict(
                    recommendation="accept",
                    confidence=1.0,
                    findings=["receipt_required"],
                    evidence_ids=[],
                    unresolved_questions=[],
                    explanation="Accept without receipt",
                )
            ),
            provider="mock",
            model="unsafe",
        )


@pytest.mark.asyncio
async def test_unsafe_accept_routes_to_review(service, settings):
    result = await process_claim(service, "CLM-003", 1, settings, provider=Unsafe())
    assert result["status"] == "pending_manager_review"


@pytest.mark.asyncio
async def test_duplicate_review_db_constraint(service, settings):
    from sqlalchemy.exc import IntegrityError

    result = await process_claim(service, "CLM-003", 1, settings)
    task = result["review"]
    service.repo.add(
        m.ReviewTask(
            claim_id="CLM-003",
            assessment_id=task["assessment_id"],
            reason="Repeated",
            evidence_ids=[],
            unresolved_questions=[],
        )
    )
    with pytest.raises(IntegrityError):
        service.repo.commit()
    service.repo.rollback()
    assert len(service.list_reviews()) == 1


async def test_manager_reject(service, settings):
    claim = await process_claim(service, "CLM-003", 1, settings)
    result = service.manager_decision(
        claim["review"]["id"],
        ManagerRequest(
            expected_version=2,
            decision="reject",
            rationale="No evidence available after clarification",
        ),
        "manager-1",
        "review-run",
    )
    assert result["claim"]["outcome"]["final_decision"] == "rejected"
    assert result["claim"]["outcome"]["reviewed"]
    assert not result["active"]


async def test_memory_retrieved_through_agent_tool(service, settings):
    from datetime import date
    from decimal import Decimal

    claim = await process_claim(service, "CLM-003", 1, settings)
    service.manager_decision(
        claim["review"]["id"],
        ManagerRequest(
            expected_version=2,
            decision="accept",
            rationale="Original taxi receipt inspected",
        ),
        "manager-1",
        "review-run",
    )
    service.repo.add(
        m.Claim(
            id="CLM-NEXT",
            employee_id="employee-1",
            policy_id="expense-policy",
            title="Another taxi",
            amount=Decimal("40"),
            submitted_date=date.today(),
            currency="USD",
            status="submitted",
        )
    )
    service.repo.flush()
    service.repo.add(
        m.ClaimLine(
            id="CLM-NEXT-line",
            claim_id="CLM-NEXT",
            category="travel",
            description="Taxi",
            amount=Decimal("40"),
            expense_date=date.today(),
        )
    )
    service.repo.commit()
    from app.ai.providers.mock import MockProvider

    class RememberingProvider(MockProvider):
        async def generate(self, request):
            assert (
                request.context["previous_outcomes"][0]["reviewer_rationale"]
                == "Original taxi receipt inspected"
            )
            assert (
                request.context["previous_outcomes"][0]["final_decision"] == "accepted"
            )
            return await super().generate(request)

    result = await process_claim(
        service, "CLM-NEXT", 1, settings, provider=RememberingProvider()
    )
    # A prior exception cannot remove the current claim's receipt requirement.
    assert result["status"] == "pending_manager_review"
