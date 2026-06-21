"""Admin CLI for database setup and user management.

Run via the console script (``sikto``) or ``python -m api.cli``. Commands read
the same Settings/.env the app uses, so the database target always matches.
"""

import asyncio
import re
from pathlib import Path

import asyncpg
import typer

from api.config import get_settings

app = typer.Typer(help="Sikto API admin CLI", no_args_is_help=True)
db_app = typer.Typer(help="Database setup and migrations", no_args_is_help=True)
user_app = typer.Typer(help="Application user management", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(user_app, name="user")

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_API_DIR = Path(__file__).resolve().parents[2]  # apps/api


def _ident(value: str, label: str) -> str:
    if not _IDENT.match(value):
        raise typer.BadParameter(f"unsafe {label}: {value!r}")
    return value


# --- db --------------------------------------------------------------------


@db_app.command("check")
def db_check() -> None:
    """Verify the app can connect to its database."""
    from api.db import check_connection, engine

    async def _run() -> None:
        try:
            await check_connection()
        finally:
            await engine.dispose()

    settings = get_settings()
    try:
        asyncio.run(_run())
    except Exception as exc:
        typer.secho(f"✗ cannot connect: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.secho(f"✓ connected to {settings.postgres_db}", fg=typer.colors.GREEN)


@db_app.command("create")
def db_create(
    admin_user: str = typer.Option(None, help="Superuser role for admin connection (default: OS user)"),
    admin_password: str = typer.Option(None, help="Password for the admin role"),
    admin_db: str = typer.Option("postgres", help="Maintenance database to connect to"),
) -> None:
    """Create the role, database, and pgvector extension (idempotent)."""
    settings = get_settings()
    user = _ident(settings.postgres_user, "POSTGRES_USER")
    name = _ident(settings.postgres_db, "POSTGRES_DB")
    password = settings.postgres_password.replace("'", "''")

    async def _run() -> None:
        admin = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=admin_user,
            password=admin_password,
            database=admin_db,
        )
        try:
            if not await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", user):
                await admin.execute(f"CREATE ROLE \"{user}\" LOGIN PASSWORD '{password}'")
                typer.echo(f"created role {user}")
            if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
                await admin.execute(f'CREATE DATABASE "{name}" OWNER "{user}"')
                typer.echo(f"created database {name}")
        finally:
            await admin.close()

        target = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=admin_user,
            password=admin_password,
            database=name,
        )
        try:
            await target.execute("CREATE EXTENSION IF NOT EXISTS vector")
        finally:
            await target.close()

    try:
        asyncio.run(_run())
    except Exception as exc:
        typer.secho(f"✗ db create failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.secho(f"✓ database {name} ready (pgvector enabled)", fg=typer.colors.GREEN)


@db_app.command("migrate")
def db_migrate(revision: str = typer.Argument("head", help="Target revision")) -> None:
    """Apply Alembic migrations up to a revision (default: head)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(_API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_API_DIR / "migrations"))
    command.upgrade(cfg, revision)
    typer.secho(f"✓ migrated to {revision}", fg=typer.colors.GREEN)


@db_app.command("reset")
def db_reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    admin_user: str = typer.Option(None),
    admin_password: str = typer.Option(None),
    admin_db: str = typer.Option("postgres"),
) -> None:
    """Drop and recreate the database, then migrate (DESTRUCTIVE)."""
    settings = get_settings()
    name = _ident(settings.postgres_db, "POSTGRES_DB")
    if not yes:
        typer.confirm(f"Drop and recreate database {name!r}?", abort=True)

    async def _drop() -> None:
        admin = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=admin_user,
            password=admin_password,
            database=admin_db,
        )
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{name}"')
        finally:
            await admin.close()

    asyncio.run(_drop())
    db_create(admin_user=admin_user, admin_password=admin_password, admin_db=admin_db)
    db_migrate()


# --- user ------------------------------------------------------------------


@user_app.command("create")
def user_create(
    name: str = typer.Option(None, help="Full name (prompted if omitted)"),
    email: str = typer.Option(None, help="Email (prompted if omitted)"),
    password: str = typer.Option(None, help="Password (prompted securely if omitted)"),
) -> None:
    """Create an application user (createsuperuser-style)."""
    from api.auth import AuthManager, EmailAlreadyExistsError, register_user
    from api.db import SessionLocal, engine

    name = name or typer.prompt("Full name")
    email = email or typer.prompt("Email")
    password = password or typer.prompt("Password", hide_input=True, confirmation_prompt=True)

    async def _run() -> str:
        try:
            async with SessionLocal() as session:
                user = await register_user(
                    session,
                    AuthManager(get_settings()),
                    name=name,
                    email=email,
                    password=password,
                )
                return user.email
        finally:
            await engine.dispose()

    try:
        created = asyncio.run(_run())
    except EmailAlreadyExistsError as exc:
        typer.secho(f"✗ {email} is already registered", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.secho(f"✗ could not create user: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.secho(f"✓ created user {created}", fg=typer.colors.GREEN)


# --- setup -----------------------------------------------------------------


@app.command("setup")
def setup() -> None:
    """One-shot: create the database and apply migrations."""
    db_create()
    db_migrate()
    typer.secho("✓ setup complete — create a user with: sikto user create", fg=typer.colors.GREEN)


def main() -> None:
    from api.observability import configure_logging

    configure_logging()
    app()


if __name__ == "__main__":
    main()
