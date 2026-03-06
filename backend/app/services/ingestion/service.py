from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Asset, IngestionRun, Observation
from app.services.ingestion.mapping import load_field_mapping
from app.services.ingestion.parsers import parse_dummy_service_export, parse_json_bytes, parse_jsonl_bytes, parse_runzero_assets
from app.services.ingestion.types import NormalizedAsset
from app.services.policies import ensure_component_types


async def create_ingestion_run(session: AsyncSession, *, source: str) -> IngestionRun:
    run = IngestionRun(status='running', source=source, started_at=datetime.now(UTC), stats={})
    session.add(run)
    await session.flush()
    return run


def detect_payload_kind(json_payload: Any) -> str:
    if isinstance(json_payload, dict):
        if json_payload and all(isinstance(value, dict) for value in json_payload.values()) and any('/' in key for key in json_payload):
            return 'dummy_service'
        if 'assets' in json_payload and isinstance(json_payload['assets'], list):
            return 'runzero_assets_wrapped'
        return 'runzero_assets_single'
    if isinstance(json_payload, list):
        return 'runzero_assets_list'
    raise ValueError('Unsupported JSON payload format')


def _merge_identifier_values(existing: list[str] | None, incoming: list[str] | None) -> list[str]:
    return sorted(set((existing or []) + (incoming or [])))


async def _load_existing_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(select(Asset))
    return result.scalars().all()


def _asset_matches(existing: Asset, incoming: NormalizedAsset) -> bool:
    existing_identifiers = existing.identifiers or {}
    incoming_identifiers = incoming.identifiers or {}
    for key in ('stable_keys', 'runzero_ids'):
        left = set(existing_identifiers.get(key, []))
        right = set(incoming_identifiers.get(key, []))
        if left and right and left.intersection(right):
            return True
    if existing.hostname and incoming.hostname and existing.hostname == incoming.hostname:
        left_serials = set(existing_identifiers.get('serials', []))
        right_serials = set(incoming_identifiers.get('serials', []))
        left_macs = set(existing_identifiers.get('macs', []))
        right_macs = set(incoming_identifiers.get('macs', []))
        if left_serials.intersection(right_serials) or left_macs.intersection(right_macs):
            return True
    return False


async def upsert_assets_and_observations(session: AsyncSession, normalized_assets: list[NormalizedAsset]) -> dict[str, int]:
    components = await ensure_component_types(session)
    existing_assets = await _load_existing_assets(session)
    stats = {'assets_created': 0, 'assets_updated': 0, 'observations_created': 0}

    for incoming in normalized_assets:
        asset = next((candidate for candidate in existing_assets if _asset_matches(candidate, incoming)), None)
        if asset is None:
            asset = Asset(
                asset_type=incoming.asset_type,
                vendor=incoming.vendor,
                model=incoming.model,
                environment=incoming.environment,
                hostname=incoming.hostname,
                identifiers=incoming.identifiers,
                first_seen_at=incoming.first_seen_at,
                last_seen_at=incoming.last_seen_at,
            )
            session.add(asset)
            await session.flush()
            existing_assets.append(asset)
            stats['assets_created'] += 1
        else:
            asset.asset_type = incoming.asset_type or asset.asset_type
            asset.vendor = incoming.vendor or asset.vendor
            asset.model = incoming.model or asset.model
            asset.environment = incoming.environment or asset.environment
            asset.hostname = incoming.hostname or asset.hostname
            asset.first_seen_at = min(asset.first_seen_at, incoming.first_seen_at)
            asset.last_seen_at = max(asset.last_seen_at, incoming.last_seen_at)
            merged = dict(asset.identifiers or {})
            for field in ('ips', 'macs', 'serials', 'runzero_ids', 'stable_keys'):
                merged[field] = _merge_identifier_values(merged.get(field), incoming.identifiers.get(field))
            asset.identifiers = merged
            stats['assets_updated'] += 1

        existing_observations = {
            (ob.version, ob.observed_at, ob.component_type_id)
            for ob in (await session.execute(select(Observation).where(Observation.asset_id == asset.id))).scalars().all()
        }
        for observation in incoming.observations:
            component = components[observation.component_type_key]
            fingerprint = (observation.version, observation.observed_at, component.id)
            if fingerprint in existing_observations:
                continue
            session.add(
                Observation(
                    asset_id=asset.id,
                    component_type_id=component.id,
                    version=observation.version,
                    observed_at=observation.observed_at,
                    source=observation.source,
                    raw=observation.raw,
                )
            )
            await session.flush()
            existing_observations.add(fingerprint)
            stats['observations_created'] += 1
    return stats


async def ingest_file_bytes(session: AsyncSession, settings: Settings, *, data: bytes, source: str = 'file_upload') -> IngestionRun:
    run = await create_ingestion_run(session, source=source)
    try:
        if data.lstrip().startswith(b'{') or data.lstrip().startswith(b'['):
            json_payload = parse_json_bytes(data)
            payload_kind = detect_payload_kind(json_payload)
            if payload_kind == 'dummy_service':
                normalized = parse_dummy_service_export(json_payload)
            elif payload_kind == 'runzero_assets_wrapped':
                mapping = load_field_mapping(settings.resolved_mapping_path)
                normalized = parse_runzero_assets(json_payload['assets'], mapping)
            elif payload_kind == 'runzero_assets_list':
                mapping = load_field_mapping(settings.resolved_mapping_path)
                normalized = parse_runzero_assets(json_payload, mapping)
            else:
                mapping = load_field_mapping(settings.resolved_mapping_path)
                normalized = parse_runzero_assets([json_payload], mapping)
        else:
            mapping = load_field_mapping(settings.resolved_mapping_path)
            normalized = parse_runzero_assets(parse_jsonl_bytes(data), mapping)

        stats = await upsert_assets_and_observations(session, normalized)
        run.status = 'success'
        run.finished_at = datetime.now(UTC)
        run.stats = {**stats, 'normalized_assets': len(normalized)}
        await session.flush()
        return run
    except Exception as exc:
        run.status = 'failed'
        run.finished_at = datetime.now(UTC)
        run.error = str(exc)
        await session.flush()
        raise


async def ingest_from_runzero_api(session: AsyncSession, settings: Settings, *, search: str | None = None, fields: str | None = None) -> IngestionRun:
    if not settings.runzero_export_token:
        raise ValueError('RUNZERO_EXPORT_TOKEN is not configured')

    params = {}
    if search or settings.runzero_default_search:
        params['search'] = search or settings.runzero_default_search
    if fields or settings.runzero_default_fields:
        params['fields'] = fields or settings.runzero_default_fields

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f'{settings.runzero_api_base}/export/org/assets.jsonl',
            params=params,
            headers={'Authorization': f'Bearer {settings.runzero_export_token}'},
        )
        response.raise_for_status()
        return await ingest_file_bytes(session, settings, data=response.content, source='runzero_api')


async def list_ingestion_runs(session: AsyncSession) -> list[IngestionRun]:
    result = await session.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc()))
    return result.scalars().all()
