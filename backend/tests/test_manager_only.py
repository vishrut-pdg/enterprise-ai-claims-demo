"""Week 2: AI advice never changes a claim into a final decision."""

import pytest
from pydantic import ValidationError

from app.assessment.service import DomainError
from app.db import models as m
from app.schemas.assessment import ManagerRequest
from app.workflows.process_claim import process_claim


@pytest.mark.parametrize(
    "claim_id,recommendation",
    [
        ("CLM-001", "accept"),
        ("CLM-002", "reject"),
        ("CLM-003", "reject"),
        ("CLM-004", "accept"),
        ("CLM-005", "accept"),
        ("CLM-006", "reject"),
        ("CLM-007", "reject"),
    ],
)
async def test_every_claim_requires_manager_even_if_policy_allows_auto(
    service, settings, claim_id, recommendation
):
    policy = service.repo.get(m.Policy, "expense-policy")
    policy.auto_accept = policy.auto_reject = True
    service.repo.commit()
    result = await process_claim(service, claim_id, 1, settings)
    assert result["assessment"]["data"]["recommendation"] == recommendation
    assert result["status"] == "pending_manager_review"
    assert result["review"]["active"]
    assert result["outcome"] is None
    assert result["executions"][0]["trajectory"][-1] == "create_review_task"
    assert not any(
        e["event_type"]
        in ("claim_accepted", "claim_rejected", "investigation_task_created")
        for e in result["history"]
    )
    # The manager can disagree with either recommendation.
    decision = "reject" if recommendation == "accept" else "accept"
    final = service.manager_decision(
        result["review"]["id"],
        ManagerRequest(
            expected_version=2,
            decision=decision,
            rationale="Manager reviewed the expense and made the final decision.",
        ),
        "manager-test",
        "manager-run",
    )
    assert final["claim"]["status"] == (
        "accepted" if decision == "accept" else "rejected"
    )
    assert final["claim"]["outcome"]["reviewed"]
    assert final["claim"]["outcome"]["recommendation"] == recommendation
    assert final["decisions"][0]["actor"] == "manager-test"
    assert not final["active"]
    with pytest.raises(DomainError, match="closed"):
        service.manager_decision(
            final["id"],
            ManagerRequest(
                expected_version=3, decision=decision, rationale="Repeated decision"
            ),
            "manager-test",
            "repeat-run",
        )


def test_only_accept_or_reject_are_manager_actions():
    with pytest.raises(ValidationError):
        ManagerRequest(
            expected_version=2,
            decision="request_information",
            rationale="Missing receipt",
        )
