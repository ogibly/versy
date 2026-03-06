from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_field_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f'Field mapping file not found: {path}')
    if path.suffix.lower() == '.json':
        return json.loads(path.read_text())
    return yaml.safe_load(path.read_text())


def _split_scalar(value: str) -> list[str]:
    if '\t' in value:
        return [item.strip() for item in value.split('\t') if item.strip()]
    if ',' in value:
        return [item.strip() for item in value.split(',') if item.strip()]
    return [value.strip()] if value.strip() else []


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        flattened: list[str] = []
        for item in value:
            flattened.extend(ensure_list(item))
        return flattened
    if isinstance(value, (set, tuple)):
        flattened: list[str] = []
        for item in value:
            flattened.extend(ensure_list(item))
        return flattened
    if isinstance(value, str):
        return _split_scalar(value)
    return [str(value)]


def get_mapped_value(payload: dict[str, Any], paths: list[str] | None) -> Any:
    if not paths:
        return None
    for path in paths:
        value = _get_path(payload, path)
        if value not in (None, '', []):
            return value
    return None


def _get_path(payload: Any, path: str) -> Any:
    if isinstance(payload, dict) and path in payload:
        return payload[path]
    parts = path.split('.')
    return _walk(payload, parts)


def _walk(current: Any, parts: list[str]) -> Any:
    if not parts:
        return current
    part = parts[0]
    rest = parts[1:]
    if isinstance(current, dict):
        if part in current:
            return _walk(current[part], rest)
        remaining = '.'.join(parts)
        if remaining in current:
            return current[remaining]
        return None
    if isinstance(current, list):
        if part.isdigit():
            index = int(part)
            return _walk(current[index], rest) if index < len(current) else None
        collected = []
        for item in current:
            value = _walk(item, parts)
            if value not in (None, '', []):
                collected.append(value)
        return collected or None
    return None
