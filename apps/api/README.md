# Sikto API

FastAPI backend for Sikto. Async SQLAlchemy + Postgres (pgvector), Alembic
migrations, email/password auth.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- A local Postgres 14+ with the `pgvector` extension available

## Configuration

All settings live in `src/api/config.py` (`Settings`) and are read from
environment variables or a local `.env` file (gitignored). Copy the template
and fill in real values:

```bash
cp .env.example .env        # or: make env  (also generates a JWT_SECRET)
make secret                 # print a strong value for JWT_SECRET
```

The database URL is composed from the `POSTGRES_*` parts (also used by the
Makefile), or set `DATABASE_URL` to point at a managed/remote database. Never
commit `.env`; commit changes to `.env.example` instead.

## Setup

Shortcut: `make setup` runs everything below (`.env` + deps + database +
migrations). Run `make help` to see every target. The manual steps:

```bash
# 1. Install dependencies into a local virtualenv (.venv)
uv sync

# 2. Make sure Postgres is running locally, then create the role + database.
#    Substitute the POSTGRES_* values from your .env for the placeholders.
createuser <db-user> --createdb 2>/dev/null || true
psql -c "ALTER USER <db-user> WITH PASSWORD '<db-password>';"
createdb <db-name> -O <db-user> 2>/dev/null || true
psql -d <db-name> -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Apply migrations
uv run alembic upgrade head
```

## Run

```bash
uv run uvicorn api.main:app --reload --port 8000
```

## Auth

Email/password with a single JWT access token delivered as an httpOnly cookie.

| Method | Path           | Purpose                         |
| ------ | -------------- | ------------------------------- |
| POST   | `/auth/signup` | Create account, set session     |
| POST   | `/auth/login`  | Authenticate, set session       |
| POST   | `/auth/logout` | Clear session cookie            |
| GET    | `/auth/me`     | Current user (requires session) |

For production set a strong `JWT_SECRET` and `COOKIE_SECURE=true` (and
`COOKIE_DOMAIN` if the web app and API live on different subdomains).

## Tests

```bash
uv run pytest                              # full suite (needs the database)
uv run pytest tests/test_auth_manager.py   # auth unit tests, no database
```
