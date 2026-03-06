from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Asset(Base):
    __tablename__ = 'assets'

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False, default='other')
    vendor: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(Text)
    hostname: Mapped[str | None] = mapped_column(Text)
    identifiers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    observations: Mapped[list['Observation']] = relationship(back_populates='asset', cascade='all, delete-orphan')
    evaluations: Mapped[list['Evaluation']] = relationship(back_populates='asset', cascade='all, delete-orphan')


class ComponentType(Base):
    __tablename__ = 'component_types'

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    observations: Mapped[list['Observation']] = relationship(back_populates='component_type')
    policies: Mapped[list['Policy']] = relationship(back_populates='component_type')
    evaluations: Mapped[list['Evaluation']] = relationship(back_populates='component_type')


class Observation(Base):
    __tablename__ = 'observations'
    __table_args__ = (
        UniqueConstraint('asset_id', 'component_type_id', 'observed_at', 'version', name='uq_observations_asset_component_seen_version'),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    component_type_id: Mapped[str] = mapped_column(ForeignKey('component_types.id', ondelete='RESTRICT'), nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default='runzero')
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    asset: Mapped[Asset] = relationship(back_populates='observations')
    component_type: Mapped[ComponentType] = relationship(back_populates='observations')


class Policy(Base):
    __tablename__ = 'policies'

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    component_type_id: Mapped[str] = mapped_column(ForeignKey('component_types.id', ondelete='RESTRICT'), nullable=False)
    asset_type: Mapped[str | None] = mapped_column(Text)
    vendor: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    match_mode: Mapped[str] = mapped_column(Text, nullable=False, default='exact')
    lifecycle_tier: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    created_by: Mapped[str | None] = mapped_column(Text)

    component_type: Mapped[ComponentType] = relationship(back_populates='policies')
    audit_logs: Mapped[list['PolicyAuditLog']] = relationship(back_populates='policy', cascade='all, delete-orphan')


class Evaluation(Base):
    __tablename__ = 'evaluations'

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    component_type_id: Mapped[str] = mapped_column(ForeignKey('component_types.id', ondelete='RESTRICT'), nullable=False)
    observed_version: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_tier: Mapped[str] = mapped_column(Text, nullable=False)
    matched_policy_id: Mapped[str | None] = mapped_column(ForeignKey('policies.id', ondelete='SET NULL'))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    rationale: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    asset: Mapped[Asset] = relationship(back_populates='evaluations')
    component_type: Mapped[ComponentType] = relationship(back_populates='evaluations')
    matched_policy: Mapped[Policy | None] = relationship()


class IngestionRun(Base):
    __tablename__ = 'ingestion_runs'

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    stats: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class PolicyAuditLog(Base):
    __tablename__ = 'policy_audit_log'

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    policy_id: Mapped[str] = mapped_column(ForeignKey('policies.id', ondelete='CASCADE'), nullable=False)
    actor: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    diff: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    policy: Mapped[Policy] = relationship(back_populates='audit_logs')
