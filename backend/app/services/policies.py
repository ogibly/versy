from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ComponentType, Policy, PolicyAuditLog
from app.schemas.api import PolicyCreate

COMPONENT_TYPE_SEEDS = {
    'OS': 'Operating system version',
    'BIOS': 'System BIOS version',
    'Firmware': 'General firmware version',
    'NetworkOS': 'Network operating system version',
    'HypervisorOS': 'Hypervisor operating system version',
    'StorageOS': 'Storage operating system version',
    'ApplianceFW': 'Appliance firmware version',
}


async def ensure_component_types(session: AsyncSession) -> dict[str, ComponentType]:
    result = await session.execute(select(ComponentType))
    existing = {component.key: component for component in result.scalars().all()}
    created = False
    for key, description in COMPONENT_TYPE_SEEDS.items():
        if key not in existing:
            component = ComponentType(key=key, description=description)
            session.add(component)
            existing[key] = component
            created = True
    if created:
        await session.flush()
    return existing


async def get_component_type_by_key(session: AsyncSession, key: str) -> ComponentType:
    components = await ensure_component_types(session)
    if key not in components:
        raise ValueError(f'Unknown component type: {key}')
    return components[key]


def normalize_policy_scope(policy: Policy) -> tuple[str | None, str | None, str | None, str | None]:
    return (policy.asset_type, policy.vendor, policy.model, policy.environment)


def date_ranges_overlap(start_a: datetime, end_a: datetime | None, start_b: datetime, end_b: datetime | None) -> bool:
    sentinel = datetime.max.replace(tzinfo=UTC)
    return start_a <= (end_b or sentinel) and start_b <= (end_a or sentinel)


async def build_policy_conflicts(session: AsyncSession, policies: list[Policy]) -> dict[str, list[dict[str, Any]]]:
    conflicts: dict[str, list[dict[str, Any]]] = {policy.id: [] for policy in policies}
    components = await ensure_component_types(session)
    component_names = {component.id: component.key for component in components.values()}

    for index, left in enumerate(policies):
        for right in policies[index + 1 :]:
            same_scope = normalize_policy_scope(left) == normalize_policy_scope(right)
            same_component = left.component_type_id == right.component_type_id
            same_match = left.version == right.version and left.match_mode == right.match_mode
            if same_scope and same_component and same_match and date_ranges_overlap(left.effective_from, left.effective_to, right.effective_from, right.effective_to):
                conflicts[left.id].append(
                    {
                        'other_policy_id': right.id,
                        'component_type_key': component_names.get(right.component_type_id, 'unknown'),
                        'reason': 'Overlapping effective dates for identical scope and version.',
                        'other_lifecycle_tier': right.lifecycle_tier,
                    }
                )
                conflicts[right.id].append(
                    {
                        'other_policy_id': left.id,
                        'component_type_key': component_names.get(left.component_type_id, 'unknown'),
                        'reason': 'Overlapping effective dates for identical scope and version.',
                        'other_lifecycle_tier': left.lifecycle_tier,
                    }
                )
    return conflicts


async def record_policy_audit(
    session: AsyncSession,
    *,
    policy_id: str,
    actor: str | None,
    action: str,
    diff: dict[str, Any],
) -> None:
    session.add(PolicyAuditLog(policy_id=policy_id, actor=actor, action=action, diff=diff))
    await session.flush()


async def import_policies_from_csv(session: AsyncSession, csv_bytes: bytes, actor: str) -> tuple[list[Policy], dict[str, list[dict[str, Any]]]]:
    reader = csv.DictReader(io.StringIO(csv_bytes.decode('utf-8')))
    created: list[Policy] = []
    for row in reader:
        payload = PolicyCreate(
            component_type_key=row['component_type_key'],
            asset_type=row.get('asset_type') or None,
            vendor=row.get('vendor') or None,
            model=row.get('model') or None,
            environment=row.get('environment') or None,
            version=row['version'],
            match_mode=(row.get('match_mode') or 'exact'),
            lifecycle_tier=row['lifecycle_tier'],
            effective_from=datetime.fromisoformat(row['effective_from']),
            effective_to=datetime.fromisoformat(row['effective_to']) if row.get('effective_to') else None,
            active=(row.get('active', 'true').strip().lower() != 'false'),
            notes=row.get('notes') or None,
            created_by=row.get('created_by') or actor,
        )
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
            created_by=payload.created_by or actor,
        )
        session.add(policy)
        await session.flush()
        await record_policy_audit(session, policy_id=policy.id, actor=actor, action='create', diff={'new': policy_to_dict(policy, component.key)})
        created.append(policy)
    conflicts = await build_policy_conflicts(session, created)
    return created, conflicts


def policy_to_dict(policy: Policy, component_type_key: str) -> dict[str, Any]:
    return {
        'id': policy.id,
        'component_type_id': policy.component_type_id,
        'component_type_key': component_type_key,
        'asset_type': policy.asset_type,
        'vendor': policy.vendor,
        'model': policy.model,
        'environment': policy.environment,
        'version': policy.version,
        'match_mode': policy.match_mode,
        'lifecycle_tier': policy.lifecycle_tier,
        'effective_from': policy.effective_from.isoformat(),
        'effective_to': policy.effective_to.isoformat() if policy.effective_to else None,
        'active': policy.active,
        'notes': policy.notes,
        'created_at': policy.created_at.isoformat(),
        'created_by': policy.created_by,
    }
