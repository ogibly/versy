from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_create_policy_ingest_evaluate_and_query(client, admin_headers) -> None:
    policy_response = await client.post(
        '/policies',
        headers=admin_headers,
        json={
            'component_type_key': 'OS',
            'version': '1.0',
            'match_mode': 'exact',
            'lifecycle_tier': 'N-1',
            'effective_from': datetime.now(UTC).isoformat(),
            'active': True,
            'notes': 'API test policy',
        },
    )
    assert policy_response.status_code == 200, policy_response.text

    fixture_path = Path(__file__).parent / 'fixtures' / 'dummy_service_export.json'
    with fixture_path.open('rb') as handle:
        ingest_response = await client.post('/ingest/file', headers=admin_headers, files={'file': ('dummy.json', handle, 'application/json')})
    assert ingest_response.status_code == 200, ingest_response.text
    assert ingest_response.json()['stats']['normalized_assets'] == 1

    evaluate_response = await client.post('/evaluate', headers=admin_headers)
    assert evaluate_response.status_code == 200, evaluate_response.text
    assert evaluate_response.json()['evaluated_records'] == 1

    evaluations_response = await client.get('/evaluations?component_type=OS', headers=admin_headers)
    assert evaluations_response.status_code == 200, evaluations_response.text
    evaluations = evaluations_response.json()
    assert len(evaluations) == 1
    assert evaluations[0]['lifecycle_tier'] == 'N-1'
    assert evaluations[0]['asset_hostname'] == 'DUMMY-CORE-SW1'

    assets_response = await client.get('/assets', headers=admin_headers)
    assert assets_response.status_code == 200, assets_response.text
    assets = assets_response.json()
    assert len(assets) == 1
    assert assets[0]['os_tier'] == 'N-1'
