# Enterprise AI Claims — Week 3

Week 3 combines AI expense assessment with controlled automation and manager review. The AI recommends **accept, reject or investigate**. The application automatically executes eligible, well-supported accept/reject recommendations; uncertainty and missing evidence go to a manager. A read-only chatbot answers clarifying questions, and policy RAG supplies relevant passages from PostgreSQL.

This branch includes seven sample expenses, live batch progress, reviewed-outcome memory, evaluations, audit history and an **AI usage & performance** dashboard. Week 3 retains human oversight for escalated cases. Its workflow differs from Week 1's fact summaries, Week 2's mandatory manager decisions and Week 4's autonomous investigation/decision workflow.

## Start from the correct checkout

Run every command from the checkout containing the `week-3` branch:

```sh
pwd
git branch --show-current
```

The branch must print `week-3`. If it is already checked out in a separate Git worktree, use that directory; `git worktree list` shows its location. Starting an older checkout's frontend or backend can display stale controls even when another worktree has the updated code.

## Install and prepare

Prerequisites: Docker Desktop running, Python 3.12 with uv, Node.js and pnpm. The project uses checked-in lockfiles; development has been verified with Node 26.5.0 and pnpm 11.19.0. PostgreSQL/Redis run in Docker; the API, worker and frontend run on the host.

From the repository root:

```sh
# New checkout only: keep an existing .env rather than overwriting it.
cp .env.example .env
uv sync --directory backend --python 3.12 --extra gcp
pnpm --dir frontend install --frozen-lockfile
docker compose -p enterprise-ai-claims up -d --wait postgres redis
uv run --directory backend alembic upgrade head
uv run --directory backend python -m app.seed
```

Week 3 defaults to database `claims` and queue `claims`. API and worker must use the same `.env`, database, provider/model and `ARQ_QUEUE_NAME`. Root `.env` is loaded regardless of whether the backend starts from the repository root or its own directory; process environment variables take precedence. `.env` is ignored by Git.

Seeding adds missing sample claims without resetting existing assessments, decisions or history. Apply all migrations, including `ai_usage_events`, before processing claims or using chat.

## Run the complete demo

For a credential-free demonstration with deterministic mock generation and RAG disabled:

```sh
LLM_PROVIDER=mock LLM_MODEL=week3-demo RAG_ENABLED=false bash scripts/demo.sh
```

For your configured provider and RAG settings:

```sh
bash scripts/demo.sh
```

The launcher starts PostgreSQL/Redis, migrates and seeds the database, refreshes the policy index when RAG is enabled, then starts the API, ARQ worker and frontend. Open [Claims desk](http://127.0.0.1:5173). Ctrl+C stops all three application processes; PostgreSQL and Redis remain running.

## Run manually without the demo script

After completing the preparation steps, use three terminals from the same repository root.

**Backend:**

```sh
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Batch worker:**

```sh
uv run --directory backend arq app.jobs.worker.WorkerSettings
```

**Frontend:**

```sh
pnpm --dir frontend dev --host 127.0.0.1 --port 5173 --strictPort
```

These commands use `.env`. For mock operation, prefix **both backend and worker commands** with `LLM_PROVIDER=mock LLM_MODEL=week3-demo RAG_ENABLED=false`. The frontend needs no provider override.

Check readiness with:

```sh
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/jobs/active
```

Wait for `worker_available: true` before starting a batch. A running API alone does not start the worker. **HTTP 202 means queued, not completed**; the frontend polls job status and refreshes claim/review data as jobs finish. A missing worker or unavailable Redis produces an explicit error.

Frontend: [127.0.0.1:5173](http://127.0.0.1:5173). API docs: [127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Vite proxies `/api` to port 8000. Ports 5432 (PostgreSQL) and 6379 (Redis) are bound to loopback. For a separately hosted frontend, configure `VITE_API_URL` and `CORS_ORIGINS`.

Press Ctrl+C in each application terminal to stop its process. To stop the database services without deleting their volume:

```sh
docker compose -p enterprise-ai-claims stop postgres redis
```

## Demo walkthrough

1. Open **Claim queue** and press **Run**. The control transitions **Run → Running → Finished**, with running/queued counts, completion progress, individual job results and failures. Batch IDs are unique; retryable provider failures can make up to three attempts.
2. Open a claim to inspect source facts, applicable policy, evidence, deterministic findings, AI interpretation, outcome and audit history. There is no per-claim **Assess & process** button; start assessments from the queue.
3. Use the inline **Ask about this claim** chatbot for clarifying questions. For CLM-003, ask **What evidence is missing?** Answers cite validated source IDs. Queue and review screens also have a floating assistant.
4. Open CLM-003's manager review, enter a rationale, and choose **Accept**, **Reject** or **Request information**. Accept/Reject confirms completion and closes the review; an information request leaves it active. Closed reviews remain available through **Include closed reviews**.
5. Open **AI usage & performance** below Manager review to inspect run outcomes, latency, token usage and estimated costs. The page refreshes every five seconds and supports date/provider filters and searchable histories.

Expected outcomes with a fresh database, the mock provider and the seeded policy:

| Claim | Scenario | Expected outcome |
| --- | --- | --- |
| CLM-001 | Supported client lunch | Accepted |
| CLM-002 | Personal entertainment | Rejected |
| CLM-003 | Airport taxi, receipt missing | Pending manager review |
| CLM-004 | Office stationery with receipt | Accepted |
| CLM-005 | Conference rail ticket with receipt | Accepted |
| CLM-006 | Hotel stay above allowance | Rejected |
| CLM-007 | Team lunch, receipt missing | Pending manager review |

Cloud-model outcomes can vary; service controls still determine whether an automatic action is allowed. Existing decisions are preserved when the app restarts.

## Agent, policy checks and memory

Thin FastAPI routes call `ClaimService`; repositories encapsulate SQLAlchemy. The bounded ADK agent retrieves the claim, policy and evidence, calculates policy checks, retrieves previous reviewed outcomes and applicable policy passages, then requests a structured assessment through the provider-neutral gateway. It receives tools, never a database session.

Deterministic checks use decimal arithmetic and validate amounts, line totals, currencies, limits, categories, receipt coverage, dates and duplicate fingerprints. Automatic execution requires confidence of at least 0.9, no unresolved questions, policy permission, current claim version and unchanged source context. Automatic acceptance requires passing checks; automatic rejection must reference a real rejection finding. Other recommendations are escalated to manager review.

PostgreSQL row locks, optimistic versions and a unique active-review index protect competing actions. Final decisions, outcomes and audit are committed together. Invalid output, invented references, timeouts and provider failures leave business status unchanged and record error codes. The local UI demonstrates manager roles using `X-Role`/`X-Actor`; these headers are not production authentication.

Reviewed final outcomes become retrieval memory for later claims in the same category. Automatic outcomes are recorded but excluded from reviewed-memory retrieval. Memory does not fine-tune the model or override current policy.

## Providers and policy RAG

Providers include mock, native Ollama, Vertex AI and an SAP BTP adapter for Azure OpenAI chat-completions deployments. SDK/authentication code stays inside provider adapters. Ollama is the `.env.example` default and requires a running local model at port 11434. Mock needs no credentials. Other SAP Hub wire formats require an adapter extension.

For local Vertex setup, project/model/region settings, ADC and indexing commands, follow [Week 3 setup](docs/Week3.md#7-local-vertex-setup-and-fixes). API and worker use the same generation configuration; embeddings can use a separate supported region.

The readable policy source is [docs/policies/README.md](docs/policies/README.md). RAG splits it into passages, generates 768-dimensional embeddings, and stores text, source IDs, content hashes and vectors in PostgreSQL/pgvector. Query-time cosine search is scoped to the current policy and embedding-model identity. Retrieved passages support explanations and chat citations; they cannot override deterministic checks or grant decision authority.

Index before enabling `RAG_ENABLED=true`:

```sh
uv run --directory backend python -m app.rag.index --if-needed
```

`EMBEDDING_PROVIDER=vertex` uses ADC and Vertex API calls. `--if-needed` avoids reindexing unchanged policy/model combinations. Missing or mismatched indexes fail explicitly. For an offline RAG demonstration, use mock generation and `EMBEDDING_PROVIDER=mock` consistently when indexing and running the app. Keep the existing PostgreSQL volume when upgrading the pgvector image.

## AI usage and performance

Open [the analytics page](http://127.0.0.1:5173/#/analytics). It separates full claim runs from generation/chat/embedding requests and shows failures, average/P95 latency, provider/model groups, tokens, estimated USD cost and expandable run traces.

A rejected expense can still be a successful AI run. Costs are provider API estimates, not a cloud bill; unknown rates or usage remain unavailable. Historical claim usage is recovered where possible, while measured chat/embedding history begins with the analytics migration. Configure `AI_COST_RATES` for different model prices. See [AI_ANALYTICS.md](docs/AI_ANALYTICS.md) for rate units, data coverage and code locations.

## Tests and evaluations

From the repository root:

```sh
uv run --directory backend pytest -q
uv run --directory backend ruff check app tests
uv run --directory backend python -m app.evaluation.suite
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```

The offline evaluation suite runs 20 cases covering RAG, all seven outcomes, chat grounding, manager review, guardrails and baseline regressions. It uses isolated SQLite/mock providers, preserves demo data, saves `backend/evaluation-results/latest.json`, and exits nonzero when checks fail. See [EVALS.md](docs/EVALS.md) for live Vertex evaluation and grading limits.

For optional isolated PostgreSQL/Redis tests, keep the services running:

```sh
TEST_POSTGRES_URL=postgresql+psycopg://claims:claims@localhost:5432/claims \
TEST_REDIS_URL=redis://localhost:6379/0 \
uv run --directory backend pytest -q
```

Browser tests require local Redis and Chromium:

```sh
pnpm --dir frontend exec playwright install chromium
pnpm --dir frontend test:e2e
```

Playwright starts a temporary SQLite/mock backend on 8001, a dedicated queue/worker and frontend on 5174. It checks seven-claim batch completion, automatic acceptance/rejection and review escalation, Run/Running/Finished, refresh persistence, claim chat, manager completion and the analytics page. It shuts down its test servers and preserves demo data. Screenshots/failure traces are under ignored `frontend/test-results/`.

The original regression runner and ADK EvalSet exporter remain available as `python -m app.evaluation.run` and `python -m app.evaluation.trajectory.export` from `backend`. Trajectory similarity alone does not verify transaction controls or model quality.

## Further reading

- [Week 3 implementation and demo notes](docs/Week3.md)
- [Codebase guide: agent, memory, RAG and services](docs/CODEBASE_GUIDE.md)
- [Evaluation coverage and commands](docs/EVALS.md)
- [AI analytics setup and implementation](docs/AI_ANALYTICS.md)
- [Original product requirements](docs/PRD.md) and [architecture](docs/ARCHITECTURE.md)

Audit/execution records and `X-Correlation-ID` link requests to tool trajectories, provider/model, timing and outcomes. OpenTelemetry spans cover HTTP, workflow, agent, tools, model and SQL execution; configure `OTEL_EXPORTER_OTLP_ENDPOINT` for an OTLP HTTP collector. Deployment descriptors live in `deployment.yaml` and `deploy/`; cloud hosting still requires service bindings, secrets, identity, networking and a persistent worker.
