"""Read-only analytics over durable calls and original claim execution history."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import select

from app.analytics.metering import PRICE_SOURCE, estimate, tokens
from app.db.models import AIExecution, AIUsageEvent


def latency(rows):
    values = sorted(r["duration_ms"] for r in rows if r["duration_ms"] is not None)
    return {
        "average_ms": round(sum(values) / len(values)) if values else None,
        "p95_ms": values[max(0, ceil(len(values) * 0.95) - 1)] if values else None,
    }


def summarize(rows):
    priced = [r for r in rows if r["cost_usd"] is not None]
    reported = [r for r in rows if r["total_tokens"] is not None]
    return {
        "requests": len(rows),
        "succeeded": sum(r["status"] == "succeeded" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "success_rate": round(
            100 * sum(r["status"] == "succeeded" for r in rows) / len(rows), 1
        )
        if rows
        else None,
        "input_tokens": sum(r["input_tokens"] or 0 for r in rows),
        "output_tokens": sum(r["output_tokens"] or 0 for r in rows),
        "thinking_tokens": sum(r["thinking_tokens"] or 0 for r in rows),
        "total_tokens": sum(r["total_tokens"] or 0 for r in rows),
        "billable_characters": sum(r["billable_characters"] or 0 for r in rows),
        "token_reported_requests": len(reported),
        "priced_requests": len(priced),
        "unpriced_requests": len(rows) - len(priced),
        "cost_usd": round(sum(r["cost_usd"] for r in priced), 10) if priced else None,
        **latency(rows),
    }


def dashboard(session, settings, days=30, provider=None):
    since = datetime.now(UTC) - timedelta(days=days) if days else None
    event_query, run_query = select(AIUsageEvent), select(AIExecution)
    if since:
        event_query = event_query.where(AIUsageEvent.created_at >= since)
        run_query = run_query.where(AIExecution.created_at >= since)
    if provider:
        event_query = event_query.where(AIUsageEvent.provider == provider)
        run_query = run_query.where(AIExecution.provider == provider)
    events = list(session.scalars(event_query.order_by(AIUsageEvent.created_at.desc())))
    runs = list(session.scalars(run_query.order_by(AIExecution.created_at.desc())))
    requests = []
    for event in events:
        requests.append(
            {
                "id": event.id,
                "run_id": event.run_id,
                "claim_id": event.claim_id,
                "operation": event.operation,
                "provider": event.provider,
                "model": event.model,
                "status": event.status,
                "duration_ms": event.duration_ms,
                "created_at": event.created_at.isoformat(),
                "error_code": event.error_code,
                "cost_usd": float(event.cost_usd)
                if event.cost_usd is not None
                else None,
                "cost_basis": event.cost_basis,
                "historical": False,
                **tokens(event.usage),
            }
        )
    # Existing executions remain visible. Derive historical usage only where there
    # is no measured event for that claim/run; never count Week 4 stages twice.
    measured_runs = {(e.run_id, e.claim_id) for e in events if e.claim_id is not None}
    for run in runs:
        if (run.run_id, run.claim_id) in measured_runs:
            continue
        stages = (
            run.usage
            if isinstance(run.usage.get("assessment"), dict)
            else {"assessment": run.usage}
        )
        for operation, usage in stages.items():
            if operation not in {"assessment", "investigation"} or not isinstance(
                usage, dict
            ):
                continue
            cost, basis = estimate(run.provider, run.model, usage, settings)
            requests.append(
                {
                    "id": f"legacy:{run.id}:{operation}",
                    "run_id": run.run_id,
                    "claim_id": run.claim_id,
                    "operation": operation,
                    "provider": run.provider,
                    "model": run.model,
                    "status": run.status,
                    "duration_ms": None,
                    "created_at": run.created_at.isoformat(),
                    "error_code": run.error_code,
                    "cost_usd": float(cost) if cost is not None else None,
                    "cost_basis": "Historical estimate · " + basis,
                    "historical": True,
                    **tokens(usage),
                }
            )
    requests.sort(key=lambda row: row["created_at"], reverse=True)
    groups = defaultdict(list)
    for request in requests:
        groups[(request["provider"], request["model"])].append(request)
    models = [
        {"provider": key[0], "model": key[1], **summarize(rows)}
        for key, rows in groups.items()
    ]
    models.sort(key=lambda row: row["requests"], reverse=True)
    claim_runs = [
        {
            "id": run.id,
            "claim_id": run.claim_id,
            "run_id": run.run_id,
            "provider": run.provider,
            "model": run.model,
            "status": run.status,
            "duration_ms": run.duration_ms,
            "created_at": run.created_at.isoformat(),
            "error_code": run.error_code,
            "trajectory": run.trajectory,
        }
        for run in runs
    ]
    run_summary = {
        "total": len(runs),
        "succeeded": sum(r.status == "succeeded" for r in runs),
        "failed": sum(r.status == "failed" for r in runs),
        **latency(claim_runs),
    }
    run_summary["success_rate"] = (
        round(100 * run_summary["succeeded"] / len(runs), 1) if runs else None
    )
    return {
        "days": days,
        "provider": provider,
        "currency": "USD",
        "summary": summarize(requests),
        "claim_runs": run_summary,
        "models": models,
        "requests": requests[:200],
        "recent_runs": claim_runs[:100],
        "history_limit": 200,
        "price_source": PRICE_SOURCE,
        "pricing_checked_at": "2026-10-09",
        "notes": [
            "Estimated provider API cost, not a cloud bill. Infrastructure, credits and negotiated pricing are excluded.",
            "Unknown usage or price is shown as unavailable; totals include only priced requests.",
            "Claim runs and model requests differ: Week 4 has investigation plus assessment; chat and RAG are separate requests.",
            "Historic claim usage is recovered when available. Chat and embedding history starts with this migration.",
            "Request latency includes generation/validation. Historical stage latency is unavailable; recorded claim-run latency remains visible.",
        ],
    }
