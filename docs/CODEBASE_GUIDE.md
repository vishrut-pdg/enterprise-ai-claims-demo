# Codebase walkthrough

Start in `frontend/src/App.tsx`: it chooses the claim queue, detail or manager review screen. `frontend/src/api/client.ts` defines the HTTP calls. The chatbot is `components/ClaimsAssistant.tsx`.

## Processing one claim

1. The detail screen POSTs the claim ID and expected version to `backend/app/api/routes.py`.
2. `workflows/process_claim.py` builds the ADK agent with claim tools and the selected model adapter.
3. `agents/claim_agent.py` follows a fixed retrieval sequence. `tools/claims.py` calls the application service, not SQL directly.
4. `assessment/service.py` loads facts and computes checks. With RAG enabled it asks the policy retrieval service for supporting passages before inference.
5. `ai/gateway.py` constructs a constrained JSON schema, calls the provider and validates references. Provider SDKs live under `ai/providers/`.
6. The service rechecks claim version, policy and evidence before recording a controlled decision or opening manager review. Model text cannot execute arbitrary actions.

## RAG: indexing and retrieval

`docs/policies/README.md` is the human-readable source. `python -m app.rag.index` splits it into Markdown sections, embeds each section, and atomically replaces only that policy's index. `db/models/__init__.py` defines `PolicyChunk`: policy ID, passage text, source, hash, embedding model identity and a 768-dimensional vector. PostgreSQL stores the actual vectors using pgvector.

`rag/embeddings.py` uses Vertex ADC with `gemini-embedding-001`; document and query embeddings use different retrieval task types. The mock adapter is deterministic and only for offline tests. `rag/repository.py` filters to applicable policy IDs and the exact embedding model identity, then orders by cosine distance in PostgreSQL and returns four passages. Exact search is appropriate for this small policy corpus; no approximate index is needed yet.

`rag/service.py` releases the database transaction before awaiting cloud embeddings. The assessment gets passages alongside its deterministic checks. `assistant/service.py` retrieves passages using the user's question and permits citations only to supplied source IDs. Enabling RAG with a missing index fails explicitly rather than pretending retrieval happened. RAG does not replace the policy rules or the reviewed-outcome memory.

## Batch jobs

The queue POSTs submitted IDs to `/api/jobs/assess`. `jobs/worker.py` checks the ARQ worker heartbeat, enqueues unique jobs and exposes `/api/jobs/status`. Redis stores queue/results; the worker runs the same controlled claim workflow. The queue polls every 1.5 seconds and shows running, queued and terminal results. Job IDs survive refresh/navigation in session storage for the browser tab. Keep the ARQ worker running alongside FastAPI. API startup alone does not start a worker.

## Persistence and tests

`db/repositories/claims.py` owns claim queries; `db/session.py` creates sessions. Alembic migrations create schema; seeding adds missing demo claims without clearing decisions. Tests use isolated SQLite or temporary PostgreSQL schemas, and E2E uses an isolated database/queue. Read `test_workflow.py`, `test_batch.py`, and `test_rag.py` for the important boundaries.

## One-command demo

Use `bash /Users/vishrut/.codex/worktrees/dfbe/enterprise-ai-claims/scripts/demo.sh`. The launcher selects this checkout, starts the pgvector PostgreSQL image and Redis using the existing compose project, applies migrations, adds missing seeds, refreshes the policy index only when needed, and starts the API, worker and frontend together. Open `http://127.0.0.1:5173`. Ctrl+C stops all three application processes; database services stay running. Stop old servers occupying 8000 or 5173 first.

The queue button displays **Run → Running → Finished**. Every job exposes queue/worker state and its final claim outcome. Active Redis jobs are discovered even if they were submitted by the old UI or browser storage was cleared. Failed jobs have explicit errors; use **Start another batch** for claims still submitted. Claim pages show the chatbot inline and refresh while awaiting batch results; they have no individual processing button. The floating assistant is retained on queue/review screens. Audit JSON is available under collapsed event details.

The seven-claim demo should accept CLM-001/004/005, reject CLM-002/006 and refer CLM-003/007 for manager review under the reference policy. Use the missing-receipt question in CLM-003 to demonstrate RAG, then open manager review, enter rationale and record the final decision.

## Local setup from this checkout

Run commands from this worktree, not the original PDG checkout. Install dependencies with `cd backend && uv sync --extra gcp`; frontend uses `pnpm install`.

```sh
# From repository root; use the SAME compose project as your existing DB.
docker compose -p enterprise-ai-claims up -d --wait postgres redis
cd backend
uv run alembic upgrade head
uv run python -m app.seed
uv run python -m app.rag.index
```

Configure root `.env`: `RAG_ENABLED=true`, `EMBEDDING_PROVIDER=vertex`, `EMBEDDING_MODEL=gemini-embedding-001`, `EMBEDDING_LOCATION=us-central1`, plus existing `GCP_PROJECT_ID`, `LLM_PROVIDER=vertex`, `LLM_MODEL=gemini-2.5-flash` and ADC from `gcloud auth application-default login`. Generation and embeddings can use different regions. Reindex after changing the embedding model or policy document.

In separate terminals, from `backend`, run `uv run arq app.jobs.worker.WorkerSettings` and `uv run fastapi dev app/main.py`; from `frontend`, run `pnpm dev`. Stop all three with Ctrl+C when finished. If port 5432 is already served by the original checkout's compose project, update that existing project rather than creating a competing database. Preserve its named volume; never use `down -v` to upgrade the image.

Implementation references: [Vertex text embedding API](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings) and [pgvector distance operators](https://github.com/pgvector/pgvector). The implementation uses 768 output dimensions and PostgreSQL cosine distance.
