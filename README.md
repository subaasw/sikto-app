# Sikto

Video automation and microlearning platform. Monorepo for the Sikto project.

```
sikto/
├── apps/
│   ├── web/   Next.js 16 + Tailwind v4 + Base UI + Vercel AI SDK
│   └── api/   FastAPI (managed by uv)
├── pnpm-workspace.yaml
├── turbo.json
└── package.json
```

## Prerequisites

- **Node** ≥ 20
- **pnpm** ≥ 10 — `brew install pnpm`
- **uv** (Python package manager) — `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Python** ≥ 3.12 (uv will install if missing)

## First-time setup

```bash
# install JS workspace deps
pnpm install

# install Python deps for the api (uv creates apps/api/.venv automatically)
cd apps/api && uv sync && cd -

# copy env files
cp apps/web/.env.local.example apps/web/.env.local
cp apps/api/.env.example      apps/api/.env
```

## Development

Run everything via Turborepo:

```bash
pnpm dev           # runs all `dev` tasks in parallel (just web today)
pnpm dev:web       # Next.js → http://localhost:3000
pnpm dev:api       # FastAPI  → http://localhost:8000
```

Or directly:

```bash
pnpm --filter web dev
cd apps/api && uv run uvicorn api.main:app --reload --port 8000
```

## Quality

```bash
# JS / TS
pnpm lint
pnpm typecheck
pnpm format          # Prettier write
pnpm format:check    # Prettier check

# Python (run from apps/api)
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```

## Stack

### Web (`apps/web`)

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS v4
- ESLint (eslint-config-next)
- Prettier + `prettier-plugin-tailwindcss`
- **Base UI** (`@base-ui-components/react`)
- `lucide-react`, `clsx`, `tailwind-merge`
- **Vercel AI SDK** (`ai`, `@ai-sdk/react`) — provider-agnostic; no provider SDK is installed

The sample agent lives at `apps/web/src/lib/agent.ts`, is served by the route handler at
`apps/web/src/app/api/chat/route.ts`, and is consumed by the `Chat` component on `/`. The model is
not hard-coded to a provider — it is read from the `AGENT_MODEL` env var and routed through the
[Vercel AI Gateway](https://vercel.com/docs/ai-gateway). Set `AGENT_MODEL` (e.g.
`anthropic/claude-sonnet-4-5`) and `AI_GATEWAY_API_KEY` in `apps/web/.env.local` to run it; swap
providers by changing the env var alone.

### API (`apps/api`)

- FastAPI (`fastapi[standard]`)
- Uvicorn
- pydantic-settings
- Dev: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `httpx`, `pre-commit`

## Adding new workspaces

```bash
# new JS app/package
mkdir apps/new-app && cd apps/new-app && pnpm init

# new Python service via uv
cd apps && uv init --name <name> --package <name>
```
