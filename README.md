# Sikto

Turns a source (text, URL, or YouTube link) into a narrated micro-lesson video.
A monorepo of four services orchestrated by Turborepo + pnpm.

```
sikto/
├── apps/
│   ├── web/      Next.js 16 + React 19 + Tailwind v4  (UI, port 3000)
│   ├── api/      FastAPI + async SQLAlchemy + pgvector (backend + job worker, port 8000)
│   ├── render/   Remotion video renderer (tsx service, port 8001)
│   └── tts/      FastAPI + edge-tts neural voiceover  (port 8002)
├── packages/     shared TS packages (e.g. scene-kit)
├── pnpm-workspace.yaml
└── turbo.json
```

How a lesson is built: **API** ingests the source, an LLM ("brain") plans a
`SceneDocument`, **TTS** narrates each scene, **render** turns it into an MP4.
TTS and render are best-effort — if they're down the lesson still completes and
the web player renders the `SceneDocument` directly.

## Prerequisites

- **Node** ≥ 20 and **pnpm** ≥ 10 — `brew install pnpm`
- **uv** (Python) — `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Python** ≥ 3.12 (uv installs it if missing)
- **Postgres** ≥ 14 with the `pgvector` extension — `brew install postgresql@17 pgvector`

## Setup

```bash
pnpm install                          # JS workspace deps
cd apps/api && uv sync && cd -        # API Python deps (creates apps/api/.venv)
cd apps/tts && uv sync && cd -        # TTS Python deps

# env files (all real .env* are gitignored — only *.example is committed)
cp apps/api/.env.example       apps/api/.env
cp apps/web/.env.local.example apps/web/.env.local
```

Then fill in `apps/api/.env`:

- `JWT_SECRET` — generate with `cd apps/api && make secret` (or `openssl rand -hex 32`)
- `DEEPSEEK_API_KEY` (default agent provider) and `AI_GATEWAY_API_KEY` (embeddings)
- `POSTGRES_*` or a full `DATABASE_URL`

Database (the API has a shortcut: `cd apps/api && make setup` does deps + DB + migrations).
Use the `POSTGRES_*` values from your `apps/api/.env` in place of the placeholders below:

```bash
cd apps/api
createuser <db-user> --createdb 2>/dev/null || true
psql -c "ALTER USER <db-user> WITH PASSWORD '<db-password>';"
createdb <db-name> -O <db-user> 2>/dev/null || true
psql -d <db-name> -c "CREATE EXTENSION IF NOT EXISTS vector;"
uv run alembic upgrade head
```

## Secrets

All API keys and DB credentials come from `.env` files — nothing is hardcoded in
source. Keys belong **only in `apps/api/.env`** (the web app reads none). Never
commit a `.env`; edit the `*.example` templates instead. In `production`
(`ENVIRONMENT=production`) the API refuses to start with the default `JWT_SECRET`.

## Run

```bash
pnpm dev          # all four services (web + api + render + tts)
pnpm dev:web      # web only            → http://localhost:3000
pnpm dev:api      # api + render + tts   → http://localhost:8000
pnpm dev:api-only # api only (no render/tts; lessons skip video/voiceover)
```

| Service | URL                     | Notes                                              |
| ------- | ----------------------- | -------------------------------------------------- |
| web     | http://localhost:3000   | proxies browser calls to the API via `/api` rewrite |
| api     | http://localhost:8000   | runs the job worker in-process (`RUN_WORKER`)       |
| render  | http://localhost:8001   | no auto-reload — restart after editing `server.ts`  |
| tts     | http://localhost:8002   | edge-tts (free, no key); narrates scenes            |

Postgres must be running: `brew services start postgresql@17`.

## Quality

```bash
# JS / TS (from repo root)
pnpm lint
pnpm typecheck
pnpm format          # Prettier write

# Python (from apps/api)
uv run ruff check . && uv run ruff format .
uv run mypy .
make test            # full suite against a separate sikto_test database
uv run pytest tests/test_auth_manager.py   # unit tests, no database
```
