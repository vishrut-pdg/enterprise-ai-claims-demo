"""Provider-reported usage, explicit missing data, and snapshot cost estimates."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from math import isfinite
from time import perf_counter

from app.db.models import AIUsageEvent
from app.telemetry import correlation_id

PRICE_SOURCE = "https://cloud.google.com/vertex-ai/generative-ai/pricing"
# Standard online text prices, USD per million units, checked 2026-10-09.
DEFAULT_RATES = {
    "vertex:gemini-2.5-flash": {"input": 0.30, "output": 2.50, "cached": 0.03},
    "vertex:gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40, "cached": 0.01},
    "vertex:gemini-embedding-001": {"characters": 0.15},
}


def count(data, *keys):
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = data.get(key)
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
            and value >= 0
            and int(value) == value
        ):
            return int(value)
    return None


def tokens(usage):
    prompt = count(
        usage,
        "prompt_token_count",
        "promptTokenCount",
        "prompt_tokens",
        "prompt_eval_count",
        "input_tokens",
    )
    output = count(
        usage,
        "candidates_token_count",
        "candidatesTokenCount",
        "completion_tokens",
        "eval_count",
        "output_tokens",
    )
    thinking = count(usage, "thoughts_token_count", "thoughtsTokenCount")
    # OpenAI completion_tokens already includes reasoning. Gemini candidates excludes it.
    if (
        output is not None
        and thinking is not None
        and any(
            key in usage for key in ("candidates_token_count", "candidatesTokenCount")
        )
    ):
        output += thinking
    cached = count(usage, "cached_content_token_count", "cachedContentTokenCount")
    if cached is None:
        cached = count(usage.get("prompt_tokens_details") or {}, "cached_tokens")
    total = count(usage, "total_token_count", "totalTokenCount", "total_tokens")
    if total is None and prompt is not None and output is not None:
        total = prompt + output
    return {
        "input_tokens": prompt,
        "output_tokens": output,
        "thinking_tokens": thinking,
        "cached_tokens": cached,
        "total_tokens": total,
        "billable_characters": count(usage, "billable_character_count"),
    }


def estimate(provider, model, usage, settings):
    if provider in {"mock", "ollama"}:
        return Decimal(0), "No provider API charge; infrastructure excluded"
    key = f"{provider}:{model}"
    overrides = settings.ai_cost_rates
    rate = overrides.get(key, DEFAULT_RATES.get(key))
    if rate is None or (
        "characters" not in rate and not {"input", "output"} <= rate.keys()
    ):
        return None, "Rate unavailable"
    normalized = tokens(usage)
    if "characters" in rate:
        units = normalized["billable_characters"]
        if units is None:
            return None, "Billable characters unavailable"
        cost = Decimal(units) * Decimal(str(rate["characters"])) / Decimal(1_000_000)
    else:
        prompt, output = normalized["input_tokens"], normalized["output_tokens"]
        if prompt is None or output is None:
            return None, "Token usage unavailable"
        cached = min(normalized["cached_tokens"] or 0, prompt)
        cost = (
            Decimal(prompt - cached) * Decimal(str(rate.get("input", 0)))
            + Decimal(cached) * Decimal(str(rate.get("cached", rate.get("input", 0))))
            + Decimal(output) * Decimal(str(rate.get("output", 0)))
        ) / Decimal(1_000_000)
    source = (
        "Configured rate" if key in overrides else "Standard online rate · 2026-10-09"
    )
    return cost.quantize(Decimal("0.0000000001")), source


@dataclass
class Measurement:
    usage: dict = field(default_factory=dict)


@contextmanager
def measured(session, settings, operation, provider, model, run_id=None, claim_id=None):
    measurement = Measurement()
    started = perf_counter()
    error = None
    try:
        yield measurement
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        if session is not None:
            cost, basis = estimate(provider, model, measurement.usage, settings)
            session.add(
                AIUsageEvent(
                    claim_id=claim_id,
                    run_id=run_id or correlation_id.get() or "unlinked",
                    operation=operation,
                    provider=provider,
                    model=model,
                    status="failed" if error else "succeeded",
                    duration_ms=round((perf_counter() - started) * 1000),
                    usage=measurement.usage,
                    cost_usd=cost,
                    cost_basis=basis,
                    error_code=error,
                )
            )
            # Callers end their read transaction before inference. Measurement commits
            # precede the business final-action transaction, preserving failed-call cost.
            session.commit()
