from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Iterable

from app.services.ingestion.mapping import ensure_list, get_mapped_value
from app.services.ingestion.types import NormalizedAsset, NormalizedObservation

DEVICE_TYPE_MAP = {
    'server': 'server',
    'desktop': 'desktop',
    'switch': 'switch',
    'router': 'router',
    'hypervisor': 'hypervisor',
    'storage': 'storage',
    'backup': 'backup',
}
VERSION_PATTERN = re.compile(r'Version\s+([A-Za-z0-9._-]+)')


def _from_epoch(value: str | int | float | None, fallback: datetime | None = None) -> datetime:
    if value in (None, ''):
        return fallback or datetime.now(UTC)
    return datetime.fromtimestamp(float(value), tz=UTC)


def _parse_version_from_sysdesc(sys_desc: str | None) -> str | None:
    if not sys_desc:
        return None
    match = VERSION_PATTERN.search(sys_desc)
    return match.group(1) if match else None


def parse_dummy_service_export(payload: dict[str, dict[str, Any]]) -> list[NormalizedAsset]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for _, service in payload.items():
        address = service.get('service.address')
        if address:
            grouped[str(address)].append(service)

    assets: list[NormalizedAsset] = []
    for address, services in grouped.items():
        timestamps = [_from_epoch(service.get('ts')) for service in services]
        device_hint = next((service.get('fp.hw.device') for service in services if service.get('fp.hw.device')), 'other')
        asset_type = DEVICE_TYPE_MAP.get(str(device_hint).strip().lower(), 'other')
        hostname = next((service.get('snmp.hostname') or service.get('snmp.sysName') for service in services if service.get('snmp.hostname') or service.get('snmp.sysName')), None)
        vendor = next((service.get('fp.hw.vendor') for service in services if service.get('fp.hw.vendor')), None)
        model = next((service.get('fp.hw.product') for service in services if service.get('fp.hw.product')), None)
        serials: list[str] = []
        macs: list[str] = []
        runzero_ids: list[str] = []
        for service in services:
            serials.extend(ensure_list(service.get('snmp.serialNumbers')))
            macs.extend(ensure_list(service.get('snmp.interfaceMacs')))
            runzero_ids.extend(ensure_list(service.get('service.id')))
        os_service = next((service for service in services if service.get('fp.os.version') or service.get('snmp.sysDesc')), services[0])
        version = os_service.get('fp.os.version') or _parse_version_from_sysdesc(os_service.get('snmp.sysDesc')) or 'unknown'
        stable_key = '|'.join(part for part in ['dummy', hostname or '', serials[0] if serials else '', address] if part)
        assets.append(
            NormalizedAsset(
                asset_type=asset_type,
                vendor=vendor,
                model=model,
                environment='other',
                hostname=hostname,
                identifiers={
                    'ips': sorted(set([address])),
                    'macs': sorted(set(macs)),
                    'serials': sorted(set(serials)),
                    'runzero_ids': sorted(set(runzero_ids)),
                    'stable_keys': [stable_key],
                },
                first_seen_at=min(timestamps),
                last_seen_at=max(timestamps),
                observations=[
                    NormalizedObservation(
                        component_type_key='OS',
                        version=str(version),
                        observed_at=max(timestamps),
                        source='runzero',
                        raw={'service_records': services},
                    )
                ],
            )
        )
    return assets


def parse_runzero_assets(records: Iterable[dict[str, Any]], mapping: dict[str, Any]) -> list[NormalizedAsset]:
    assets: list[NormalizedAsset] = []
    identity = mapping.get('identity', {})
    timestamps = mapping.get('timestamps', {})
    components = mapping.get('components', {})

    for raw_asset in records:
        hostname = get_mapped_value(raw_asset, identity.get('hostname'))
        vendor = get_mapped_value(raw_asset, identity.get('vendor'))
        model = get_mapped_value(raw_asset, identity.get('model'))
        asset_type = str(get_mapped_value(raw_asset, identity.get('asset_type')) or 'other').lower()
        if asset_type not in DEVICE_TYPE_MAP.values():
            asset_type = 'other'
        environment = get_mapped_value(raw_asset, identity.get('environment')) or 'other'
        stable_ids = ensure_list(get_mapped_value(raw_asset, identity.get('stable_ids')))
        serials = ensure_list(get_mapped_value(raw_asset, identity.get('serials')))
        ips = ensure_list(get_mapped_value(raw_asset, identity.get('ips')))
        macs = ensure_list(get_mapped_value(raw_asset, identity.get('macs')))
        first_seen = _from_epoch(get_mapped_value(raw_asset, timestamps.get('first_seen_at')), datetime.now(UTC))
        last_seen = _from_epoch(get_mapped_value(raw_asset, timestamps.get('last_seen_at')), first_seen)
        stable_key_parts = stable_ids or [hostname or '', serials[0] if serials else '', macs[0] if macs else '']
        stable_key = '|'.join(part for part in stable_key_parts if part)
        observations: list[NormalizedObservation] = []
        for component_key, component_mapping in components.items():
            version = get_mapped_value(raw_asset, component_mapping.get('version'))
            if version in (None, ''):
                continue
            observed_at = _from_epoch(get_mapped_value(raw_asset, component_mapping.get('observed_at')), last_seen)
            observations.append(
                NormalizedObservation(
                    component_type_key=component_key,
                    version=str(version),
                    observed_at=observed_at,
                    source='runzero',
                    raw={'asset': raw_asset, 'component_type_key': component_key},
                )
            )
        assets.append(
            NormalizedAsset(
                asset_type=asset_type,
                vendor=str(vendor) if vendor is not None else None,
                model=str(model) if model is not None else None,
                environment=str(environment) if environment is not None else None,
                hostname=str(hostname) if hostname is not None else None,
                identifiers={
                    'ips': sorted(set(ips)),
                    'macs': sorted(set(macs)),
                    'serials': sorted(set(serials)),
                    'runzero_ids': sorted(set(stable_ids)),
                    'stable_keys': [stable_key] if stable_key else [],
                },
                first_seen_at=first_seen,
                last_seen_at=last_seen,
                observations=observations,
            )
        )
    return assets


def parse_jsonl_bytes(data: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in data.decode('utf-8').splitlines() if line.strip()]


def parse_json_bytes(data: bytes) -> Any:
    return json.loads(data.decode('utf-8'))
