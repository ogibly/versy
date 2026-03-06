from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Lifecycle Policy Engine'
    environment_name: str = 'development'
    api_prefix: str = ''
    database_url: str = 'postgresql+asyncpg://postgres:postgres@localhost:5432/lifecycle_policy_engine'
    jwt_secret_key: str = 'change-me'
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60
    auth_users_json: str = '[{"username":"admin","password":"admin123!","role":"admin","full_name":"Platform Admin"},{"username":"viewer","password":"viewer123!","role":"viewer","full_name":"Read Only User"}]'
    cors_origins_raw: str = 'http://localhost:5173,http://127.0.0.1:5173'
    runzero_console_url: str = 'https://console.runzero.com'
    runzero_api_base: str = 'https://console.runzero.com/api/v1.0'
    runzero_export_token: str | None = None
    runzero_mapping_path: str = 'backend/app/config/runzero_field_mapping.yaml'
    runzero_schedule_enabled: bool = False
    runzero_schedule_interval_minutes: int = 60
    runzero_default_search: str | None = None
    runzero_default_fields: str | None = None
    auto_create_schema: bool = False

    @property
    def auth_users(self) -> list[dict[str, Any]]:
        data = json.loads(self.auth_users_json)
        if not isinstance(data, list):
            raise ValueError('AUTH_USERS_JSON must be a JSON array')
        return data

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(',') if item.strip()]

    @property
    def resolved_mapping_path(self) -> Path:
        path = Path(self.runzero_mapping_path)
        if path.is_absolute() or path.exists():
            return path
        return Path('/workspace') / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
