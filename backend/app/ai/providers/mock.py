import json

from app.ai.models import LLMRequest, LLMResponse


class MockProvider:
    async def health(self):
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        findings = request.context["checks"]
        recommendation = (
            "reject"
            if any(f["severity"] == "reject" for f in findings)
            else "investigate"
            if any(f["severity"] == "investigate" for f in findings)
            else "accept"
        )
        data = dict(
            recommendation=recommendation,
            confidence=0.99,
            findings=[f["code"] for f in findings],
            evidence_ids=[e["id"] for e in request.context["evidence"]],
            unresolved_questions=[
                "Please provide the missing or clarified supporting evidence."
            ]
            if recommendation == "investigate"
            else [],
            explanation="; ".join(f["message"] for f in findings),
        )
        return LLMResponse(
            content=json.dumps(data), provider="mock", model=request.model
        )
