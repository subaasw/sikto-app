"""End-to-end auth router tests. Requires a running, migrated database."""

import uuid

import httpx
from httpx import ASGITransport

from api.main import app


def _client() -> httpx.AsyncClient:
    # A cookie jar per client mimics one browser session.
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


async def test_signup_sets_session_and_me_returns_user():
    email = _email()
    async with _client() as client:
        resp = await client.post(
            "/auth/signup", json={"name": "Ada", "email": email, "password": "supersecret"}
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == email
        assert "access_token" in resp.cookies

        me = await client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert me.json()["name"] == "Ada"


async def test_duplicate_email_returns_conflict():
    email = _email()
    async with _client() as client:
        first = await client.post(
            "/auth/signup", json={"name": "A", "email": email, "password": "supersecret"}
        )
        assert first.status_code == 201
    async with _client() as client:
        dup = await client.post(
            "/auth/signup", json={"name": "B", "email": email, "password": "supersecret"}
        )
        assert dup.status_code == 409


async def test_login_with_wrong_password_is_unauthorized():
    email = _email()
    async with _client() as client:
        await client.post(
            "/auth/signup", json={"name": "A", "email": email, "password": "supersecret"}
        )
    async with _client() as client:
        resp = await client.post("/auth/login", json={"email": email, "password": "wrongpass"})
        assert resp.status_code == 401


async def test_login_succeeds_with_correct_password():
    email = _email()
    async with _client() as client:
        await client.post(
            "/auth/signup", json={"name": "A", "email": email, "password": "supersecret"}
        )
    async with _client() as client:
        resp = await client.post("/auth/login", json={"email": email, "password": "supersecret"})
        assert resp.status_code == 200
        assert "access_token" in resp.cookies


async def test_me_without_session_is_unauthorized():
    async with _client() as client:
        resp = await client.get("/auth/me")
        assert resp.status_code == 401


async def test_logout_clears_session():
    email = _email()
    async with _client() as client:
        await client.post(
            "/auth/signup", json={"name": "A", "email": email, "password": "supersecret"}
        )
        assert (await client.get("/auth/me")).status_code == 200
        logout = await client.post("/auth/logout")
        assert logout.status_code == 204
        assert (await client.get("/auth/me")).status_code == 401
