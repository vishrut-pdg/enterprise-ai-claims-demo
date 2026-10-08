# Week 4 implementation plan

## Current repository assessment
Read frozen PRD/ARCHITECTURE, .env.example and frontend/backend configuration. All backend modules are empty; frontend is Vite starter with Tailwind/shadcn (components are under an incorrect alias directory). Python >=3.12, uv lock and frontend npm lock exist. No tests, migrations, Dockerfiles, README or deployment.yaml exist. No AGENTS.md found. Host has uv, pnpm, Node 26 and Docker; default Python is 3.9, so uv must supply 3.12. Existing untracked source will be extended.

## Implementation phases
1. Configuration, entities, repositories, migrations and reproducible seeds.
2. Deterministic checks, normalized providers, validated assessment and guarded actions.
3. ADK tools, manager decisions, outcome memory, ARQ, evaluation and telemetry.
4. Enterprise frontend, tests, deployment descriptors and documentation.
5. Execute checks, repair failures and record results.

## Assumptions
Trusted local analyst/manager roles use explicit request headers; production requires real identity integration. Decimal USD amounts. Missing receipts require investigation; forbidden categories, future dates and excess amounts are explicit rejection conditions. Memory never overrides current policy. Mock enables credential-free tests.

## Dependency gaps
Add TanStack Query/Table, DOM test environment, Playwright runner. Verify uv dependency availability. Use ADK BaseAgent for bounded tool orchestration through internal gateway. SDK/auth belongs inside adapters.

## Risks
Concurrency needs row locks, optimistic versions and unique active-review constraint. Invalid/ungrounded AI must fail without decision. Redis/provider failures must be visible. Docker/Ollama/cloud access may be unavailable; report precise validation limits. Cloud descriptors require service bindings/IAM.

## Acceptance tests
Deterministic rules including duplicates/arithmetic; schema/grounding/provider contracts; guarded accept/reject/investigate; idempotency; manager history/memory; stale versions; model failures; role controls; evaluation trajectories; frontend loading/error/detail/review; Playwright investigation-to-manager-accept. Mock plus isolated SQLite for tests; PostgreSQL migrations/runtime if Docker available.

## Expected final run commands
Root: `docker compose up -d`, `cp .env.example .env`, native `ollama serve` and model pull. Backend: `uv sync`, `uv run alembic upgrade head`, `uv run python -m app.seed`, `uv run fastapi dev app/main.py`, `uv run arq app.jobs.worker.WorkerSettings`. Frontend: `pnpm install`, `pnpm dev`. Checks: `uv run pytest`, `uv run python -m app.evaluation.run`, `pnpm test`, `pnpm build`, `pnpm test:e2e`. Verification status will be recorded in the result.

## Implementation Result

### Completed capabilities
- All thirteen required SQLAlchemy entities, repository persistence, explicit Alembic migration, PostgreSQL local Compose and idempotent Accept/Reject/Investigate seeds.
- Decimal policy checks for amount validity/total/limit, receipts per line, category, currency, date and receipt duplicates. Findings are stored before model interpretation.
- Provider-neutral gateway and normalized mock/Ollama/Vertex/BTP adapters; strict Pydantic assessment and reference validation. Invalid/unavailable models fail without a business decision.
- One bounded Google ADK custom agent and service-backed retrieval/execution tools. Row locking, optimistic versions, unchanged source snapshots, confidence/uncertainty thresholds and policy permissions protect automatic actions. One active review is enforced in the database.
- Manager queue/detail, Accept/Reject/Request information, review history, transactional reviewed outcomes and category-based enterprise-memory retrieval. Prior cases cannot remove current policy requirements.
- React/TanStack Query/Table v8 frontend with shadcn/Tailwind, filtering/sorting, errors/loading, claim/evidence/policy/assessment, manager actions, outcomes and audit history.
- Redis/ARQ batch assessment, bounded retries, evaluation worker function and explicit queue outage behavior. Request correlation propagates to queued assessments.
- Six version-controlled behavior evaluation cases and a schema-validated ADK EvalSet exporter. Structured logs, correlation IDs and OpenTelemetry integration through HTTP/workflow/agent/model/tool/service/database/action.
- Local runtime documentation, root Dockerfile/deployment contract and minimal local/BTP/GCP descriptors. PRD and ARCHITECTURE were not edited.

### Tests executed
- Final backend suite with `TEST_POSTGRES_URL` and `TEST_REDIS_URL`: **38 passed**, including real PostgreSQL concurrent acceptance/investigation and a real ARQ assessment against an isolated schema/queue.
- Normal mock/SQLite tests require no cloud credentials; PostgreSQL/Redis integration tests are opt-in.
- Frontend Vitest: **5 passed**. ESLint and TypeScript/Vite production build passed.
- Playwright Chromium E2E: **1 passed**, exercising automatic accept/reject, investigation, manager acceptance, outcome and audit in a fresh temporary database.
- CLI behavior evaluation: **6/6 passed**. ADK EvalSet validation passed.
- Backend Ruff checks/format passed. Locked uv sync and pnpm install passed.
- Actual PostgreSQL `alembic upgrade head`, idempotent seed (repeated), and `alembic check` passed with no schema drift.
- FastAPI development command and ARQ worker command started successfully; frontend/API live HTTP checks returned 200. Docker PostgreSQL/Redis are running.
- Screenshot inspected for layout. Only upstream ADK/Starlette/ARQ deprecation warnings remain in test output.

### Provider status and known limitations
Mock is fully verified end to end. Ollama has a tested HTTP contract, but native Ollama/model inference cannot be verified because Ollama is absent on this host. Vertex SDK and SAP OAuth/inference contracts are tested without cloud credentials; real inference is unverified. BTP adapter supports AI Core Azure OpenAI chat deployments; other Hub formats need an adapter extension. Cloud health checks mean configuration readiness. OTLP exporter delivery, native ADK model-based scoring and Docker image build are unverified.

The local UI uses trusted manager headers, not authentication. Employee submission, receipt uploads/OCR and full policy administration are outside this teaching reference. Evidence is seeded text with verified metadata. Reviewed memory uses category retrieval, not embeddings or fine-tuning. ADK session state is per run in memory; durable business history and trajectories are persisted in PostgreSQL. Backend and frontend package lockfiles preserve the inspected stack; the older npm lockfile is not authoritative for pnpm.

### Local run instructions
Exact tested setup is in root README. PostgreSQL/Redis: `docker compose up -d`. Backend: `uv sync --python 3.12`, `uv run alembic upgrade head`, `uv run python -m app.seed`, `LLM_PROVIDER=mock uv run fastapi dev app/main.py --host 127.0.0.1`. Separate worker: `LLM_PROVIDER=mock uv run arq app.jobs.worker.WorkerSettings`. Frontend: `pnpm install --frozen-lockfile`, `pnpm dev`. A root `.env` was copied from the example; currently running processes override the model provider with mock. Default `.env` remains Ollama for a host with native Ollama/model available. Seeds never overwrite existing decisions.

### Remaining BTP/GCP deployment work
Provide real model deployments/credentials, database/Redis services, secure secret injection, authenticated reviewer identity, IAM/networking, frontend hosting and persistent worker processes. Replace GCP image/project placeholders; stage BTP Python runtime template with buildpack inputs. Apply migrations before serving traffic. Descriptors are prepared, not cloud deployments. No cloud resources were provisioned.


## UX, assistant and batch follow-up — 8 October 2026

Implemented on `week-3`: seven additive seed claims (CLM-004 through CLM-007 added to existing local data); assessment/investigation/manager completion feedback; compact read-only provider-neutral assistant with validated citations; worker heartbeat checks and explicit offline error; unique retryable batch IDs; job-status endpoint, per-claim outcomes, progress polling and automatic queue refresh. No frozen architecture/product document was changed. Existing decisions are preserved by seeding.

Verification: 48 backend tests passed including PostgreSQL/Redis integration; 8 frontend tests passed; lint and production build passed; expanded Chromium E2E verified actual four-claim ARQ processing, manager feedback and chatbot citations. Tests use mock inference and isolated schemas/queues. New chat has not been live-tested against Vertex; it uses the existing provider adapter/credentials. Dev servers and workers are shut down after validation; database services remain available.

## Policy RAG and persistent batch status

Add the readable expense policy, section-level ingestion with Vertex embeddings, a pgvector migration and cosine retrieval filtered to the applicable policy/model. Supply passages to assessment and read-only chat while retaining deterministic rule authority. Audit retrieved passages with assessment requests. Test retrieval, idempotent ingestion, model mismatch and PostgreSQL vector queries. Persist browser-tab batch job IDs and verify progress survives reload. Provide the codebase guide and shut down verification servers after completion.

Validation completed: 53 backend tests including isolated PostgreSQL/Redis checks, 8 frontend tests, browser E2E with batch reload persistence, lint and frontend build. Live Vertex policy ingestion and retrieval succeeded (five 768-dimensional vectors; receipt passage ranked first). Compared claims, assessments, reviews, decisions, outcomes, audit and executions against the pre-upgrade backup: unchanged. RAG enabled in this worktree's ignored local .env. Development servers and workers stopped; PostgreSQL/Redis remain running.

## Demo refinement

Queue controls now display Run / Running / Finished, with animated execution feedback, active Redis job discovery (including legacy jobs), per-job states/outcomes, refresh persistence and explicit offline readiness. Removed individual assessment controls and placed the chatbot inline on every claim. Collapsed verbose audit event details. Added scripts/demo.sh to start the correct checkout's API, ARQ worker and frontend, update pgvector services, migrate, seed and refresh a changed policy index; trap-based shutdown was smoke-tested with an isolated worker queue.

Validation: 54 backend tests including PostgreSQL/Redis, 11 frontend tests, lint/build and the full browser batch/chat/review scenario. The same seven-claim browser scenario passed with live Vertex AI generation and Vertex policy embeddings/RAG (7 complete, 0 failed), using an isolated test database; a final mock browser run passed as well. The expanded 15-section user policy was preserved and reindexed. Stopped old PDG checkout servers and all verification servers/workers; demo data was not reset by these checks.


## Week 4 scope change — autonomous investigation

User explicitly changed Week 4 to autonomous AI investigation with binary final decisions and no human oversight. Week 3 remains isolated in its original branch/worktree. Add a structured AI investigation before assessment; retain deterministic source checks and concurrency controls; record accept/reject rather than creating human reviews. Automatically discover undecided claims at worker startup and on a five-second cron; isolate job IDs by queue/claim/version and retry technical failures after cooldown. Provide a separate claims_week4 database and claims-week4 queue. Replace manager UI with decision history, expose investigator findings/limitations, retain read-only grounded chat and add Week 4 evals/documentation.

Mock and live Vertex browser scenarios verified automatic decisions for all seven seeded claims with no Run click or human decision request, including missing-receipt rejection, visible investigation, final decision, chat citations and history. The earlier unnamespaced automatic IDs caused a cross-queue collision in the first live check; namespace isolation was corrected and the live check passed. Week 4 database/policy index prepared separately; Week 3 data was not processed by these tests.

Final Week 4 validation: 76 backend tests with PostgreSQL/Redis passed, 11 frontend tests passed, 10/10 autonomous evals passed, lint and build passed. Final offline browser scenario passed; live Vertex no-click browser scenario passed. Prepared a separate Week 4 database and policy v2 index. Test servers/workers stopped after verification.
