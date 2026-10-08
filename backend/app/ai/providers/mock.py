import json

from app.ai.models import LLMRequest, LLMResponse


class MockProvider:
    async def health(self):
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if request.context.get("task") == "chat":
            context = request.context
            if "claim" in context:
                claim = context["claim"]
                notes = "; ".join(check["message"] for check in context["checks"])
                answer = f"{claim['id']} is {claim['status'].replace('_', ' ')}. {notes} Use the claim and manager review controls to record a decision; this assistant cannot change claims."
                sources = [claim["id"], claim["policy"]["id"]]
            else:
                claims = context["claims"]
                review = [
                    c
                    for c in claims
                    if c["status"]
                    in ("pending_manager_review", "information_requested")
                ]
                answer = f"There are {len(claims)} claims and {len(review)} awaiting manager attention. Open a claim for policy, evidence and assessment details. I can explain records but cannot execute decisions."
                sources = [c["id"] for c in review] or [c["id"] for c in claims[:3]]
            return LLMResponse(
                content=json.dumps({"answer": answer, "sources": sources}),
                provider="mock",
                model=request.model,
            )
        findings = request.context["checks"]
        recommendation = (
            "reject"
            if any(f["severity"] == "reject" for f in findings)
            else "reject"
            if any(f["severity"] == "unverified" for f in findings)
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
            if any(f["severity"] == "unverified" for f in findings)
            else [],
            explanation="; ".join(f["message"] for f in findings),
        )
        return LLMResponse(
            content=json.dumps(data), provider="mock", model=request.model
        )
