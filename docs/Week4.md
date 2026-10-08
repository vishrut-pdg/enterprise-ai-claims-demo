# Week 4 — Autonomous AI investigation and decisions

Week 4 builds on the completed Week 3 implementation in a separate branch/worktree. The reference app automatically investigates undecided expense claims and records **Accept or Reject**. It creates no new manager-review tasks and requires no Run click or approval.

## Behavior

| Stage | Week 3 | Week 4 |
|---|---|---|
| Start processing | Queue button | Worker discovers claims at startup and every five seconds |
| Missing receipt or uncertainty | Manager review | AI investigation; reject when supplied records cannot establish compliance |
| Decision | Accept / reject / investigate | Final accept / reject |
| Human approval | Required for investigations | Disabled in autonomous mode |
| Memory | Reviewed manager outcomes | Prior recorded AI outcomes; never overrides current policy checks |
| Dashboard | Queue and manager review | Autonomous monitor and decision history |
| Claim detail | Assessment and manager controls | AI investigation, unmet requirements, final decision and audit |

The default Week 4 policy accepts CLM-001, CLM-004 and CLM-005; rejects CLM-002, CLM-003, CLM-006 and CLM-007. Missing-receipt claims are rejected after AI investigation instead of waiting for a manager.

## Investigation workflow

1. The ARQ worker scans submitted claims and undecided historical reviews.
2. A queue- and version-specific job ID prevents duplicate scheduling and cross-worktree collisions.
3. The bounded ADK agent retrieves claim lines, policy, evidence, deterministic checks and prior outcomes. RAG supplies relevant passages from the applicable policy.
4. **First model call:** AI investigation examines those sources and returns a structured conclusion, confidence, exact finding/evidence IDs, summary and limitations.
5. The service validates references, rechecks source facts and records the investigation.
6. **Second model call:** the assessment produces an accept/reject recommendation using the completed investigation.
7. The service rechecks current claim version and sources. It accepts only if all checks pass, both model stages support acceptance at confidence >=0.90, evidence references are complete, no limitations/questions remain and policy permits acceptance. Otherwise it rejects under the autonomous policy with reasons.
8. The final assessment includes the investigation report; the outcome and audit events are recorded atomically. Existing historical reviews can be closed by the AI with an `ai_investigator` decision.

The model cannot fabricate a missing receipt, mark evidence verified, override a failed deterministic rule or act on stale facts. The current investigator uses supplied records and policy retrieval; it does not contact employees, merchants or external verification systems.

Technical failure is distinct from rejection. Invalid model output, unavailable providers and database conflicts leave the claim undecided with a failed execution record. Provider failures receive bounded ARQ retries; failed automatic job results expire after a configurable cooldown so the recurring scan can retry without human intervention or a tight retry loop. Audit history remains in PostgreSQL.

If policy explicitly disables automatic rejection, an unacceptably supported claim remains a configuration failure rather than silently ignoring policy. The supplied Week 4 policy enables automatic acceptance and rejection.

## Isolation from Week 3

Week 3 stays on its own branch and worktree. Week 4 defaults to:

```dotenv
DATABASE_URL=postgresql+psycopg://claims:claims@localhost:5432/claims_week4
ARQ_QUEUE_NAME=claims-week4
DECISION_MODE=autonomous
AUTONOMOUS_RETRY_SECONDS=300
```

The bootstrap command creates the separate database. It refuses to prepare the Week 3 `claims` database in autonomous mode. Job IDs include queue name, claim ID and claim version because ARQ result keys are shared across queues in Redis. Do not reuse Week 3's queue/database settings.

The `human_review` code path remains explicitly available for historical regression tests; it is not the default Week 4 runtime. The UI exposes no human decision controls, and the human-decision API rejects requests in autonomous mode. Week 3 documentation is retained as a historical implementation record.

## Manual setup

From a fresh checkout, get the Week 4 branch:

```sh
git clone --branch week-4 git@github.com:vishrut-pdg/enterprise-ai-claims-demo.git enterprise-ai-claims-week4
cd enterprise-ai-claims-week4
cp .env.example .env
```

If you already have a checkout, use `git switch week-4`. If Git reports that the branch is checked out in another worktree, open that worktree instead. The existing local Week 4 worktree is:

```sh
cd /Users/vishrut/.codex/worktrees/0377/enterprise-ai-claims
```

Install dependencies, configure root `.env`, and prepare storage:

```sh
(cd backend && uv sync --extra gcp)
(cd frontend && pnpm install --frozen-lockfile)
docker compose -p enterprise-ai-claims up -d --wait postgres redis
uv run --directory backend python -m app.bootstrap
uv run --directory backend alembic upgrade head
uv run --directory backend python -m app.seed
uv run --directory backend python -m app.rag.index --if-needed
```

For Vertex, use ADC and the existing project/model settings. Set `LLM_PROVIDER=vertex`, `RAG_ENABLED=true`, `EMBEDDING_PROVIDER=vertex`, and `DECISION_MODE=autonomous`. Policy indexing uses `gemini-embedding-001` with 768 dimensions. The separate model/embedding regions remain configurable.

Run in three terminals from this root:

```sh
# Terminal 1: API
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```sh
# Terminal 2: autonomous worker — starts processing immediately
uv run --directory backend arq app.jobs.worker.WorkerSettings
```

```sh
# Terminal 3: frontend
pnpm --dir frontend dev --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173. Stop any old checkout's servers occupying these ports first. Ctrl+C stops each process. No claim queue action is required: the worker picks up undecided claims automatically.

Alternatively, `bash scripts/demo.sh` prepares storage and launches all three processes together. Ctrl+C stops application processes while PostgreSQL/Redis remain running.

## API and UI

- `/api/health` reports the configured decision mode.
- `/api/jobs/active` discovers ongoing jobs and worker readiness.
- `/api/jobs/status` supplies progress/results. The dashboard keeps polling so automatic retries do not leave stale failed-job displays.
- `/api/claims` and claim details reflect final accepted/rejected outcomes.
- `/api/reviews/{id}/decisions` is disabled in autonomous mode. Historical review records remain readable for audit.
- The chatbot explains investigation and decision context with validated citations. It remains read-only; the worker, rather than chat instructions, owns execution.

## Evals and verification

Run the new Week 4 suite:

```sh
uv run --directory backend python -m app.evaluation.autonomous
```

It evaluates seven binary claim outcomes plus forced acceptance with missing evidence, low confidence and invented evidence. It uses isolated synthetic storage and reports per-case checks. Results are saved to ignored `backend/evaluation-results/week4.json`; any failed case produces exit code 1. The worker's `evaluate` function uses this suite.

Optional live Vertex eval:

```sh
uv run --directory backend python -m app.evaluation.autonomous --provider vertex
```

The earlier Week 3 eval modules remain historical compatibility checks. The optional standalone Week 4 Vertex eval has not been run as part of this change; live Vertex was verified through the browser workflow instead.

Browser eval:

```sh
pnpm --dir frontend exec playwright test
DEMO_TEST_VERTEX=1 pnpm --dir frontend exec playwright test
```

The browser test creates isolated storage and a queue, starts the worker and waits for all seven decisions without clicking Run or submitting a manager decision. It checks binary outcomes, refresh persistence, visible AI investigation/final decision, inline chat and decision history. Test servers shut down automatically.

Backend tests also cover missing receipts despite a forged accept response, low confidence, invalid investigation output, stale sources, autonomous closure of historical reviews, API rejection of human decisions, startup/recurring discovery, new claims arriving after startup, queue namespace isolation, retry cooldown and AI-only memory. Week 3 regression fixtures explicitly retain the older decision mode.

Implementation references: [ARQ cron scheduling](https://arq-docs.helpmanual.io/#cron-jobs). The recurring scanner uses its unique five-second cron scheduling; the claim-job namespace and business version checks provide separate deduplication and concurrency controls.

## Main code changes

- `backend/app/agents/claim_agent.py`: investigation stage before final assessment.
- `backend/app/ai/gateway.py`: structured investigator output, binary autonomous assessment and source validation.
- `backend/app/assessment/service.py`: final binary decision controls, investigation/audit persistence and automatic legacy-review closure.
- `backend/app/jobs/worker.py`: startup discovery, recurring scan, isolated versioned IDs and cooldown recovery.
- `backend/app/bootstrap.py`: separate local Week 4 database initialization.
- `backend/app/evaluation/autonomous.py`: Week 4 eval runner.
- `frontend/src/features/claims/ClaimQueue.tsx`: autonomous monitor and decision history.
- `frontend/src/features/claims/ClaimDetail.tsx`: visible AI investigation and final decision.
- `docs/policies/README.md`: policy v2 for autonomous evidence-based outcomes.

## Verification results

Final regression run: **76 backend tests passed**, including isolated PostgreSQL concurrency and Redis integration; **11 frontend tests passed**; **10/10 autonomous evals passed**. Backend/frontend lint and frontend build passed. The final offline browser test passed. The live Vertex browser scenario completed all seven binary decisions and grounded chat without Run clicks or human decisions. Week 4 storage/index was prepared separately. Verification API/frontend/worker processes were shut down after tests.
