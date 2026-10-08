import pytest
from pydantic import ValidationError

from app.ai.factory import create_provider
from app.ai.gateway import LLMGateway
from app.config import Settings
from app.schemas.assessment import Assessment


@pytest.mark.parametrize(
    "update",
    [
        {"confidence": 1.01},
        {"confidence": float("nan")},
        {"recommendation": "approve"},
        {"extra": "value"},
        {"explanation": ""},
    ],
)
def test_schema(update):
    data = dict(
        recommendation="accept",
        confidence=0.9,
        findings=["compliant"],
        evidence_ids=[],
        unresolved_questions=[],
        explanation="Compliant",
    )
    data.update(update)
    with pytest.raises(ValidationError):
        Assessment.model_validate(data)


@pytest.mark.asyncio
async def test_mock_contract(service, settings):
    context = dict(
        claim=service.get_claim("CLM-001"),
        policy=service.get_policy("CLM-001"),
        evidence=service.get_evidence("CLM-001"),
        checks=service.calculate_policy_checks("CLM-001"),
    )
    result, response = await LLMGateway(create_provider(settings), settings).assess(
        context, "test"
    )
    assert result.recommendation == "accept" and response.provider == "mock"


@pytest.mark.parametrize("name", ["mock", "ollama", "vertex", "btp"])
def test_factory(name):
    provider = create_provider(Settings(llm_provider=name, _env_file=None))
    assert callable(provider.generate) and callable(provider.health)


@pytest.mark.parametrize("claim_id", ["CLM-001", "CLM-003"])
async def test_request_schema_constrains_grounding(service, settings, claim_id):
    from app.ai.providers.mock import MockProvider

    context = {
        "claim": service.get_claim(claim_id),
        "policy": service.get_policy(claim_id),
        "evidence": service.get_evidence(claim_id),
        "checks": service.calculate_policy_checks(claim_id),
    }

    class InspectingProvider(MockProvider):
        async def generate(self, request):
            properties = request.response_schema["properties"]
            assert properties["findings"]["items"]["enum"] == sorted(
                {f["code"] for f in context["checks"]}
            )
            assert properties["findings"]["minItems"] == 1
            if context["evidence"]:
                assert properties["evidence_ids"]["items"]["enum"] == sorted(
                    e["id"] for e in context["evidence"]
                )
            else:
                assert properties["evidence_ids"]["maxItems"] == 0
            return await super().generate(request)

    assessment, _ = await LLMGateway(InspectingProvider(), settings).assess(
        context, "grounding-test"
    )
    assert assessment.findings


async def test_narrative_findings_still_rejected(service, settings):
    import json

    from app.ai.providers.mock import MockProvider

    context = {
        "evidence": service.get_evidence("CLM-003"),
        "checks": service.calculate_policy_checks("CLM-003"),
    }

    class NarrativeProvider(MockProvider):
        async def generate(self, request):
            response = await super().generate(request)
            data = json.loads(response.content)
            data["findings"] = ["A verified receipt is missing."]
            response.content = json.dumps(data)
            return response

    with pytest.raises(ValueError, match="unknown references"):
        await LLMGateway(NarrativeProvider(), settings).assess(
            context, "grounding-test"
        )
