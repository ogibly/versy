from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import AuthenticationError, decode_access_token
from app.schemas.api import UserContext

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/token')


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.db.session_factory() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme), settings: Settings = Depends(get_settings)) -> UserContext:
    try:
        payload = decode_access_token(settings, token)
        username = str(payload['sub'])
        role = str(payload['role'])
    except (KeyError, AuthenticationError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication credentials') from exc

    for user in settings.auth_users:
        if user.get('username') == username:
            return UserContext(username=username, role=role, full_name=user.get('full_name'))
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication credentials')


def require_role(*roles: str) -> Callable[[UserContext], UserContext]:
    async def dependency(current_user: UserContext = Depends(get_current_user)) -> UserContext:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient privileges')
        return current_user

    return dependency
