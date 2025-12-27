from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from referencing import Registry, Resource

from monopoly_api.paths import resolve_repo_root


SCHEMA_SUFFIX = ".schema.json"


def _schema_dir() -> Path:
    return resolve_repo_root() / "contracts" / "schemas"


def _schema_uris(path: Path, schema_id: str | None) -> list[str]:
    uris: set[str] = set()
    if schema_id:
        uris.add(schema_id)
    uris.add(path.name)
    try:
        uris.add(path.resolve().as_uri())
    except ValueError:
        pass
    try:
        relative = path.resolve().relative_to(resolve_repo_root())
        uris.add(str(relative).replace("\\", "/"))
    except ValueError:
        pass
    return sorted(uris)


@lru_cache(maxsize=1)
def load_schema_registry() -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry = Registry()
    schema_map: dict[str, dict[str, Any]] = {}
    schema_dir = _schema_dir()
    for path in sorted(schema_dir.glob(f"*{SCHEMA_SUFFIX}")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id") or path.name
        if schema_id in schema_map:
            raise ValueError(f"Duplicate schema id '{schema_id}' in {schema_dir}.")
        schema_map[schema_id] = schema
        resource = Resource.from_contents(schema)
        for uri in _schema_uris(path, schema_id):
            registry = registry.with_resource(uri, resource)
    return registry, schema_map


def get_schema_registry() -> Registry:
    registry, _ = load_schema_registry()
    return registry


def get_schema(schema_id: str) -> dict[str, Any]:
    _, schema_map = load_schema_registry()
    if schema_id not in schema_map:
        raise KeyError(f"Schema '{schema_id}' not found in registry.")
    return schema_map[schema_id]
