# Enterprise AI Claims — Week 4

Week 4 investigates expense claims and records **Accept or Reject automatically**. No Run click, manager review or human approval is required. The worker discovers undecided claims at startup and every five seconds. Claim pages show the AI investigation, evidence gaps, final decision and audit trail.

Week 3 remains on its separate branch. Week 4 uses the separate `claims_week4` database and `claims-week4` Redis queue. See [Week4.md](docs/Week4.md) for the architecture, decision policy, isolation, manual setup and evals. [Week3.md](docs/Week3.md) records the completed earlier scope.

## Local setup

Prerequisites: Docker Desktop, uv/Python 3.12, Node and pnpm. Use the checked-in lockfiles. Run commands from the Week 4 worktree.

```sh
cp .env.example .env  # Only when a local .env does not already exist.
(cd backend && uv sync --extra gcp)
(cd frontend && pnpm install --frozen-lockfile)
docker compose -p enterprise-ai-claims up -d --wait postgres redis
uv run --directory backend python -m app.bootstrap
uv run --directory backend alembic upgrade head
uv run --directory backend python -m app.seed
```

For an offline demo, configure `LLM_PROVIDER=mock` and `RAG_ENABLED=false` in root `.env`. For Vertex, authenticate with `gcloud auth application-default login` and configure:

```dotenv
LLM_PROVIDER=vertex
LLM_MODEL=gemini-2.5-flash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=asia-south1
RAG_ENABLED=true
EMBEDDING_PROVIDER=vertex
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_LOCATION=us-central1
DECISION_MODE=autonomous
DATABASE_URL=postgresql+psycopg://claims:claims@localhost:5432/claims_week4
ARQ_QUEUE_NAME=claims-week4
AUTONOMOUS_RETRY_SECONDS=300
```

Generation and embedding locations are configurable. After enabling RAG, index the autonomous policy:

```sh
uv run --directory backend python -m app.rag.index --if-needed
```

## Start manually

Use three terminals, each at this repository root:

```sh
# API
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```sh
# Autonomous worker — processing starts automatically
uv run --directory backend arq app.jobs.worker.WorkerSettings
```

```sh
# Frontend
pnpm --dir frontend dev --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173. Ctrl+C stops each process. Alternatively, `bash scripts/demo.sh` prepares storage/indexes and starts all three together. Stop old checkout servers occupying the same ports first.

The API's `/api/health` reports decision mode; `/api/jobs/active` reports worker availability and ongoing jobs. An API running without the worker does not process claims. The dashboard shows offline status explicitly and monitors technical retries.

## Demo outcomes

Seeding adds missing examples without overwriting existing decisions.

| Claim | Expense | Amount | Autonomous outcome |
|---|---|---:|---|
| CLM-001 | Client lunch | USD 84.50 | Accepted |
| CLM-002 | Personal entertainment | USD 125.00 | Rejected |
| CLM-003 | Taxi, verified receipt missing | USD 62.00 | Rejected after investigation |
| CLM-004 | Office stationery | USD 48.25 | Accepted |
| CLM-005 | Conference rail ticket | USD 186.00 | Accepted |
| CLM-006 | Hotel above allowance | USD 680.00 | Rejected |
| CLM-007 | Team lunch, verified receipt missing | USD 115.00 | Rejected after investigation |

Open CLM-003 to inspect the AI investigation, unmet receipt requirement, final rejection and audit. Ask its inline chatbot to explain the missing evidence. Decision history lists accepted/rejected claims; no manager controls are exposed.

## Controls and architecture

FastAPI routes call application services; agents retrieve through tools; repositories own SQL access. The bounded ADK workflow retrieves facts/checks and policy passages, calls the model for investigation, validates references, calls it for a binary assessment, then revalidates source facts and claim version before committing a decision.

Acceptance requires all deterministic checks to pass, complete evidence references, both model stages supporting acceptance with confidence >=0.90, no unresolved requirements and enabled policy automation. Unmet evidence requirements produce rejection under the [autonomous policy](docs/policies/README.md). The AI cannot invent receipts or external verification. Technical failures remain undecided and retry automatically after cooldown; an outage is not a policy violation.

PostgreSQL pgvector stores 768-dimensional policy embeddings and performs cosine retrieval filtered to the applicable policy/model. Retrieved passages and prior AI outcomes support reasoning but cannot override current checks. Investigation, final decision, outcome and execution trajectory are auditable. The chatbot explains supplied records with validated citations and cannot mutate claims.

The original [PRD](docs/PRD.md) and [architecture](docs/ARCHITECTURE.md) are historical Week 3 references. The user's Week 4 scope change and implementation are documented in [Week4.md](docs/Week4.md) and [the implementation plan](docs/IMPLEMENTATION_PLAN.md). Provider adapters for mock, Ollama, Vertex and BTP are retained. Existing deployment templates remain in the repository; this change prepares local operation rather than provisioning cloud resources.

## Evals and tests

```sh
# Ten autonomous evals: binary outcomes and adversarial output controls
uv run --directory backend python -m app.evaluation.autonomous
# Optional model-quality run with configured Vertex credentials
uv run --directory backend python -m app.evaluation.autonomous --provider vertex
# Backend and frontend regression tests
uv run --directory backend pytest -q
pnpm --dir frontend test --run
# Real worker/browser scenario, no Run or approval clicks
pnpm --dir frontend exec playwright test
# Same scenario with live Vertex generation and policy RAG
DEMO_TEST_VERTEX=1 pnpm --dir frontend exec playwright test
```

Eval reports are generated under ignored `backend/evaluation-results/`. Evals use isolated synthetic storage and fail with exit code 1 when checks fail. Browser tests use isolated databases/queues and automatically stop their test servers. The older Week 3 eval suite remains available for historical compatibility.

Validated during this change: 76 backend tests with PostgreSQL/Redis integration, 11 frontend tests, 10/10 autonomous evals, lint/build, offline browser flow and live Vertex no-click processing of all seven claims with grounded chat.
