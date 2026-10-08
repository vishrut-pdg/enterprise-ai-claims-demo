# Week 3 evals

## Run the offline suite

From the updated worktree:

```sh
cd /Users/vishrut/.codex/worktrees/dfbe/enterprise-ai-claims
uv run --directory backend python -m app.evaluation.suite
```

The runner prints a pass count and saves `backend/evaluation-results/latest.json`. It exits 0 only if every check passes; failures exit 1 and list failed case IDs/checks. The report contains per-case checks, durations, group counts, pass rate and model identity. Generated reports are ignored by Git. Use `--output /path/report.json` to save elsewhere.

The default uses deterministic mock generation/embeddings and fresh in-memory SQLite databases. It does not modify your demo claims, PostgreSQL or Redis, and requires no cloud credentials. It evaluates application controls and plumbing, not the quality of a cloud model.

| Group | Cases | What is graded |
|---|---:|---|
| RAG | 5 | Policy ingestion, receipt/currency/date retrieval at rank 1, source traceability and policy isolation |
| Batch outcomes | 7 | Each seeded claim's expected final status, finding/evidence references, RAG trajectory and review creation |
| Chat | 3 | Receipt explanation, refusal to execute an approval, read-only state and rejection of invented citations |
| Manager review | 1 | Review closure, final acceptance and reviewed outcome memory |
| Guardrails | 3 | Unknown finding/evidence rejection and low-confidence acceptance routed to investigation |
| Regression | 1 | The six existing baseline scenarios, including unsafe acceptance, malformed output and stale version |

Ground truth lives in `backend/app/evaluation/datasets/demo.json`; the original cases remain in `datasets/cases.json`. Add cases there and update suite handlers for new kinds of checks. All seven claim workflow outcomes are tested; the actual HTTP queue, worker lifecycle and UI are checked by the browser eval below.

## Evaluate live Vertex and RAG

```sh
uv run --directory backend python -m app.evaluation.suite \
  --provider vertex --output evaluation-results/vertex.json
```

This uses the current `.env` project/model/embedding configuration and ADC. It embeds the policy and submits synthetic seeded claim and chat contexts to Vertex, incurring normal API usage. Storage remains isolated. It checks the real model's outcomes and retrieval plus policy passage citations in chat; forced invalid-output cases still use controlled mock responses to test safeguards. Changed answers or retrieval rankings can produce failures, which are recorded rather than silently accepted.

Retrieval uses heading matches at rank 1. Chat relevance/refusal uses explicit keyword checks plus source validation and unchanged business state. These are transparent behavioral heuristics, not a comprehensive semantic or prompt-injection benchmark; inspect the cases and add independent fixtures as coverage grows.

## Browser batch eval

Keep Redis running, then:

```sh
pnpm --dir frontend exec playwright test
```

This creates an isolated database and queue, launches its own API/worker/frontend, and verifies Run → Running → Finished, all seven outcomes, refresh persistence, inline claim chat and manager review. Test servers stop automatically. Screenshots and failure traces are under `frontend/test-results/`.

For the same browser scenario using real Vertex generation and policy embeddings:

```sh
DEMO_TEST_VERTEX=1 pnpm --dir frontend exec playwright test
```

## Regression checks

```sh
uv run --directory backend pytest -q
pnpm --dir frontend test --run
```

The suite itself is tested for a fully passing run and a deliberately wrong expectation: failures are reported and remaining cases continue.
