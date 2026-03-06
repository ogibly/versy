from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class AuthenticationError(Exception):
    pass


def verify_password(plain_password: str, configured_password: str) -> bool:
    if configured_password.startswith('$2'):
        return pwd_context.verify(plain_password, configured_password)
    return plain_password == configured_password


def authenticate_user(settings: Settings, username: str, password: str) -> dict[str, Any]:
    for user in settings.auth_users:
        if user.get('username') == username and verify_password(password, str(user.get('password', ''))):
            return user
    raise AuthenticationError('Incorrect username or password')


def create_access_token(settings: Settings, subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {'sub': subject, 'role': role, 'exp': expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthenticationError('Could not validate credentials') from exc
