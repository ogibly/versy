from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import Asset, ComponentType, Evaluation
from app.schemas.api import EvaluationRead, UserContext

router = APIRouter(prefix='/evaluations', tags=['evaluations'])


@router.get('', response_model=list[EvaluationRead])
async def list_evaluations(
    tier: str | None = None,
    component_type: str | None = None,
    asset_type: str | None = None,
    environment: str | None = None,
    skip: int = 0,
    limit: int = 100,
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EvaluationRead]:
    stmt = (
        select(Evaluation, Asset, ComponentType.key)
        .join(Asset, Evaluation.asset_id == Asset.id)
        .join(ComponentType, Evaluation.component_type_id == ComponentType.id)
        .order_by(Evaluation.evaluated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if tier:
        stmt = stmt.where(Evaluation.lifecycle_tier == tier)
    if component_type:
        stmt = stmt.where(ComponentType.key == component_type)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if environment:
        stmt = stmt.where(Asset.environment == environment)

    rows = (await session.execute(stmt)).all()
    return [
        EvaluationRead(
            id=evaluation.id,
            asset_id=evaluation.asset_id,
            component_type_id=evaluation.component_type_id,
            component_type_key=component_key,
            observed_version=evaluation.observed_version,
            lifecycle_tier=evaluation.lifecycle_tier,
            matched_policy_id=evaluation.matched_policy_id,
            evaluated_at=evaluation.evaluated_at,
            rationale=evaluation.rationale,
            asset_hostname=asset.hostname,
            asset_type=asset.asset_type,
            environment=asset.environment,
        )
        for evaluation, asset, component_key in rows
    ]
