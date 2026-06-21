"""Stateless auth primitives: password hashing and JWT access tokens (no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from api.config import Settings

from .errors import InvalidTokenError

_BCRYPT_MAX_BYTES = 72  # bcrypt silently truncates beyond this; we reject instead.


class AuthManager:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)

    # --- passwords -------------------------------------------------------
    def hash_password(self, password: str) -> str:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > _BCRYPT_MAX_BYTES:
            raise ValueError("password must be at most 72 bytes")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > _BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))

    # --- tokens ----------------------------------------------------------
    def create_access_token(self, user_id: uuid.UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_access_token(self, token: str) -> uuid.UUID:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError("could not decode access token") from exc
        if payload.get("type") != "access":
            raise InvalidTokenError("wrong token type")
        sub = payload.get("sub")
        if not sub:
            raise InvalidTokenError("token missing subject")
        try:
            return uuid.UUID(sub)
        except ValueError as exc:
            raise InvalidTokenError("token subject is not a valid id") from exc
