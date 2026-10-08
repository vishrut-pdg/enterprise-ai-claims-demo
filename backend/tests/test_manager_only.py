"""Week 1 summaries never recommend a decision; managers own all three actions."""

import pytest
from pydantic import ValidationError

from app.assessment.service import DomainError
from app.db import models as m
from app.schemas.assessment import ManagerRequest
from app.workflows.process_claim import process_claim


@pytest.mark.parametrize("claim_id", [f"CLM-00{i}" for i in range(1, 8)])
async def test_every_claim_has_facts_only(service, settings, claim_id):
    policy = service.repo.get(m.Policy, "expense-policy")
    policy.auto_accept = policy.auto_reject = True
    service.repo.commit()
    result = await process_claim(service, claim_id, 1, settings)
    assert "recommendation" not in result["assessment"]["data"]
    summary = result["assessment"]["data"]["summary"]
    assert claim_id in summary and result["amount"] in summary
    assert result["status"] == "pending_manager_review"
    assert result["review"]["active"] and result["outcome"] is None
    assert not any(
        e["event_type"]
        in ("recommendation_produced", "claim_accepted", "claim_rejected")
        for e in result["history"]
    )


@pytest.mark.parametrize("decision", ["accept", "reject"])
async def test_manager_investigation_then_final_decision(service, settings, decision):
    result = await process_claim(service, "CLM-003", 1, settings)
    review_id = result["review"]["id"]

    def request(version, action):
        return ManagerRequest(
            expected_version=version,
            decision=action,
            rationale="Manager reviewed the supplied receipt facts.",
        )

    investigation = service.manager_decision(
        review_id, request(2, "investigate"), "manager-test", "investigate-run"
    )
    assert investigation["active"]
    assert investigation["claim"]["status"] == "under_investigation"
    assert investigation["claim"]["outcome"] is None
    assert investigation["claim"]["version"] == 3
    with pytest.raises(DomainError, match="version"):
        service.manager_decision(
            review_id, request(2, decision), "manager-test", "stale-run"
        )
    continued = service.manager_decision(
        review_id, request(3, "investigate"), "manager-test", "continued-run"
    )
    assert continued["claim"]["version"] == 4
    final = service.manager_decision(
        review_id, request(4, decision), "manager-test", "final-run"
    )
    assert final["claim"]["status"] == (
        "accepted" if decision == "accept" else "rejected"
    )
    assert final["claim"]["outcome"]["reviewed"] and not final["active"]
    assert "recommendation" not in final["claim"]["outcome"]
    assert [d["decision"] for d in final["decisions"]] == [
        "investigate",
        "investigate",
        decision,
    ]
    with pytest.raises(DomainError, match="closed"):
        service.manager_decision(
            review_id, request(5, decision), "manager-test", "repeat-run"
        )


def test_no_request_information_action():
    with pytest.raises(ValidationError):
        ManagerRequest(
            expected_version=2,
            decision="request_information",
            rationale="Missing receipt",
        )
