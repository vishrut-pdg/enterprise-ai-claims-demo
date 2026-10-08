"""Behavioral evals: isolated seeded storage, explicit expectations, JSON report.

Default mock run checks application behavior, not live model quality. --provider
vertex evaluates the real adapter, model answers and embeddings with ADC.
"""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.factory import create_provider
from app.ai.models import LLMResponse
from app.ai.providers.mock import MockProvider
from app.assessment.service import ClaimService, DomainError
from app.assistant.schemas import ChatRequest
from app.assistant.service import AssistantService
from app.config import Settings, get_settings
from app.db.models import Base
from app.db.repositories.claims import ClaimRepository
from app.evaluation.run import RETRIEVAL, run_evaluation
from app.rag.index import index_policy
from app.rag.service import PolicyRetrieval
from app.schemas.assessment import ManagerRequest
from app.seed import seed
from app.workflows.process_claim import process_claim

DATA = Path(__file__).parent / "datasets/demo.json"
POLICY = Path(__file__).resolve().parents[3] / "docs/policies/README.md"


class FaultProvider(MockProvider):
    def __init__(self, fault):
        self.fault = fault

    async def generate(self, request):
        response = await super().generate(request)
        data = json.loads(response.content)
        if self.fault == "unknown_finding":
            data["findings"] = ["invented-rule"]
        elif self.fault == "unknown_evidence":
            data["evidence_ids"] = ["invented-receipt"]
        elif self.fault == "low_confidence":
            data["confidence"] = 0.2
        elif self.fault == "unknown_citation":
            data["sources"] = ["invented-policy"]
        return LLMResponse(
            content=json.dumps(data), provider="mock", model=request.model
        )


async def run_suite(provider_name="mock"):
    settings = (
        get_settings().model_copy(
            update={
                "llm_provider": "vertex",
                "rag_enabled": True,
                "embedding_provider": "vertex",
            }
        )
        if provider_name == "vertex"
        else Settings(
            llm_provider="mock",
            llm_model="eval-mock",
            embedding_provider="mock",
            rag_enabled=True,
            _env_file=None,
        )
    )
    if provider_name == "vertex" and not settings.gcp_project_id:
        raise ValueError("Configure GCP_PROJECT_ID and ADC before Vertex evals")
    dataset = json.loads(DATA.read_text())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    results = []
    started = time.perf_counter()

    async def evaluate(group, case_id, fn):
        start = time.perf_counter()
        try:
            checks = await fn()
            results.append(
                {
                    "group": group,
                    "case": case_id,
                    "passed": all(checks.values()),
                    "checks": checks,
                    "duration_ms": round((time.perf_counter() - start) * 1000),
                }
            )
        except Exception as exc:
            # Provider/driver errors may contain credentials or supplied context.
            results.append(
                {
                    "group": group,
                    "case": case_id,
                    "passed": False,
                    "error_code": type(exc).__name__,
                    "duration_ms": round((time.perf_counter() - start) * 1000),
                }
            )

    try:
        with Session(engine, expire_on_commit=False) as session:
            seed(session)
            svc = ClaimService(ClaimRepository(session))
            provider = create_provider(settings)

            async def index():
                count = await index_policy(session, settings, POLICY.read_text())
                return {"nonempty_policy_index": count > 0}

            await evaluate("rag", "index_policy", index)

            for case in dataset["retrieval"]:

                async def retrieve(case=case):
                    passages = await PolicyRetrieval(session, settings).retrieve(
                        case["question"], ["expense-policy"]
                    )
                    return {
                        "hit_at_1": bool(passages)
                        and case["heading_contains"] in passages[0]["heading"].lower(),
                        "correct_policy_scope": all(
                            p["policy_id"] == "expense-policy" for p in passages
                        ),
                        "source_traceable": all(
                            p["source"] == "docs/policies/README.md" for p in passages
                        ),
                    }

                await evaluate("rag", case["id"], retrieve)

            async def wrong_scope():
                try:
                    await PolicyRetrieval(session, settings).retrieve(
                        "receipt", ["other-policy"]
                    )
                except DomainError:
                    return {"other_policy_not_retrieved": True}
                return {"other_policy_not_retrieved": False}

            await evaluate("rag", "policy_isolation", wrong_scope)

            # Every submitted seed takes the same workflow used by ARQ. Queue and
            # browser protocol are evaluated separately by Playwright.
            for case in dataset["claims"]:

                async def assess(case=case):
                    result = await process_claim(
                        svc,
                        case["id"],
                        svc.claim(case["id"]).version,
                        settings,
                        provider=provider,
                    )
                    assessment = result["assessment"]["data"]
                    return {
                        "expected_final_status": result["status"] == case["expected"],
                        "no_ai_recommendation": "recommendation" not in assessment,
                        "facts_summary_present": bool(assessment["summary"]),
                        "grounded_findings": set(assessment["findings"])
                        <= {f["code"] for f in result["findings"]},
                        "grounded_evidence": set(assessment["evidence_ids"])
                        <= {e["id"] for e in result["evidence"]},
                        "rag_in_trajectory": "retrieve_policy_passages"
                        in result["executions"][0]["trajectory"],
                        "bounded_retrieval": result["executions"][0]["trajectory"][:5]
                        == RETRIEVAL,
                        "review_matches_status": bool(result["review"])
                        == (case["expected"] == "pending_manager_review"),
                    }

                await evaluate("batch_outcomes", case["id"], assess)

            for case in dataset["chat"]:

                async def chat(case=case):
                    before = svc.claim(case["claim_id"]).status
                    answer = await AssistantService(svc, settings, provider).answer(
                        ChatRequest(
                            message=case["question"], claim_id=case["claim_id"]
                        ),
                        "eval-chat",
                    )
                    checks = {
                        "relevant_answer": case["answer_contains"]
                        in answer["answer"].lower(),
                        "sources_present": bool(answer["sources"]),
                        "read_only_flag": answer["read_only"],
                        "claim_unchanged": svc.claim(case["claim_id"]).status == before,
                    }
                    if provider_name == "vertex":
                        checks["policy_citation"] = any(
                            s.startswith("policy:") for s in answer["sources"]
                        )
                    return checks

                await evaluate("chat", case["id"], chat)

            async def invalid_citation():
                before = svc.claim("CLM-003").status
                try:
                    await AssistantService(
                        svc, settings, FaultProvider("unknown_citation")
                    ).answer(
                        ChatRequest(message="Explain policy", claim_id="CLM-003"),
                        "eval-invalid-source",
                    )
                except DomainError:
                    return {
                        "invented_citation_blocked": True,
                        "claim_unchanged": svc.claim("CLM-003").status == before,
                    }
                return {"invented_citation_blocked": False}

            await evaluate("chat", "invented_citation", invalid_citation)

            async def manager():
                claim = svc.detail("CLM-003")
                investigation = svc.manager_decision(
                    claim["review"]["id"],
                    ManagerRequest(
                        expected_version=claim["version"],
                        decision="investigate",
                        rationale="Manager is checking the supplied evidence.",
                    ),
                    "eval-manager",
                    "eval-investigate-run",
                )
                claim = svc.detail("CLM-003")
                result = svc.manager_decision(
                    claim["review"]["id"],
                    ManagerRequest(
                        expected_version=claim["version"],
                        decision="accept",
                        rationale="Original taxi receipt verified.",
                    ),
                    "eval-manager",
                    "eval-manager-run",
                )
                detail = svc.detail("CLM-003")
                return {
                    "investigation_remains_open": investigation["active"],
                    "no_final_investigation_outcome": investigation["claim"]["outcome"]
                    is None,
                    "review_closed": not result["active"],
                    "claim_accepted": detail["status"] == "accepted",
                    "reviewed_memory": detail["outcome"]["reviewed"],
                }

            await evaluate("review", "manager_outcome", manager)

        # Forced malicious/low-quality outputs test controls, independent of
        # which real model is selected. Fresh storage prevents case interference.
        for fault in ("unknown_finding", "unknown_evidence", "low_confidence"):
            isolated = create_engine("sqlite://")
            Base.metadata.create_all(isolated)
            with Session(isolated, expire_on_commit=False) as session:
                seed(session)
                svc = ClaimService(ClaimRepository(session))

                async def guard(fault=fault, svc=svc):
                    rejected = False
                    try:
                        await process_claim(
                            svc,
                            "CLM-001",
                            1,
                            Settings(
                                llm_provider="mock", rag_enabled=False, _env_file=None
                            ),
                            provider=FaultProvider(fault),
                        )
                    except DomainError:
                        rejected = True
                    detail = svc.detail("CLM-001")
                    if fault == "low_confidence":
                        return {
                            "unsafe_acceptance_prevented": detail["status"]
                            == "pending_manager_review"
                        }
                    return {
                        "invalid_reference_blocked": rejected,
                        "claim_unprocessed": detail["status"] == "submitted",
                        "no_assessment": detail["assessment"] is None,
                        "no_outcome": detail["outcome"] is None,
                    }

                await evaluate("guardrails", fault, guard)
            isolated.dispose()

        async def regression():
            prior = await run_evaluation()
            return {r["case"]: r["passed"] for r in prior}

        await evaluate("regression", "existing_six_cases", regression)
    finally:
        engine.dispose()
    passed = sum(r["passed"] for r in results)
    groups = {}
    for result in results:
        group = groups.setdefault(result["group"], {"passed": 0, "total": 0})
        group["total"] += 1
        group["passed"] += int(result["passed"])
    return {
        "provider": provider_name,
        "model": settings.llm_model,
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "total": len(results),
        "pass_rate": passed / len(results) if results else 0,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "groups": groups,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("mock", "vertex"), default="mock")
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation-results/latest.json")
    )
    args = parser.parse_args()
    from app.telemetry import configure

    configure(Settings(_env_file=None))
    report = asyncio.run(run_suite(args.provider))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"{report['passed']}/{report['total']} evals passed ({report['provider']}); report: {args.output}"
    )
    for result in report["results"]:
        if not result["passed"]:
            print(
                f"FAIL {result['group']}/{result['case']}: {result.get('error_code') or [k for k, v in result['checks'].items() if not v]}"
            )
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
