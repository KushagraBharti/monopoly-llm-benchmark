from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    runs_dir: Path
    api_host: str
    api_port: int


def load_settings() -> Settings:
    runs_dir = Path(os.getenv("RUNS_DIR", "./runs"))
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    return Settings(runs_dir=runs_dir, api_host=api_host, api_port=api_port)
