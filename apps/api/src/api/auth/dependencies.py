"""FastAPI dependencies that expose the AuthManager and the current user."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings, get_settings
from api.db import get_session
from api.models import User

from . import repository
from .errors import InvalidTokenError
from .manager import AuthManager

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_auth_manager(settings: Annotated[Settings, Depends(get_settings)]) -> AuthManager:
    return AuthManager(settings)


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    manager: Annotated[AuthManager, Depends(get_auth_manager)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise _UNAUTHENTICATED
    try:
        user_id = manager.verify_access_token(token)
    except InvalidTokenError as exc:
        raise _UNAUTHENTICATED from exc
    user = await repository.get_user_by_id(session, user_id)
    if user is None:
        raise _UNAUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
