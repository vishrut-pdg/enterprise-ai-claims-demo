"""Week 4 accept/reject evals; isolated synthetic claims, no human decisions."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.factory import create_provider
from app.ai.models import LLMResponse
from app.ai.providers.mock import MockProvider
from app.assessment.service import ClaimService, DomainError
from app.config import Settings, get_settings
from app.db.models import Base
from app.db.repositories.claims import ClaimRepository
from app.rag.index import index_policy
from app.seed import seed
from app.workflows.process_claim import process_claim

EXPECTED = {
    "CLM-001": "accepted",
    "CLM-002": "rejected",
    "CLM-003": "rejected",
    "CLM-004": "accepted",
    "CLM-005": "accepted",
    "CLM-006": "rejected",
    "CLM-007": "rejected",
}


class Adversarial(MockProvider):
    def __init__(self, kind):
        self.kind = kind

    async def generate(self, request):
        response = await super().generate(request)
        data = json.loads(response.content)
        if self.kind == "invented_evidence":
            data["evidence_ids"] = ["invented-receipt"]
        elif self.kind == "low_confidence":
            data["confidence"] = 0.2
        elif self.kind == "forced_acceptance":
            data.update(recommendation="accept", confidence=0.99)
            if request.context.get("task") == "investigation":
                data["limitations"] = []
            else:
                data["unresolved_questions"] = []
        response.content = json.dumps(data)
        return LLMResponse(**response.model_dump())


async def run_autonomous_evaluation(provider_name="mock"):
    settings = (
        get_settings().model_copy(
            update={
                "llm_provider": "vertex",
                "decision_mode": "autonomous",
                "rag_enabled": True,
                "embedding_provider": "vertex",
            }
        )
        if provider_name == "vertex"
        else Settings(
            llm_provider="mock",
            llm_model="week4-eval",
            decision_mode="autonomous",
            rag_enabled=False,
            _env_file=None,
        )
    )
    cases = [(cid, expected, None) for cid, expected in EXPECTED.items()] + [
        ("CLM-003", "rejected", "forced_acceptance"),
        ("CLM-001", "rejected", "low_confidence"),
        ("CLM-001", "submitted", "invented_evidence"),
    ]
    results = []
    for claim_id, expected, adversarial in cases:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as session:
            seed(session)
            service = ClaimService(ClaimRepository(session))
            try:
                selected = (
                    settings.model_copy(update={"rag_enabled": False})
                    if adversarial
                    else settings
                )
                if selected.rag_enabled:
                    source = (
                        Path(__file__).resolve().parents[3] / "docs/policies/README.md"
                    )
                    await index_policy(session, selected, source.read_text())
                provider = (
                    Adversarial(adversarial)
                    if adversarial
                    else create_provider(selected)
                )
                try:
                    result = await process_claim(
                        service, claim_id, 1, selected, provider=provider
                    )
                except DomainError:
                    if adversarial != "invented_evidence":
                        raise
                    result = service.detail(claim_id)
                checks = {
                    "expected_status": result["status"] == expected,
                    "no_human_review": result["review"] is None
                    and service.list_reviews() == [],
                }
                if expected != "submitted":
                    checks.update(
                        investigation_recorded=bool(
                            result["assessment"]["data"].get("investigation")
                        ),
                        binary_decision=result["assessment"]["data"]["recommendation"]
                        in ("accept", "reject"),
                        audited=any(
                            e["event_type"] == "autonomous_decision_recorded"
                            for e in result["history"]
                        ),
                    )
                else:
                    checks.update(
                        no_fabricated_decision=result["assessment"] is None
                        and result["outcome"] is None
                    )
                results.append(
                    {
                        "case": adversarial or claim_id,
                        "passed": all(checks.values()),
                        "checks": checks,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "case": adversarial or claim_id,
                        "passed": False,
                        "error_code": type(exc).__name__,
                    }
                )
        engine.dispose()
    return {
        "provider": provider_name,
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("mock", "vertex"), default="mock")
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation-results/week4.json")
    )
    args = parser.parse_args()
    report = asyncio.run(run_autonomous_evaluation(args.provider))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"{report['passed']}/{report['total']} autonomous evals passed; report: {args.output}"
    )
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
