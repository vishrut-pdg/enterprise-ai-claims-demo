# AI usage and performance — all four weeks

Open **AI usage & performance** in the sidebar, below Claim queue and Manager review (Decision history in Week 4), or visit `#/analytics`. The page refreshes every five seconds. Filter by period/provider and inspect model requests or claim run traces. It never starts claim processing.

## Setup

From `backend`, using the environment for the selected week:

```sh
uv run alembic upgrade head
```

Run this migration against **each** week's database: `claims_week1`, `claims_week2`, `claims`, and `claims_week4`. It adds `ai_usage_events`; it does not reset claims or decisions. Restart your backend and frontend after switching branches. Migration must run before processing or chat because these paths now persist telemetry.

## Reading the page

- A **claim run** is the complete workflow recorded in `ai_executions`, including failed runs and retries. An expense being rejected is a successful run when processing completed successfully. Manager decisions do not count as model requests.
- A **model request** is a summary/assessment, autonomous investigation, chatbot generation, or document/query embedding. Week 4 usually makes investigation and assessment calls. RAG queries/indexing and chat are measured separately in every week.
- Latency uses elapsed wall-clock time around the provider request and response validation. Claim-run latency covers its existing workflow boundary. P95 uses the nearest-rank percentile over available durations; it is not an average.
- Input/output/total tokens come from provider metadata. Gemini output cost includes thinking tokens. Cached input uses a separate rate when reported. Missing metadata is unavailable, never an invented count.
- Costs are **estimated provider API charges in USD**, not a cloud billing report. Only requests with usage and a known rate contribute to the subtotal. The page displays priced/unpriced coverage. Mock/Ollama have zero provider API charge; hosting, machines, database, network, credits, taxes, and negotiated discounts are excluded.
- Failed requests can still incur cost when the model responded but schema/citation validation failed. Transport errors without usage have unavailable cost. Telemetry saves error class and metadata; it does not save prompts, generated chat content, credentials, or stack traces.

## Pricing configuration

Standard online text defaults, checked 2026-10-09 against [Vertex pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing): Gemini 2.5 Flash input/output/cached input are $0.30/$2.50/$0.03 per million tokens; Flash Lite $0.10/$0.40/$0.01. Gemini Embedding uses $0.15 per million **billable characters**, using the API's billable character metadata. It does not multiply embedding token counts by a character price.

Set `AI_COST_RATES` to JSON in `.env` for another model or contracted rate. Keys are exact `provider:model` identities; units are USD per million tokens or billable characters:

```dotenv
AI_COST_RATES='{"btp:your-model":{"input":1.0,"output":3.0,"cached":0.1},"vertex:gemini-embedding-001":{"characters":0.15}}'
```

Rates must be finite and nonnegative. Generation rates require input and output. Each new event snapshots its estimated cost/rate basis, so changing configuration does not rewrite historical measured costs. Older `ai_executions` usage is estimated at the currently configured rate and labelled historical. Unsupported models stay unpriced.

## Code walkthrough

1. `app/analytics/metering.py`: normalizes Vertex/OpenAI-compatible/Ollama usage; estimates cost with Decimal arithmetic; `measured` captures duration, usage and outcome and commits one durable event. Callers finish their read transaction before inference; telemetry is committed before the claim's final action.
2. `app/ai/gateway.py`: wraps structured summary/assessment validation and Week 4 investigation. `workflows/process_claim.py` supplies the workflow's session and correlation ID.
3. `app/assistant/service.py`: measures clarifying chat including response/citation validation. Chat still cannot make business decisions.
4. `app/rag/embeddings.py`: measures document indexing and retrieval queries. `rag/service.py` carries the claim ID so requests can be traced correctly even when multiple batch jobs share a correlation ID.
5. `db/models/__init__.py` and migration `20261009_ai_usage.py`: add the usage table alongside the original execution history.
6. `app/analytics/service.py`: builds totals, success rate, latency, provider/model groups and recent histories. Historical claim usage is recovered without double counting measured claim/run pairs. Historical stage latency is unavailable. Chat/embedding history starts with this migration; historical execution-based request rows are inferred from stored claim usage, not a reconstructed provider billing log.
7. `GET /api/analytics/ai?days=30&provider=vertex`: analyst/manager read endpoint. `days=0` means all time. Totals cover the selected period; history tables return the latest 200 requests and 100 runs.
8. `frontend/src/features/analytics/AIUsage.tsx`: refresh/filter state, metric cards, provider/model breakdown, searchable/sortable request history and expandable claim traces. Navigation lives in `App.tsx`.

## Week scopes remain distinct

| Branch | AI activity | Who decides? |
|---|---|---|
| week-1 | Fact summary, clarifying chat, optional RAG | Manager accepts/rejects/investigates |
| week-2 | Recommendation, clarifying chat, optional RAG | Manager accepts/rejects every claim |
| week-3 | Assessment, clarifying chat, optional RAG | Automation handles eligible decisions; manager handles escalation |
| week-4 | Investigation then assessment, clarifying chat, optional RAG | Autonomous workflow accepts/rejects |

The analytics page adds visibility; it does not change any week's authority or decision rules.
