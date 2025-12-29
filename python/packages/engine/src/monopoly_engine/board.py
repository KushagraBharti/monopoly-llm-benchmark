from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import SpaceState


def _resolve_repo_root() -> Path:
    start = Path(__file__).resolve()
    current = start if start.is_dir() else start.parent
    for parent in [current, *current.parents]:
        if (parent / "contracts").is_dir():
            return parent
    raise RuntimeError("Repo root not found (expected a contracts/ directory).")


@lru_cache(maxsize=1)
def _load_board_spec() -> dict[str, Any]:
    board_path = _resolve_repo_root() / "contracts" / "data" / "board.json"
    spec = json.loads(board_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != "v1":
        raise ValueError("Unsupported board schema_version (expected v1).")
    return spec


def _required_list(value: Any, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"board.json field '{field}' must be a list")
    return value


def _required_dict(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"board.json field '{field}' must be an object")
    return value


def _parse_int_keyed_dict(value: Any, *, field: str) -> dict[int, Any]:
    raw = _required_dict(value, field=field)
    parsed: dict[int, Any] = {}
    for key, entry in raw.items():
        try:
            int_key = int(key)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"board.json field '{field}' has non-integer key '{key}'") from exc
        parsed[int_key] = entry
    return parsed


def normalize_space_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    return cleaned.strip("_").upper()


def _build_board_spec_tuples(spec: dict[str, Any]) -> list[tuple[int, str, str, str | None, int | None]]:
    spaces = _required_list(spec.get("spaces"), field="spaces")
    tuples: list[tuple[int, str, str, str | None, int | None]] = []
    for space in spaces:
        if not isinstance(space, dict):
            raise TypeError("board.json spaces[] must contain objects")
        index = int(space.get("index", 0))
        kind = str(space.get("kind", ""))
        name = str(space.get("name", ""))
        group = space.get("group")
        if group is not None:
            group = str(group)
        price = space.get("price")
        if price is not None:
            price = int(price)
        tuples.append((index, kind, name, group, price))
    return tuples


_SPEC = _load_board_spec()

BOARD_SPEC: list[tuple[int, str, str, str | None, int | None]] = _build_board_spec_tuples(_SPEC)
SPACE_KEY_BY_INDEX: dict[int, str] = {
    index: normalize_space_key(name) for index, _, name, _, _ in BOARD_SPEC
}
SPACE_INDEX_BY_KEY: dict[str, int] = {space_key: index for index, space_key in SPACE_KEY_BY_INDEX.items()}

PROPERTY_RENT_TABLES: dict[int, list[int]] = {
    key: [int(value) for value in _required_list(entry, field=f"property_rent_tables.{key}")]
    for key, entry in _parse_int_keyed_dict(_SPEC.get("property_rent_tables"), field="property_rent_tables").items()
}

RAILROAD_RENTS = [int(value) for value in _required_list(_SPEC.get("railroad_rents"), field="railroad_rents")]
UTILITY_RENT_MULTIPLIER = {
    key: int(value)
    for key, value in _parse_int_keyed_dict(_SPEC.get("utility_rent_multiplier"), field="utility_rent_multiplier").items()
}
TAX_AMOUNTS = {
    key: int(value)
    for key, value in _parse_int_keyed_dict(_SPEC.get("tax_amounts"), field="tax_amounts").items()
}
HOUSE_COST_BY_GROUP: dict[str, int] = {
    str(key): int(value)
    for key, value in _required_dict(_SPEC.get("house_cost_by_group"), field="house_cost_by_group").items()
}

OWNABLE_KINDS = {"PROPERTY", "RAILROAD", "UTILITY"}

GROUP_INDEXES: dict[str, list[int]] = {}
for index, kind, _, group, _ in BOARD_SPEC:
    if group:
        GROUP_INDEXES.setdefault(group, []).append(index)


def build_board() -> list[SpaceState]:
    return [
        SpaceState(index=index, kind=kind, name=name, group=group, price=price)
        for index, kind, name, group, price in BOARD_SPEC
    ]
