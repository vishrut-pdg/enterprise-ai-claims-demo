"""Credential-free behavioral evaluation over real ADK/workflow and isolated storage."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.models import LLMResponse
from app.ai.providers.mock import MockProvider
from app.assessment.service import ClaimService, DomainError
from app.config import Settings
from app.db.models import Base
from app.db.repositories.claims import ClaimRepository
from app.seed import seed
from app.workflows.process_claim import process_claim

RETRIEVAL = [
    "get_claim",
    "get_policy",
    "get_evidence",
    "calculate_policy_checks",
    "get_previous_outcomes",
]


class CaseProvider(MockProvider):
    def __init__(self, mode):
        self.mode = mode

    async def generate(self, request):
        if self.mode == "invalid":
            return LLMResponse(content="{}", provider="mock", model=request.model)
        response = await super().generate(request)
        if self.mode == "unsafe":
            data = json.loads(response.content)
            data.update(recommendation="accept", unresolved_questions=[])
            response.content = json.dumps(data)
        return response


async def run_evaluation():
    cases = json.loads((Path(__file__).parent / "datasets/cases.json").read_text())
    results = []
    for case in cases:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as session:
            seed(session)
            svc = ClaimService(ClaimRepository(session))
            if case.get("mode") == "stale":
                svc.claim(case["claim_id"]).title = "Updated source"
                svc.repo.commit()
            failed = False
            try:
                result = await process_claim(
                    svc,
                    case["claim_id"],
                    1,
                    Settings(
                        llm_provider="mock", llm_model="evaluation", _env_file=None
                    ),
                    provider=CaseProvider(case.get("mode")),
                )
            except DomainError:
                failed = True
                result = svc.detail(case["claim_id"])
            assert result["status"] == case["expected"], case["id"]
            assert result["policy"]["id"] == "expense-policy"
            assert [e["id"] for e in result["evidence"]] == case["evidence_ids"]
            if case.get("mode") in ("invalid", "stale", "unsafe"):
                assert (
                    failed
                    and result["assessment"] is None
                    and result["outcome"] is None
                )
            else:
                assert result["assessment"]["claim_version"] == 1
                assert "recommendation" not in result["assessment"]["data"]
                assert result["assessment"]["data"]["summary"]
                trajectory = result["executions"][0]["trajectory"]
                assert trajectory == RETRIEVAL + ["assess", case["action"]]
                assert set(result["assessment"]["data"]["findings"]) <= {
                    f["code"] for f in result["findings"]
                }
                assert bool(result["review"]) == (
                    case["expected"] == "pending_manager_review"
                )
            results.append({"case": case["id"], "passed": True})
        engine.dispose()
    return results


if __name__ == "__main__":
    from app.telemetry import configure

    configure(Settings(_env_file=None))
    print(json.dumps(asyncio.run(run_evaluation()), indent=2))
