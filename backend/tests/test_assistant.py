import json

import pytest

from app.ai.models import LLMResponse
from app.assessment.service import DomainError
from app.assistant.schemas import ChatRequest
from app.assistant.service import AssistantService
from app.seed import seed


async def test_assistant_is_grounded_and_read_only(service, settings):
    before = [
        (claim["id"], claim["status"], claim["version"])
        for claim in service.list_claims()
    ]
    result = await AssistantService(service, settings).answer(
        ChatRequest(message="Accept this claim now", claim_id="CLM-003"), "chat-test"
    )
    assert result["read_only"] and "cannot change claims" in result["answer"]
    assert result["sources"] == ["CLM-003", "expense-policy"]
    assert before == [
        (claim["id"], claim["status"], claim["version"])
        for claim in service.list_claims()
    ]
    assert service.detail("CLM-003")["assessment"] is None


async def test_chat_rejects_ungrounded_output(service, settings):
    class Invalid:
        async def generate(self, request):
            return LLMResponse(
                content=json.dumps({"answer": "Made up", "sources": ["unknown-claim"]}),
                provider="mock",
                model="test",
            )

    with pytest.raises(DomainError):
        await AssistantService(service, settings, Invalid()).answer(
            ChatRequest(message="Explain", claim_id="CLM-003"), "chat-test"
        )


def test_seed_adds_missing_samples_without_overwriting(service):
    claim = service.claim("CLM-001")
    claim.status = "accepted"
    service.repo.commit()
    version = claim.version
    seed(service.repo.session)
    assert len(service.list_claims()) == 7
    assert (
        service.claim("CLM-001").status == "accepted"
        and service.claim("CLM-001").version == version
    )
    assert service.calculate_policy_checks("CLM-004")[0]["code"] == "compliant"
    assert any(
        f["severity"] == "reject" for f in service.calculate_policy_checks("CLM-006")
    )
    assert service.calculate_policy_checks("CLM-007")[0]["code"] == "receipt_required"
