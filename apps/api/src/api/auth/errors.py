"""Auth domain errors. Each carries its HTTP status + client-safe detail;
`register_auth_error_handler` (handlers.py) turns them into JSON responses."""

from fastapi import status


class AuthError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "authentication error"


class EmailAlreadyExistsError(AuthError):
    status_code = status.HTTP_409_CONFLICT
    detail = "email already registered"


class InvalidCredentialsError(AuthError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "invalid email or password"


class InvalidTokenError(AuthError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "not authenticated"
