# Week 2 — AI recommends, manager decides

Week 2 starts from the Week 3 codebase and narrows decision authority: **the AI recommends accept or reject; the manager decides every expense**. Week 3 and Week 4 remain separate branches.

## Workflow

1. Open Claim queue and click Run to generate recommendations for submitted expenses. API and ARQ worker must both be running.
2. The app reads claim facts, evidence and policy, computes factual checks, and asks the model for structured advice. Optional policy RAG supplies supporting passages. There is no AI investigation stage.
3. Every valid recommendation creates a manager review. The claim remains `pending_manager_review`, even when policy flags allow automatic actions. No final outcome is created by the model or worker.
4. Open Manager review, read the recommendation and sources, then Accept or Reject with a rationale. The manager can disagree with the AI.
5. The app records the final status, manager identity, rationale, reviewed outcome and audit transaction. A closed review cannot be decided again.

There is no Request information action. Missing evidence supports a reject recommendation with its reason; the manager still makes the decision. Provider failures or invalid references leave the claim submitted with a failed execution record.

## Seven sample expenses

| Claim | AI recommendation | Status after AI |
| --- | --- | --- |
| CLM-001 Client lunch | Accept | Pending manager review |
| CLM-002 Personal entertainment | Reject | Pending manager review |
| CLM-003 Taxi, receipt missing | Reject | Pending manager review |
| CLM-004 Office stationery | Accept | Pending manager review |
| CLM-005 Conference rail ticket | Accept | Pending manager review |
| CLM-006 Hotel above limit | Reject | Pending manager review |
| CLM-007 Team lunch, receipt missing | Reject | Pending manager review |

These are deterministic mock recommendations, not preset final decisions.

## Local setup

Use the `week-2` checkout. Copy `.env.example` to `.env` only when you do not already have a configured file. Week 2 uses its own PostgreSQL database `claims_week2` and Redis queue `claims-week2`; keep them separate from Week 3 and Week 4.

```sh
(cd backend && uv sync --extra gcp)
(cd frontend && pnpm install --frozen-lockfile)
docker compose -p enterprise-ai-claims up -d --wait postgres redis
uv run --directory backend python -m app.bootstrap
uv run --directory backend alembic upgrade head
uv run --directory backend python -m app.seed
```

The bootstrap creates the configured database and refuses the existing shared Week 3 or Week 4 database. Seeding preserves existing claim decisions and disables the sample policy's auto-decision flags. The service forbids auto-decisions regardless of those flags.

For a credential-free demo, configure `LLM_PROVIDER=mock` and `RAG_ENABLED=false`. For Vertex, retain ADC, project, model and region settings. When using policy RAG, index this branch's policy before starting:

```sh
uv run --directory backend python -m app.rag.index --if-needed
```

Run in three terminals from the repository root:

```sh
# API
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```sh
# Recommendation worker
uv run --directory backend arq app.jobs.worker.WorkerSettings
```

```sh
# Frontend
pnpm --dir frontend dev --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173. Alternatively run `bash scripts/demo.sh`; Ctrl+C stops its API, frontend and worker. Stop older checkout servers using the same ports before starting.

## Code and verification

- `assessment/service.py`: saves advice and always creates manager approval; manager action is the only final-decision path.
- `schemas/assessment.py`: binary recommendations and binary manager actions.
- `ai/gateway.py`: explicitly requests advice, never investigation or execution.
- `features/reviews/Reviews.tsx`: shows the recommendation, with Accept and Reject only.
- `tests/test_manager_only.py`: covers all seven claims, auto-policy flags, manager overrides, reviewed outcomes and duplicate decisions.

Run from the root:

```sh
uv run --directory backend pytest -q
uv run --directory backend python -m app.evaluation.suite
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
pnpm --dir frontend exec playwright test
```

The browser test uses separate temporary storage and checks all seven claims are pending before a manager decides. Existing Week 3 documentation remains historical; this file defines the current Week 2 behavior.

## Verified results

64 backend tests passed, including PostgreSQL concurrency and real Redis/ARQ execution; 11 frontend tests and 20/20 mock evals passed. Backend/frontend lint and frontend build passed. The browser test verified all seven claims await a manager, then exercised acceptance against reject advice and rejection against accept advice. Test servers were stopped after verification. This Week 2 change was verified with the mock model; live Vertex generation was not rerun.
