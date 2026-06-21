import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    AuthManager,
    CurrentUser,
    LoginRequest,
    SignupRequest,
    UserResponse,
    authenticate_user,
    clear_access_cookie,
    get_auth_manager,
    register_user,
    set_access_cookie,
)
from api.config import Settings, get_settings
from api.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ManagerDep = Annotated[AuthManager, Depends(get_auth_manager)]


def _issue_session(
    response: Response, manager: AuthManager, settings: Settings, user_id: uuid.UUID
) -> None:
    token = manager.create_access_token(user_id)
    set_access_cookie(response, token, settings)


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def signup(
    body: SignupRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    manager: ManagerDep,
) -> UserResponse:
    user = await register_user(
        session, manager, name=body.name, email=body.email, password=body.password
    )
    _issue_session(response, manager, settings, user.id)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    manager: ManagerDep,
) -> UserResponse:
    user = await authenticate_user(
        session, manager, email=body.email, password=body.password
    )
    _issue_session(response, manager, settings, user.id)
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: SettingsDep) -> None:
    clear_access_cookie(response, settings)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
