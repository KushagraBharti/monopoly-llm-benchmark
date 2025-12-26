from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .writer_jsonl import append_jsonl


@dataclass
class RunFiles:
    run_id: str
    run_dir: Path
    events_path: Path
    snapshots_dir: Path
    summary_path: Path

    def write_event(self, event: dict[str, Any]) -> None:
        append_jsonl(self.events_path, event)

    def write_snapshot(self, snapshot: dict[str, Any]) -> Path:
        turn_index = snapshot.get("turn_index", 0)
        path = self.snapshots_dir / f"turn_{turn_index:04d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(snapshot, separators=(",", ":"), ensure_ascii=True),
            encoding="utf-8",
        )
        return path

    def write_summary(self, summary: dict[str, Any]) -> None:
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.write_text(
            json.dumps(summary, separators=(",", ":"), ensure_ascii=True),
            encoding="utf-8",
        )


def init_run_files(runs_dir: Path, run_id: str) -> RunFiles:
    run_dir = runs_dir / run_id
    snapshots_dir = run_dir / "state"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return RunFiles(
        run_id=run_id,
        run_dir=run_dir,
        events_path=run_dir / "events.jsonl",
        snapshots_dir=snapshots_dir,
        summary_path=run_dir / "summary.json",
    )
