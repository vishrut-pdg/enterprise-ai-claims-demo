from decimal import Decimal

import pytest
from sqlalchemy import select

from app.analytics.metering import estimate, measured, tokens
from app.analytics.service import dashboard
from app.db.models import AIExecution, AIUsageEvent
from app.workflows.process_claim import process_claim


def test_provider_units_and_thinking(settings):
    usage = {
        "prompt_token_count": 1000,
        "candidates_token_count": 100,
        "thoughts_token_count": 200,
        "cached_content_token_count": 400,
    }
    assert tokens(usage)["total_tokens"] == 1300
    assert estimate("vertex", "gemini-2.5-flash", usage, settings)[0] == Decimal(
        "0.000942"
    )
    assert (
        tokens(
            {"prompt_tokens": 10, "completion_tokens": 20, "thoughts_token_count": 5}
        )["output_tokens"]
        == 20
    )
    assert tokens({"prompt_eval_count": 10, "eval_count": 20})["total_tokens"] == 30


def test_missing_usage_and_embedding_units(settings):
    assert estimate("vertex", "gemini-2.5-flash", {}, settings)[0] is None
    assert (
        estimate("btp", "unknown", {"input_tokens": 10, "output_tokens": 0}, settings)[
            0
        ]
        is None
    )
    assert estimate(
        "vertex", "gemini-embedding-001", {"billable_character_count": 1000}, settings
    )[0] == Decimal("0.00015")
    assert tokens({"input_tokens": True, "output_tokens": -1})["total_tokens"] is None
    assert estimate("mock", "offline", {}, settings)[0] == 0


def test_failed_validation_retains_billed_usage(service, settings):
    session = service.repo.session
    with pytest.raises(ValueError):
        with measured(
            session,
            settings,
            "chat",
            "vertex",
            "gemini-2.5-flash",
            "failure",
            "CLM-001",
        ) as event:
            event.usage = {"prompt_token_count": 100, "candidates_token_count": 50}
            raise ValueError("invalid response")
    session.rollback()
    stored = session.scalar(select(AIUsageEvent))
    assert stored.status == "failed" and stored.error_code == "ValueError"
    assert stored.cost_usd > 0 and stored.duration_ms >= 0
    assert service.claim("CLM-001").status == "submitted"


@pytest.mark.asyncio
async def test_measured_runs_not_double_counted(service, settings):
    await process_claim(service, "CLM-001", 1, settings)
    data = dashboard(service.repo.session, settings)
    assert data["claim_runs"]["total"] == 1
    assert data["summary"]["requests"] == (
        2 if getattr(settings, "decision_mode", "") == "autonomous" else 1
    )
    assert not data["requests"][0]["historical"]
    assert data["summary"]["cost_usd"] == 0


def test_batch_correlation_is_scoped_to_claim(service, settings):
    session = service.repo.session
    for claim_id in ["CLM-001", "CLM-002"]:
        session.add(
            AIExecution(
                claim_id=claim_id,
                run_id="batch",
                provider="mock",
                model="offline",
                status="succeeded",
                duration_ms=50,
                trajectory=[],
                usage={},
            )
        )
    session.commit()
    with measured(
        session, settings, "assessment", "mock", "offline", "batch", "CLM-001"
    ):
        pass
    data = dashboard(session, settings)
    assert data["claim_runs"]["succeeded"] == 2
    assert data["summary"]["requests"] == 2
    assert sum(r["historical"] for r in data["requests"]) == 1
    assert dashboard(session, settings, provider="vertex")["summary"]["requests"] == 0


def test_historical_week4_stages_and_latency(service, settings):
    session = service.repo.session
    session.add(
        AIExecution(
            claim_id="CLM-001",
            run_id="old",
            provider="vertex",
            model="gemini-2.5-flash",
            status="succeeded",
            duration_ms=3000,
            trajectory=[],
            usage={
                stage: {"prompt_token_count": 100, "candidates_token_count": 10}
                for stage in ["assessment", "investigation"]
            },
        )
    )
    session.commit()
    data = dashboard(session, settings)
    assert data["summary"]["requests"] == 2
    assert data["summary"]["total_tokens"] == 220
    assert data["summary"]["average_ms"] is None
    assert data["claim_runs"]["average_ms"] == 3000


def test_analytics_api_filters_and_access(service, settings, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api import routes
    from app.main import app

    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    app.dependency_overrides[routes.service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get("/api/analytics/ai?days=0&provider=vertex")
            assert response.status_code == 200
            assert response.json()["summary"]["requests"] == 0
            assert client.get("/api/analytics/ai?days=-1").status_code == 422
            assert (
                client.get(
                    "/api/analytics/ai", headers={"X-Role": "employee"}
                ).status_code
                == 403
            )
    finally:
        app.dependency_overrides.clear()
