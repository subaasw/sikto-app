"""Unit tests for AuthManager — pure logic, no database required."""

import uuid

import pytest

from api.auth.errors import InvalidTokenError
from api.auth.manager import AuthManager
from api.config import Settings


def _manager(*, ttl_minutes: int = 60) -> AuthManager:
    settings = Settings(jwt_secret="test-secret-key-at-least-32-bytes-long", access_token_ttl_minutes=ttl_minutes)
    return AuthManager(settings)


def test_hash_password_is_verifiable():
    manager = _manager()
    hashed = manager.hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert manager.verify_password("correct horse battery", hashed)
    assert not manager.verify_password("wrong password", hashed)


def test_access_token_round_trips_user_id():
    manager = _manager()
    user_id = uuid.uuid4()
    token = manager.create_access_token(user_id)
    assert manager.verify_access_token(token) == user_id


def test_expired_token_is_rejected():
    manager = _manager(ttl_minutes=-1)  # already expired on creation
    token = manager.create_access_token(uuid.uuid4())
    with pytest.raises(InvalidTokenError):
        manager.verify_access_token(token)


def test_token_signed_with_other_secret_is_rejected():
    issuer = _manager()
    token = issuer.create_access_token(uuid.uuid4())
    other = AuthManager(
        Settings(jwt_secret="another-different-secret-32-bytes-minimum", access_token_ttl_minutes=60)
    )
    with pytest.raises(InvalidTokenError):
        other.verify_access_token(token)


def test_garbage_token_is_rejected():
    manager = _manager()
    with pytest.raises(InvalidTokenError):
        manager.verify_access_token("not-a-jwt")


def test_overlong_password_is_rejected():
    manager = _manager()
    with pytest.raises(ValueError):
        manager.hash_password("x" * 100)
