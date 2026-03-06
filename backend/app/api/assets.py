from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import Asset, ComponentType, Evaluation, Observation
from app.schemas.api import AssetDetail, AssetRead, EvaluationRead, ObservationRead, UserContext
from app.services.evaluation import FIRMWARE_COMPONENT_KEYS, OS_COMPONENT_KEYS

router = APIRouter(prefix='/assets', tags=['assets'])


def _tier_map(evaluations: list[tuple[Evaluation, str]]) -> tuple[str | None, str | None]:
    os_tier = None
    fw_tier = None
    for evaluation, component_key in evaluations:
        if component_key in OS_COMPONENT_KEYS and os_tier is None:
            os_tier = evaluation.lifecycle_tier
        if component_key in FIRMWARE_COMPONENT_KEYS and fw_tier is None:
            fw_tier = evaluation.lifecycle_tier
    return os_tier, fw_tier


@router.get('', response_model=list[AssetRead])
async def list_assets(
    asset_type: str | None = None,
    environment: str | None = None,
    vendor: str | None = None,
    model: str | None = None,
    q: str | None = Query(default=None, description='Search hostname, vendor, or model'),
    skip: int = 0,
    limit: int = 100,
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AssetRead]:
    stmt = select(Asset).order_by(Asset.last_seen_at.desc()).offset(skip).limit(limit)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if environment:
        stmt = stmt.where(Asset.environment == environment)
    if vendor:
        stmt = stmt.where(Asset.vendor == vendor)
    if model:
        stmt = stmt.where(Asset.model == model)
    if q:
        like = f'%{q}%'
        stmt = stmt.where(or_(Asset.hostname.ilike(like), Asset.vendor.ilike(like), Asset.model.ilike(like)))
    assets = (await session.execute(stmt)).scalars().all()
    asset_ids = [asset.id for asset in assets]
    evaluations_by_asset: dict[str, list[tuple[Evaluation, str]]] = defaultdict(list)
    if asset_ids:
        evaluation_rows = await session.execute(
            select(Evaluation, ComponentType.key)
            .join(ComponentType, Evaluation.component_type_id == ComponentType.id)
            .where(Evaluation.asset_id.in_(asset_ids))
            .order_by(Evaluation.evaluated_at.desc())
        )
        for evaluation, component_key in evaluation_rows.all():
            evaluations_by_asset[evaluation.asset_id].append((evaluation, component_key))

    results = []
    for asset in assets:
        os_tier, fw_tier = _tier_map(evaluations_by_asset.get(asset.id, []))
        results.append(
            AssetRead(
                id=asset.id,
                asset_type=asset.asset_type,
                vendor=asset.vendor,
                model=asset.model,
                environment=asset.environment,
                hostname=asset.hostname,
                identifiers=asset.identifiers,
                first_seen_at=asset.first_seen_at,
                last_seen_at=asset.last_seen_at,
                os_tier=os_tier,
                firmware_tier=fw_tier,
            )
        )
    return results


@router.get('/{asset_id}', response_model=AssetDetail)
async def get_asset(
    asset_id: str,
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AssetDetail:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail='Asset not found')

    observation_rows = await session.execute(
        select(Observation, ComponentType.key)
        .join(ComponentType, Observation.component_type_id == ComponentType.id)
        .where(Observation.asset_id == asset.id)
        .order_by(Observation.observed_at.desc())
    )
    observations = [
        ObservationRead(
            id=observation.id,
            component_type_id=observation.component_type_id,
            component_type_key=component_key,
            version=observation.version,
            observed_at=observation.observed_at,
            source=observation.source,
            raw=observation.raw,
        )
        for observation, component_key in observation_rows.all()
    ]

    evaluation_rows = await session.execute(
        select(Evaluation, ComponentType.key)
        .join(ComponentType, Evaluation.component_type_id == ComponentType.id)
        .where(Evaluation.asset_id == asset.id)
        .order_by(Evaluation.evaluated_at.desc())
    )
    eval_pairs: list[tuple[Evaluation, str]] = []
    evaluations = []
    for evaluation, component_key in evaluation_rows.all():
        eval_pairs.append((evaluation, component_key))
        evaluations.append(
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
        )

    os_tier, fw_tier = _tier_map(eval_pairs)
    return AssetDetail(
        id=asset.id,
        asset_type=asset.asset_type,
        vendor=asset.vendor,
        model=asset.model,
        environment=asset.environment,
        hostname=asset.hostname,
        identifiers=asset.identifiers,
        first_seen_at=asset.first_seen_at,
        last_seen_at=asset.last_seen_at,
        os_tier=os_tier,
        firmware_tier=fw_tier,
        observations=observations,
        evaluations=evaluations,
    )
