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
