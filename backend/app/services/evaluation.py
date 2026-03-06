from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, ComponentType, Evaluation, Observation, Policy
from app.services.policies import ensure_component_types

OS_COMPONENT_KEYS = {'OS', 'NetworkOS', 'HypervisorOS', 'StorageOS'}
FIRMWARE_COMPONENT_KEYS = {'Firmware', 'BIOS', 'ApplianceFW'}


@dataclass(slots=True)
class CandidatePolicy:
    policy: Policy
    component_type_key: str


def _version_matches(policy: Policy, observed_version: str) -> bool:
    if policy.match_mode == 'exact':
        return observed_version == policy.version
    prefix = policy.version.rstrip('xX*')
    return observed_version.startswith(prefix)


def _scope_matches(policy: Policy, asset: Asset) -> bool:
    checks = {
        'asset_type': policy.asset_type,
        'vendor': policy.vendor,
        'model': policy.model,
        'environment': policy.environment,
    }
    for field_name, expected in checks.items():
        if expected is None:
            continue
        if getattr(asset, field_name) != expected:
            return False
    return True


def precedence_rank(policy: Policy) -> int:
    if policy.vendor and policy.model and policy.environment:
        return 1
    if policy.vendor and policy.model:
        return 2
    if policy.asset_type and policy.environment:
        return 3
    if policy.asset_type:
        return 4
    if policy.environment:
        return 5
    return 6


async def recompute_evaluations(session: AsyncSession) -> tuple[int, datetime]:
    now = datetime.now(UTC)
    await ensure_component_types(session)

    observation_rows = await session.execute(
        select(Observation, Asset, ComponentType)
        .join(Asset, Observation.asset_id == Asset.id)
        .join(ComponentType, Observation.component_type_id == ComponentType.id)
        .order_by(Observation.asset_id, Observation.component_type_id, Observation.observed_at.desc(), Observation.id.desc())
    )
    latest_observations: dict[tuple[str, str], tuple[Observation, Asset, ComponentType]] = {}
    for observation, asset, component_type in observation_rows.all():
        key = (observation.asset_id, observation.component_type_id)
        latest_observations.setdefault(key, (observation, asset, component_type))

    policy_rows = await session.execute(
        select(Policy, ComponentType)
        .join(ComponentType, Policy.component_type_id == ComponentType.id)
        .where(Policy.active.is_(True))
        .where(Policy.effective_from <= now)
        .where((Policy.effective_to.is_(None)) | (Policy.effective_to >= now))
        .order_by(Policy.effective_from.desc(), Policy.id.asc())
    )
    policies_by_component: dict[str, list[CandidatePolicy]] = {}
    for policy, component in policy_rows.all():
        policies_by_component.setdefault(policy.component_type_id, []).append(CandidatePolicy(policy=policy, component_type_key=component.key))

    await session.execute(delete(Evaluation))
    created = 0
    for observation, asset, component in latest_observations.values():
        matching = []
        for candidate in policies_by_component.get(component.id, []):
            if not _scope_matches(candidate.policy, asset):
                continue
            if not _version_matches(candidate.policy, observation.version):
                continue
            matching.append(candidate)

        matching.sort(key=lambda item: (precedence_rank(item.policy), -item.policy.effective_from.timestamp(), item.policy.id))
        selected = matching[0] if matching else None
        if selected:
            matched_fields = {
                key: value
                for key, value in {
                    'asset_type': selected.policy.asset_type,
                    'vendor': selected.policy.vendor,
                    'model': selected.policy.model,
                    'environment': selected.policy.environment,
                }.items()
                if value is not None
            }
            rationale: dict[str, Any] = {
                'matched': True,
                'component_type_key': component.key,
                'precedence_rank': precedence_rank(selected.policy),
                'matched_constraints': matched_fields,
                'policy_version': selected.policy.version,
                'policy_match_mode': selected.policy.match_mode,
                'reason': 'Most specific active policy matched observed version.',
            }
            tier = selected.policy.lifecycle_tier
            matched_policy_id = selected.policy.id
        else:
            rationale = {
                'matched': False,
                'component_type_key': component.key,
                'reason': 'No active policy matched the observed version; defaulted to Unsupported.',
            }
            tier = 'Unsupported'
            matched_policy_id = None

        session.add(
            Evaluation(
                asset_id=asset.id,
                component_type_id=component.id,
                observed_version=observation.version,
                lifecycle_tier=tier,
                matched_policy_id=matched_policy_id,
                evaluated_at=now,
                rationale=rationale,
            )
        )
        created += 1

    await session.flush()
    return created, now


async def dashboard_summary(session: AsyncSession) -> dict[str, Any]:
    evaluation_rows = await session.execute(
        select(Evaluation, Asset, ComponentType)
        .join(Asset, Evaluation.asset_id == Asset.id)
        .join(ComponentType, Evaluation.component_type_id == ComponentType.id)
    )
    counts = Counter()
    hotspots = Counter()
    for evaluation, asset, component_type in evaluation_rows.all():
        group = 'OS' if component_type.key in OS_COMPONENT_KEYS else 'Firmware'
        counts[(group, evaluation.lifecycle_tier)] += 1
        hotspots[('asset_type', asset.asset_type or 'other')] += 1
        hotspots[('environment', asset.environment or 'other')] += 1

    return {
        'counts': [
            {'component_group': component_group, 'lifecycle_tier': tier, 'count': count}
            for (component_group, tier), count in sorted(counts.items())
        ],
        'hotspots': [
            {'dimension': dimension, 'value': value, 'count': count}
            for (dimension, value), count in hotspots.most_common(10)
        ],
    }
