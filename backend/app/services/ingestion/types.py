from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class NormalizedObservation:
    component_type_key: str
    version: str
    observed_at: datetime
    source: str
    raw: dict[str, Any]


@dataclass(slots=True)
class NormalizedAsset:
    asset_type: str
    vendor: str | None
    model: str | None
    environment: str | None
    hostname: str | None
    identifiers: dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime
    observations: list[NormalizedObservation] = field(default_factory=list)
