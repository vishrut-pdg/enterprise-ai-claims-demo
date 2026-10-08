#!/bin/bash
# Launch this checkout's frontend, API and worker as one managed demo.
set -euo pipefail
DEMO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DEMO_ROOT"
for port in 8000 5173; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already occupied. Stop the existing dev server first."
    exit 1
  fi
done
if [[ ! -x backend/.venv/bin/python || ! -d frontend/node_modules ]]; then
  echo "Install first: (cd backend && uv sync --extra gcp) && (cd frontend && pnpm install)"
  exit 1
fi
docker compose -p enterprise-ai-claims up -d --wait postgres redis
(cd backend && .venv/bin/python -m app.bootstrap && .venv/bin/python -m alembic upgrade head && .venv/bin/python -m app.seed)
RAG_ON="$(cd backend && .venv/bin/python -c 'from app.config import get_settings; print(int(get_settings().rag_enabled))')"
if [[ "$RAG_ON" == "1" ]]; then
  (cd backend && .venv/bin/python -m app.rag.index --if-needed)
fi
DEMO_CHILDREN=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${DEMO_CHILDREN[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
  for pid in "${DEMO_CHILDREN[@]}"; do wait "$pid" 2>/dev/null || true; done
  echo "Demo frontend, API and worker stopped."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
(cd backend && exec .venv/bin/python -m arq app.jobs.worker.WorkerSettings) &
DEMO_CHILDREN+=("$!")
(cd backend && exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
DEMO_CHILDREN+=("$!")
(cd frontend && exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort) &
DEMO_CHILDREN+=("$!")
echo "Demo checkout: $DEMO_ROOT"
echo "Open http://127.0.0.1:5173 — Ctrl+C stops all three processes."
# Exit if any component dies; the trap cleans up the remaining processes.
while true; do
  for pid in "${DEMO_CHILDREN[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "A demo component exited. Check its log above."
      exit 1
    fi
  done
  sleep 1
done
