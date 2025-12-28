from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def resolve_repo_root() -> Path:
    start = Path(__file__).resolve()
    current = start if start.is_dir() else start.parent
    for parent in [current, *current.parents]:
        if (parent / "contracts").is_dir():
            return parent
    raise RuntimeError("Repo root not found (expected a contracts/ directory).")


def contracts_schema_path(name: str) -> Path:
    return resolve_repo_root() / "contracts" / "schemas" / name


def api_dir() -> Path:
    return resolve_repo_root() / "python" / "apps" / "api"


def default_players_config_path() -> Path:
    return api_dir() / "src" / "monopoly_api" / "config" / "players.json"


def resolve_repo_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return resolve_repo_root() / candidate

