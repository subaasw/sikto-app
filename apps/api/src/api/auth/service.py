"""Auth orchestration over repository + AuthManager; raises domain errors."""

from sqlalchemy.ext.asyncio import AsyncSession

from api.models import User

from . import repository
from .errors import EmailAlreadyExistsError, InvalidCredentialsError
from .manager import AuthManager


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def register_user(
    session: AsyncSession,
    manager: AuthManager,
    *,
    name: str,
    email: str,
    password: str,
) -> User:
    email = _normalize_email(email)
    if await repository.get_user_by_email(session, email) is not None:
        raise EmailAlreadyExistsError(email)
    password_hash = manager.hash_password(password)
    return await repository.create_user(
        session, name=name.strip(), email=email, password_hash=password_hash
    )


async def authenticate_user(
    session: AsyncSession,
    manager: AuthManager,
    *,
    email: str,
    password: str,
) -> User:
    email = _normalize_email(email)
    user = await repository.get_user_by_email(session, email)
    if user is None or not manager.verify_password(password, user.password_hash):
        raise InvalidCredentialsError(email)
    return user
