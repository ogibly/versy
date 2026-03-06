from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import Asset, Evaluation, Observation, Policy
from app.services.evaluation import recompute_evaluations
from app.services.policies import ensure_component_types


@pytest.mark.asyncio
async def test_policy_matching_precedence_all_layers(app_instance) -> None:
    now = datetime.now(UTC)
    async with app_instance.state.db.session_factory() as session:
        components = await ensure_component_types(session)
        asset = Asset(
            asset_type='switch',
            vendor='ExampleVendor',
            model='ExampleSwitch-1000',
            environment='prod',
            hostname='DUMMY-CORE-SW1',
            identifiers={'ips': ['192.0.2.10'], 'macs': ['00:11:22:33:44:55'], 'serials': ['EXAMPLE123456'], 'stable_keys': ['dummy-key']},
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(asset)
        await session.flush()
        session.add(
            Observation(
                asset_id=asset.id,
                component_type_id=components['OS'].id,
                version='1.0',
                observed_at=now,
                source='runzero',
                raw={'fixture': True},
            )
        )
        await session.flush()

        def add_policy(**overrides) -> Policy:
            base = {
                'component_type_id': components['OS'].id,
                'version': '1.0',
                'match_mode': 'exact',
                'lifecycle_tier': 'Unsupported',
                'effective_from': now,
                'active': True,
                'created_by': 'test',
            }
            base.update(overrides)
            policy = Policy(**base)
            session.add(policy)
            return policy

        p6 = add_policy(lifecycle_tier='Unsupported')
        await session.flush()
        await recompute_evaluations(session)
        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.matched_policy_id == p6.id

        p5 = add_policy(environment='prod', lifecycle_tier='N-2')
        await session.flush()
        await recompute_evaluations(session)
        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.matched_policy_id == p5.id

        p4 = add_policy(asset_type='switch', lifecycle_tier='N-1')
        await session.flush()
        await recompute_evaluations(session)
        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.matched_policy_id == p4.id

        p3 = add_policy(asset_type='switch', environment='prod', lifecycle_tier='N')
        await session.flush()
        await recompute_evaluations(session)
        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.matched_policy_id == p3.id

        p2 = add_policy(vendor='ExampleVendor', model='ExampleSwitch-1000', lifecycle_tier='N-1')
        await session.flush()
        await recompute_evaluations(session)
        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.matched_policy_id == p2.id

        p1 = add_policy(vendor='ExampleVendor', model='ExampleSwitch-1000', environment='prod', lifecycle_tier='N')
        await session.flush()
        await recompute_evaluations(session)
        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.matched_policy_id == p1.id
