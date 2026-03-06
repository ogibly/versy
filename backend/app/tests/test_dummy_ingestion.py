from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Asset, Evaluation, Observation, Policy
from app.services.evaluation import recompute_evaluations
from app.services.ingestion.service import ingest_file_bytes
from app.services.policies import ensure_component_types


@pytest.mark.asyncio
async def test_dummy_ingestion_and_re_evaluation(app_instance) -> None:
    fixture_path = Path(__file__).parent / 'fixtures' / 'dummy_service_export.json'
    async with app_instance.state.db.session_factory() as session:
        run = await ingest_file_bytes(session, app_instance.state.settings, data=fixture_path.read_bytes())
        await session.commit()
        assert run.status == 'success'

        assets = (await session.execute(select(Asset))).scalars().all()
        observations = (await session.execute(select(Observation))).scalars().all()
        assert len(assets) == 1
        assert len(observations) == 1
        assert observations[0].version == '1.0'

        components = await ensure_component_types(session)
        policy = Policy(
            component_type_id=components['OS'].id,
            version='1.0',
            match_mode='exact',
            lifecycle_tier='N-1',
            effective_from=datetime.now(UTC),
            active=True,
            created_by='test',
        )
        session.add(policy)
        await session.flush()
        await recompute_evaluations(session)
        await session.commit()

        evaluation = (await session.execute(select(Evaluation))).scalars().one()
        assert evaluation.lifecycle_tier == 'N-1'

        policy.lifecycle_tier = 'N'
        await session.flush()
        await recompute_evaluations(session)
        await session.commit()

        updated = (await session.execute(select(Evaluation))).scalars().one()
        assert updated.lifecycle_tier == 'N'
