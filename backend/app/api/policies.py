from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_role
from app.models import ComponentType, Policy
from app.schemas.api import PolicyCreate, PolicyImportResult, PolicyRead, PolicyUpdate, UserContext
from app.services.policies import build_policy_conflicts, get_component_type_by_key, import_policies_from_csv, policy_to_dict, record_policy_audit

router = APIRouter(prefix='/policies', tags=['policies'])


async def _serialize_policies(session: AsyncSession, policies: list[Policy]) -> list[PolicyRead]:
    component_rows = await session.execute(select(ComponentType))
    components = {component.id: component.key for component in component_rows.scalars().all()}
    all_policies = (await session.execute(select(Policy))).scalars().all()
    conflicts = await build_policy_conflicts(session, all_policies)
    return [
        PolicyRead(
            **policy_to_dict(policy, components[policy.component_type_id]),
            conflicts=conflicts.get(policy.id, []),
        )
        for policy in policies
    ]


@router.get('', response_model=list[PolicyRead])
async def list_policies(
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PolicyRead]:
    policies = (await session.execute(select(Policy).order_by(Policy.created_at.desc()))).scalars().all()
    return await _serialize_policies(session, policies)


@router.post('', response_model=PolicyRead, dependencies=[Depends(require_role('admin'))])
async def create_policy(
    payload: PolicyCreate,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyRead:
    component = await get_component_type_by_key(session, payload.component_type_key)
    policy = Policy(
        component_type_id=component.id,
        asset_type=payload.asset_type,
        vendor=payload.vendor,
        model=payload.model,
        environment=payload.environment,
        version=payload.version,
        match_mode=payload.match_mode,
        lifecycle_tier=payload.lifecycle_tier,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        active=payload.active,
        notes=payload.notes,
        created_by=payload.created_by or current_user.username,
    )
    session.add(policy)
    await session.flush()
    await record_policy_audit(session, policy_id=policy.id, actor=current_user.username, action='create', diff={'new': policy_to_dict(policy, component.key)})
    await session.commit()
    return (await _serialize_policies(session, [policy]))[0]


@router.put('/{policy_id}', response_model=PolicyRead, dependencies=[Depends(require_role('admin'))])
@router.patch('/{policy_id}', response_model=PolicyRead, dependencies=[Depends(require_role('admin'))])
async def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyRead:
    policy = await session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail='Policy not found')

    before_component_key = (await session.get(ComponentType, policy.component_type_id)).key
    before = policy_to_dict(policy, before_component_key)
    updates = payload.model_dump(exclude_unset=True)
    if 'component_type_key' in updates:
        component = await get_component_type_by_key(session, updates.pop('component_type_key'))
        policy.component_type_id = component.id
    for field, value in updates.items():
        setattr(policy, field, value)
    await session.flush()
    after_component_key = (await session.get(ComponentType, policy.component_type_id)).key
    await record_policy_audit(session, policy_id=policy.id, actor=current_user.username, action='update', diff={'before': before, 'after': policy_to_dict(policy, after_component_key)})
    await session.commit()
    return (await _serialize_policies(session, [policy]))[0]


@router.delete('/{policy_id}', dependencies=[Depends(require_role('admin'))])
async def delete_policy(
    policy_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    policy = await session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail='Policy not found')
    component_key = (await session.get(ComponentType, policy.component_type_id)).key
    snapshot = policy_to_dict(policy, component_key)
    await record_policy_audit(session, policy_id=policy.id, actor=current_user.username, action='delete', diff={'before': snapshot})
    await session.delete(policy)
    await session.commit()
    return {'status': 'deleted'}


@router.post('/import', response_model=PolicyImportResult, dependencies=[Depends(require_role('admin'))])
async def import_policy_csv(
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PolicyImportResult:
    created, conflicts = await import_policies_from_csv(session, await file.read(), current_user.username)
    await session.commit()
    return PolicyImportResult(created=len(created), conflicts_detected=sum(len(items) for items in conflicts.values()), policy_ids=[policy.id for policy in created])
