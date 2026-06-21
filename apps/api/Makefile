# Sikto API — Postgres + Alembic helpers.
# Override any variable inline, e.g.  make db-create POSTGRES_DB=sikto_test

# Load config/secrets from .env (the same file the app reads) when present.
-include .env

POSTGRES_USER     ?= sikto
POSTGRES_PASSWORD ?= sikto
POSTGRES_DB       ?= sikto
POSTGRES_HOST     ?= localhost
POSTGRES_PORT     ?= 5432
PG_SERVICE        ?= postgresql@17

# alembic/env.py reads DATABASE_URL; compose it from the parts unless .env
# already provides an explicit DATABASE_URL.
export DATABASE_URL ?= postgresql+asyncpg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- setup ------------------------------------------------------------------

.PHONY: install
install: ## Install dependencies into .venv (uv sync)
	uv sync

.PHONY: crawl-setup
crawl-setup: ## Install the Playwright browser Crawl4AI needs for URL scraping
	uv run crawl4ai-setup

.PHONY: setup
setup: env install db-create migrate crawl-setup ## One-shot: .env + deps + database + migrations + crawler

.PHONY: env
env: ## Create .env from .env.example with a generated JWT_SECRET (if missing)
	@if [ -f .env ]; then \
		echo ".env already exists — leaving it untouched"; \
	else \
		cp .env.example .env; \
		secret=$$(openssl rand -hex 32); \
		sed -i '' "s|^JWT_SECRET=.*|JWT_SECRET=$$secret|" .env; \
		echo "created .env with a generated JWT_SECRET — review DB creds before continuing"; \
	fi

.PHONY: secret
secret: ## Print a strong random value suitable for JWT_SECRET
	@openssl rand -hex 32

# --- postgres service (Homebrew) -------------------------------------------

.PHONY: pg-start
pg-start: ## Start local Postgres (brew services)
	brew services start $(PG_SERVICE)

.PHONY: pg-stop
pg-stop: ## Stop local Postgres (brew services)
	brew services stop $(PG_SERVICE)

# --- database ---------------------------------------------------------------

.PHONY: db-create
db-create: ## Create role + database + pgvector extension (idempotent)
	-createuser $(POSTGRES_USER) --createdb 2>/dev/null || true
	-psql -d postgres -c "ALTER USER $(POSTGRES_USER) WITH PASSWORD '$(POSTGRES_PASSWORD)';"
	-createdb $(POSTGRES_DB) -O $(POSTGRES_USER) 2>/dev/null || true
	psql -d $(POSTGRES_DB) -c "CREATE EXTENSION IF NOT EXISTS vector;"

.PHONY: db-drop
db-drop: ## Drop the database (DESTRUCTIVE)
	dropdb --if-exists $(POSTGRES_DB)

.PHONY: db-reset
db-reset: db-drop db-create migrate ## Drop, recreate, and re-run all migrations

.PHONY: db-shell
db-shell: ## Open a psql shell on the database
	psql -d $(POSTGRES_DB)

# --- migrations -------------------------------------------------------------

.PHONY: migrate
migrate: ## Apply all migrations (alembic upgrade head)
	uv run alembic upgrade head

.PHONY: upgrade
upgrade: migrate ## Alias for migrate

.PHONY: downgrade
downgrade: ## Roll back the last migration (override: STEP=-2)
	uv run alembic downgrade $(or $(STEP),-1)

.PHONY: migration
migration: ## Create a migration from model changes (usage: make migration m="add foo")
	@test -n "$(m)" || { echo "Usage: make migration m=\"message\""; exit 1; }
	uv run alembic revision --autogenerate -m "$(m)"

.PHONY: migration-empty
migration-empty: ## Create an empty migration (usage: make migration-empty m="message")
	@test -n "$(m)" || { echo "Usage: make migration-empty m=\"message\""; exit 1; }
	uv run alembic revision -m "$(m)"

.PHONY: history
history: ## Show migration history
	uv run alembic history --indicate-current

.PHONY: current
current: ## Show the currently applied revision
	uv run alembic current

# --- run / test -------------------------------------------------------------

.PHONY: run
run: ## Run the API with reload on :8000
	uv run uvicorn api.main:app --reload --port 8000

TEST_DB ?= sikto_test

.PHONY: test-db
test-db: ## Create + migrate the dedicated test database (safe to re-run)
	$(MAKE) db-create POSTGRES_DB=$(TEST_DB)
	$(MAKE) migrate POSTGRES_DB=$(TEST_DB)

.PHONY: test
test: test-db ## Run the full test suite against the isolated test database
	uv run pytest

.PHONY: lint
lint: ## Lint with ruff
	uv run ruff check src tests
