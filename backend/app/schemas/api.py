from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LifecycleTier = Literal['N', 'N-1', 'N-2', 'Unsupported']
MatchMode = Literal['exact', 'prefix']
Role = Literal['admin', 'viewer']


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    role: Role
    username: str


class UserContext(BaseModel):
    username: str
    role: Role
    full_name: str | None = None


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    component_type_id: str
    component_type_key: str
    version: str
    observed_at: datetime
    source: str
    raw: dict[str, Any]


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    component_type_id: str
    component_type_key: str
    observed_version: str
    lifecycle_tier: LifecycleTier
    matched_policy_id: str | None = None
    evaluated_at: datetime
    rationale: dict[str, Any]
    asset_hostname: str | None = None
    asset_type: str | None = None
    environment: str | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_type: str
    vendor: str | None = None
    model: str | None = None
    environment: str | None = None
    hostname: str | None = None
    identifiers: dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime
    os_tier: LifecycleTier | None = None
    firmware_tier: LifecycleTier | None = None


class AssetDetail(AssetRead):
    observations: list[ObservationRead]
    evaluations: list[EvaluationRead]


class PolicyScopeMixin(BaseModel):
    asset_type: str | None = None
    vendor: str | None = None
    model: str | None = None
    environment: str | None = None

    @model_validator(mode='after')
    def validate_scope(self) -> 'PolicyScopeMixin':
        flags = (bool(self.vendor), bool(self.model), bool(self.asset_type), bool(self.environment))
        allowed = {
            (False, False, False, False),
            (False, False, False, True),
            (False, False, True, False),
            (False, False, True, True),
            (True, True, False, False),
            (True, True, False, True),
        }
        if flags not in allowed:
            raise ValueError(
                'Policies must use one of: component only, component+environment, component+asset_type, '
                'component+asset_type+environment, component+vendor+model, component+vendor+model+environment.'
            )
        return self


class PolicyBase(PolicyScopeMixin):
    component_type_key: str
    version: str = Field(min_length=1)
    match_mode: MatchMode = 'exact'
    lifecycle_tier: LifecycleTier
    effective_from: datetime
    effective_to: datetime | None = None
    active: bool = True
    notes: str | None = None


class PolicyCreate(PolicyBase):
    created_by: str | None = None


class PolicyUpdate(PolicyScopeMixin):
    component_type_key: str | None = None
    version: str | None = None
    match_mode: MatchMode | None = None
    lifecycle_tier: LifecycleTier | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    active: bool | None = None
    notes: str | None = None


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    component_type_id: str
    component_type_key: str
    asset_type: str | None = None
    vendor: str | None = None
    model: str | None = None
    environment: str | None = None
    version: str
    match_mode: MatchMode
    lifecycle_tier: LifecycleTier
    effective_from: datetime
    effective_to: datetime | None = None
    active: bool
    notes: str | None = None
    created_at: datetime
    created_by: str | None = None
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class PolicyImportResult(BaseModel):
    created: int
    conflicts_detected: int
    policy_ids: list[str]


class IngestRunRequest(BaseModel):
    search: str | None = None
    fields: str | None = None


class IngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    source: str
    stats: dict[str, Any]
    error: str | None = None


class EvaluateResponse(BaseModel):
    evaluated_records: int
    evaluated_at: datetime


class TierCount(BaseModel):
    component_group: str
    lifecycle_tier: LifecycleTier
    count: int


class Hotspot(BaseModel):
    dimension: str
    value: str
    count: int


class DashboardSummary(BaseModel):
    counts: list[TierCount]
    hotspots: list[Hotspot]
