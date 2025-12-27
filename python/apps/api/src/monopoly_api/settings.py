from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    runs_dir: Path
    api_host: str
    api_port: int
    players_config_path: Path


def load_settings() -> Settings:
    load_dotenv()
    runs_dir = Path(os.getenv("RUNS_DIR", "./runs"))
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    default_players_path = Path(__file__).resolve().parent / "config" / "players.json"
    players_config_path = Path(os.getenv("PLAYERS_CONFIG_PATH", str(default_players_path)))
    return Settings(
        runs_dir=runs_dir,
        api_host=api_host,
        api_port=api_port,
        players_config_path=players_config_path,
    )
