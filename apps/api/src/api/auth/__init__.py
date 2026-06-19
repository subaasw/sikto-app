"""Email/password auth: hashing, JWT access tokens, and route guards.

Public surface for the rest of the app; import from `api.auth` directly.
"""

from .cookies import clear_access_cookie, set_access_cookie
from .dependencies import CurrentUser, get_auth_manager, get_current_user
from .errors import (
    AuthError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from .handlers import register_auth_error_handler
from .manager import AuthManager
from .schemas import LoginRequest, SignupRequest, UserResponse
from .service import authenticate_user, register_user

__all__ = [
    "AuthError",
    "AuthManager",
    "CurrentUser",
    "EmailAlreadyExistsError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "LoginRequest",
    "SignupRequest",
    "UserResponse",
    "authenticate_user",
    "clear_access_cookie",
    "get_auth_manager",
    "get_current_user",
    "register_auth_error_handler",
    "register_user",
    "set_access_cookie",
]
