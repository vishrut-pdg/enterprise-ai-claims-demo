# Enterprise AI Claims — Week 4

A locally running reference for claim retrieval, deterministic policy checks, structured AI assessment, controlled execution, manager review, outcome memory, evaluation and audit. The product and architecture constraints remain frozen in `docs/PRD.md` and `docs/ARCHITECTURE.md`. Implementation decisions and verification are in `docs/IMPLEMENTATION_PLAN.md`.

## Prerequisites

Docker Desktop running, uv with Python 3.12, Node (tested with 26.5.0), and pnpm 11.19.0. Use the checked-in uv and pnpm lockfiles. PostgreSQL and Redis run in Docker; application processes run on the host.

Native Ollama is the default model runtime at localhost:11434. Install/run Ollama and make the configured `LLM_MODEL` available before selecting it. This host has no Ollama installation, so live Ollama inference was not verified. The credential-free mock path below is fully verified and provides deterministic demonstrations.

## Local setup

From the repository root:

```bash
cp .env.example .env
docker compose up -d
```

Backend terminal:

```bash
cd backend
uv sync --python 3.12
uv run alembic upgrade head
uv run python -m app.seed
LLM_PROVIDER=mock uv run fastapi dev app/main.py --host 127.0.0.1
```

The last command uses the mock provider for an immediately reproducible walkthrough. Once native Ollama is ready, omit the `LLM_PROVIDER=mock` override to use the `.env` provider/model. Configuration is loaded from root `.env`, with environment variables taking precedence. The default model target is `gemma4:e4b-it-q4_K_M`; no code depends on that name.

Separate worker terminal:

```bash
cd backend
LLM_PROVIDER=mock uv run arq app.jobs.worker.WorkerSettings
```

Use the same provider settings for API and worker. Synchronous assessment needs no worker. Batch assessment enqueues Redis jobs, retries model failures up to three attempts, and skips already processed claims. The worker also exposes the `evaluate` job. Redis failure returns an explicit error and does not prevent synchronous actions.

Frontend terminal:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open [Claims desk](http://localhost:5173). API and interactive endpoint docs are at [localhost:8000/docs](http://localhost:8000/docs). Vite proxies `/api` to the backend. For a separately hosted frontend, set `VITE_API_URL` to the HTTPS backend API prefix and configure `CORS_ORIGINS` as a JSON array.

| Service | Port |
| --- | --- |
| Frontend | 5173 |
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Native Ollama | 11434 |

The database and Redis ports are bound to loopback. Database credentials in the Compose example are local development values.

## Walkthrough

Seeding is idempotent and never overwrites existing claim decisions. A fresh database receives three submitted claims:

| Claim | Scenario | Mock outcome |
| --- | --- | --- |
| CLM-001 | Supported client lunch | Accepted |
| CLM-002 | Non-reimbursable personal entertainment | Rejected |
| CLM-003 | Taxi with missing verified receipt | Pending manager review |

Open each claim and choose **Assess & process**. The screen separates source facts, policy, deterministic findings and AI interpretation. Clear cases execute automatically only when policy permits them. Open CLM-003's manager review, enter a rationale, and Accept, Reject or Request information. Information requests remain active and can be followed by a final decision. Closed reviews remain available through the queue's **Include closed reviews** filter. The claim displays its final outcome and audit history.

Reviewed final decisions become retrieval memory for future claims in the same expense category. Automatic outcomes are recorded but excluded from reviewed-memory retrieval. Memory does not fine-tune a model or override current policy. Receipt evidence is seeded text with verified metadata; this reference does not implement receipt upload, OCR or employee submission.

## Execution controls and boundaries

Thin FastAPI routes delegate to `ClaimService`; repositories encapsulate SQLAlchemy. The ADK `ClaimAgent` runs a small bounded trajectory: get claim → policy → evidence → calculate checks → retrieve reviewed outcomes → gateway assessment → controlled application action. It receives tools, never a session. ADK sessions/events orchestrate the run; model inference uses the internal gateway for every provider.

Amounts use decimal arithmetic. Rules check positive amounts, line totals, currency, limits, categories, receipt coverage, dates and receipt fingerprints. Currency mismatch/duplicates/missing receipts require investigation. Forbidden category, invalid amount/date and excess limits provide explicit rejection conditions. An automatic action requires confidence at least 0.9, no unresolved questions, current claim version, unchanged source context, current deterministic checks and policy permission. Automatic rejection must reference an actual rejection finding. Unsupported recommendations create human review, never an unchecked decision.

PostgreSQL row locks and SQLAlchemy optimistic versions prevent competing actions. A partial unique index enforces one active review per claim. Transactions persist decisions, outcomes and audit together. Invalid JSON, invalid references, timeouts and provider failures leave business status unchanged and record safe error codes. Version conflicts return 409; invalid requests 422; provider failures 502; queue/database outages 503.

The UI deliberately runs as a **trusted local manager**. `X-Role` and `X-Actor` demonstrate role boundaries, not authentication. A production identity provider and authorization model are required before exposing this reference publicly. Claim lines/evidence/policies have no public editing endpoint; internal source snapshot checks also detect changes outside the claim version.

## Provider configuration

| Provider | Required configuration | Verification |
| --- | --- | --- |
| mock | `LLM_PROVIDER=mock`, any model label | Full workflow, evaluation and E2E |
| Ollama | `LLM_PROVIDER=ollama`, `LLM_MODEL`, `OLLAMA_BASE_URL` | HTTP request/response contract tested; live model unavailable |
| Vertex AI | `LLM_PROVIDER=vertex`, model, `GCP_PROJECT_ID`, `GCP_LOCATION`, application default credentials | SDK adapter contract tested without credentials; live inference unverified |
| SAP BTP AI | `LLM_PROVIDER=btp`, model, `BTP_AI_BASE_URL`, `BTP_AI_DEPLOYMENT_ID`, OAuth settings, resource group | OAuth and inference wire contracts tested; live inference unverified |

The SAP adapter targets an Azure OpenAI chat-completions deployment in SAP AI Core/Generative AI Hub. Other Hub model wire formats or orchestration deployments require an adapter extension. `BTP_AI_BASE_URL` is the AI API base URL (before `/v2`); `BTP_TOKEN_URL` is the full OAuth token endpoint. Provider SDKs/authentication stay inside adapters. Cloud `health()` methods report configuration readiness, not a credential/inference probe. `.env` is ignored; never commit credentials.

## Tests and evaluation

Backend:

```bash
cd backend
uv run pytest -q
uv run ruff check app tests
uv run python -m app.evaluation.run
uv run python -m app.evaluation.trajectory.export
```

The normal suite uses mock providers and isolated SQLite and needs no cloud credentials. PostgreSQL/Redis tests are opt-in; they create temporary schemas/queues and preserve demo data:

```bash
TEST_POSTGRES_URL=postgresql+psycopg://claims:claims@localhost:5432/claims \
TEST_REDIS_URL=redis://localhost:6379/0 uv run pytest -q
```

Frontend:

```bash
cd frontend
pnpm test
pnpm lint
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

Playwright launches a fresh temporary SQLite/mock backend on 8001 and frontend on 5174, so it does not alter demo data. The E2E path covers automatic acceptance/rejection, investigation, manager acceptance, outcome and audit. Screenshot and failed traces are written under ignored `test-results/`.

The version-controlled evaluation dataset covers policy/evidence retrieval, claim version, tool trajectory, grounding, unsafe-action escalation, human-review boundaries, invalid output and stale versions. The trajectory exporter produces a schema-validated Google ADK EvalSet. Behavioral safety assertions run separately because trajectory similarity alone cannot verify transaction controls. ADK native model-based scoring has not been run.

## Telemetry and portability

Every HTTP response supplies `X-Correlation-ID`; a valid UUID supplied in the request is propagated. Audit and AI execution records include the run ID, tool trajectory, provider/model, status, timing and safe error code. OpenTelemetry spans cover HTTP, workflow, agent, model, tools, controlled services and SQL execution. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP HTTP collector to export traces. SQL statements/parameters and credentials are not logged. Exporter delivery is not verified here.

`deployment.yaml` records the deployment contract. `deploy/local/`, `deploy/btp/` and `deploy/gcp/` contain minimal platform descriptors, with a root Dockerfile for the API. The BTP buildpack's locked dependencies are exported to `backend/requirements.txt`; the runtime template is under `deploy/btp/`. Cloud deployment still needs real PostgreSQL/Redis bindings, secure secrets, identity/IAM, networking, frontend hosting and a persistent worker. Cloud descriptors and Docker image build are unverified; the application itself remains platform-neutral.
