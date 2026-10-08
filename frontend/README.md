# Claims desk frontend

React + TypeScript + Vite, Tailwind/shadcn, TanStack Query and TanStack Table v8.

From this directory: `pnpm install --frozen-lockfile`, then `pnpm dev`.
The frontend runs at localhost:5173 and proxies `/api` to localhost:8000.

Checks: `pnpm test`, `pnpm lint`, `pnpm build`, `pnpm test:e2e`.
The browser suite requires backend `uv sync` and `pnpm exec playwright install chromium`.

See the root README for the full runtime, provider configuration, test isolation and local-role limitations.
