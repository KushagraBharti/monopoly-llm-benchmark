from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values

from monopoly_api.paths import (
    default_players_config_path,
    resolve_repo_path,
    resolve_repo_root,
)


@dataclass(frozen=True)
class Settings:
    runs_dir: Path
    api_host: str
    api_port: int
    players_config_path: Path


def load_settings() -> Settings:
    _load_env()
    runs_dir = resolve_repo_path(os.getenv("RUNS_DIR", str(resolve_repo_root() / "runs")))
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    players_config_path = resolve_repo_path(
        os.getenv("PLAYERS_CONFIG_PATH", str(default_players_config_path()))
    )
    return Settings(
        runs_dir=runs_dir,
        api_host=api_host,
        api_port=api_port,
        players_config_path=players_config_path,
    )


def _load_env() -> None:
    repo_root = resolve_repo_root()
    env_paths = [
        repo_root / ".env",
        repo_root / "python" / ".env",
        repo_root / "python" / "apps" / "api" / ".env",
    ]
    loaded_keys: set[str] = set()
    for path in env_paths:
        if not path.exists():
            continue
        values = dotenv_values(path)
        for key, value in values.items():
            if value is None:
                continue
            if key not in os.environ or key in loaded_keys:
                os.environ[key] = value
                loaded_keys.add(key)
