# Week 1 — AI summarizes facts, manager decides

Week 1 starts from Week 2 and narrows AI's role to factual summaries and clarifying questions. This branch does not generate decision recommendations.

## Workflow

1. Run the fact-summary batch from Claim queue.
2. The app reads each expense's employee, amount, category, dates, evidence and policy. Deterministic calculations produce factual check results. AI returns a structured fact summary, source references and missing information, with no recommendation field.
3. Every successfully summarized claim awaits manager review. AI never accepts, rejects or investigates an expense.
4. The manager chooses **Accept**, **Reject** or **Investigate**, with a rationale. Accept/Reject closes the review and records the final outcome.
5. Investigate keeps the review active and sets the claim to `under_investigation`. It records the manager's action and rationale, advances the claim version, and creates no final outcome. The manager can later accept or reject.
6. The chatbot remains available on claim details and manager-review pages for clarifying questions. Answers use the supplied records and policy, cite validated sources, and do not change business state or recommend a decision.

Missing evidence remains a factual gap. Neither its presence nor a policy-check issue executes a decision. Technical/model failures leave the claim submitted with a failed execution record. Source/version checks, manager role checks and one-active-review constraints remain enforced.

## Local setup

Use branch `week-1`. Install dependencies and configure `.env` from `.env.example` if no configured file exists:

```sh
(cd backend && uv sync --extra gcp)
(cd frontend && pnpm install --frozen-lockfile)
docker compose -p enterprise-ai-claims up -d --wait postgres redis
uv run --directory backend python -m app.bootstrap
uv run --directory backend alembic upgrade head
uv run --directory backend python -m app.seed
```

Week 1 uses `DATABASE_URL=postgresql+psycopg://claims:claims@localhost:5432/claims_week1` and `ARQ_QUEUE_NAME=claims-week1`. The bootstrap refuses the existing other-week databases. Do not reuse their queue or database.

For an offline demo set `LLM_PROVIDER=mock` and `RAG_ENABLED=false`. Vertex remains supported with ADC and configured project/model/regions. Optional RAG supplies factual policy context; index this branch's policy when enabled:

```sh
uv run --directory backend python -m app.rag.index --if-needed
```

Run these in three terminals from the repository root:

```sh
# API
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```sh
# Fact-summary worker
uv run --directory backend arq app.jobs.worker.WorkerSettings
```

```sh
# Frontend
pnpm --dir frontend dev --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173. Alternatively run `bash scripts/demo.sh`; Ctrl+C stops API, frontend and worker. Stop older checkouts using these ports before launching.

## Code changes

- `schemas/assessment.py`: fact summary schema with no recommendation; manager actions include investigate.
- `ai/gateway.py` and `ai/providers/mock.py`: factual summarization and source validation.
- `assessment/service.py`: summary persistence, manager-owned investigation state and terminal outcomes.
- `assistant/service.py`: clarifying answers, no decision advice or write tools.
- `features/claims/ClaimDetail.tsx`: visible factual summary and inline chatbot.
- `features/reviews/Reviews.tsx`: three manager actions and investigation feedback.
- `tests/test_manager_only.py`: seven facts-only summaries, manager investigation, final decisions, version protection and closed-review checks.

The internal legacy `ClaimAssessment` table now stores fact-summary JSON. The legacy outcome `recommendation` column contains a `not_applicable` compatibility marker and is omitted from API responses. It is not model-generated advice. Older Week 2/3 documentation is retained as history; this document describes Week 1.

## Verification commands

```sh
uv run --directory backend pytest -q
uv run --directory backend python -m app.evaluation.suite
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
pnpm --dir frontend exec playwright test
```

The browser test uses temporary storage and a dedicated queue. It checks all seven summaries contain no recommendation, clarifying chat, a manager's Investigate action surviving refresh, and final Accept/Reject actions. It shuts down test processes automatically. The mocked eval suite also tests invalid decision output, source grounding and manager investigation before final acceptance.

## Verification results

66 backend tests passed, including isolated PostgreSQL concurrency and Redis/ARQ execution. 11 frontend tests, 20/20 mock evals, lint and frontend build passed. The browser test verified facts-only summaries, clarifying chat, persistent manager investigation and final Accept/Reject actions. Test servers were shut down. Live Vertex generation was not rerun for this change.
