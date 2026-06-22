# Sikto API — FastAPI + uv.  Build from apps/api:
#   docker build -t sikto-api apps/api
# Provide config at runtime (DB + keys), e.g.:
#   docker run -p 8000:8000 --env-file apps/api/.env -e POSTGRES_HOST=host.docker.internal sikto-api
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# uv — the Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app

# Dependencies first (cached layer): lockfile + project metadata only.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# Only the files needed to run — keeps .env / .venv / tests out of the image.
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# Playwright/Chromium that Crawl4AI uses for URL scraping. Heavy (~400MB) — drop
# this line if you never ingest lessons from URLs.
RUN crawl4ai-setup || true

EXPOSE 8000
# Apply migrations, then serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
