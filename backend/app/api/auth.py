from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_settings
from app.core.config import Settings
from app.core.security import AuthenticationError, authenticate_user, create_access_token
from app.schemas.api import TokenResponse

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/token', response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    try:
        user = authenticate_user(settings, form_data.username, form_data.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token = create_access_token(settings, subject=user['username'], role=user['role'])
    return TokenResponse(access_token=token, role=user['role'], username=user['username'])
