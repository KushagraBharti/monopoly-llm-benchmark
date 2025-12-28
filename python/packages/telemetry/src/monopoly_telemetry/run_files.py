from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .writer_jsonl import append_jsonl


@dataclass
class RunFiles:
    run_id: str
    run_dir: Path
    events_path: Path
    decisions_path: Path
    snapshots_dir: Path
    prompts_dir: Path
    summary_path: Path

    def write_event(self, event: dict[str, Any]) -> None:
        append_jsonl(self.events_path, event)

    def write_snapshot(self, snapshot: dict[str, Any]) -> Path:
        turn_index = snapshot.get("turn_index", 0)
        canonical_path = self.snapshots_dir / f"turn_{turn_index:04d}.json"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=True)
        if not canonical_path.exists():
            canonical_path.write_text(payload, encoding="utf-8")
            return canonical_path

        existing = canonical_path.read_text(encoding="utf-8")
        if existing == payload:
            return canonical_path

        phase = str(snapshot.get("phase") or "UNKNOWN")
        variant_kind = "decision" if phase == "AWAITING_DECISION" else "snapshot"
        variant_path = _next_snapshot_variant_path(self.snapshots_dir, int(turn_index), variant_kind)
        variant_path.write_text(payload, encoding="utf-8")
        return variant_path

    def write_summary(self, summary: dict[str, Any]) -> None:
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.write_text(
            json.dumps(summary, separators=(",", ":"), ensure_ascii=True),
            encoding="utf-8",
        )

    def write_decision(self, decision_entry: dict[str, Any]) -> None:
        append_jsonl(self.decisions_path, decision_entry)

    def write_prompt_artifacts(
        self,
        *,
        decision_id: str,
        attempt_index: int,
        system_prompt: str | None,
        user_payload: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
        response: dict[str, Any] | None,
        parsed: dict[str, Any] | None,
    ) -> None:
        prefix = _prompt_file_prefix(decision_id, attempt_index=attempt_index)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        if system_prompt is not None:
            (self.prompts_dir / f"{prefix}_system.txt").write_text(system_prompt, encoding="utf-8")
        if user_payload is not None:
            (self.prompts_dir / f"{prefix}_user.json").write_text(
                json.dumps(user_payload, separators=(",", ":"), ensure_ascii=True),
                encoding="utf-8",
            )
        if tools is not None:
            (self.prompts_dir / f"{prefix}_tools.json").write_text(
                json.dumps(tools, separators=(",", ":"), ensure_ascii=True),
                encoding="utf-8",
            )
        if response is not None:
            (self.prompts_dir / f"{prefix}_response.json").write_text(
                json.dumps(response, separators=(",", ":"), ensure_ascii=True),
                encoding="utf-8",
            )
        if parsed is not None:
            (self.prompts_dir / f"{prefix}_parsed.json").write_text(
                json.dumps(parsed, separators=(",", ":"), ensure_ascii=True),
                encoding="utf-8",
            )


def init_run_files(runs_dir: Path, run_id: str) -> RunFiles:
    run_dir = runs_dir / run_id
    snapshots_dir = run_dir / "state"
    prompts_dir = run_dir / "prompts"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return RunFiles(
        run_id=run_id,
        run_dir=run_dir,
        events_path=run_dir / "events.jsonl",
        decisions_path=run_dir / "decisions.jsonl",
        snapshots_dir=snapshots_dir,
        prompts_dir=prompts_dir,
        summary_path=run_dir / "summary.json",
    )


def _prompt_file_prefix(decision_id: str, *, attempt_index: int) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", decision_id.strip())
    safe = safe.strip("._-") or "decision"
    if attempt_index <= 0:
        return f"decision_{safe}"
    return f"decision_{safe}_retry{attempt_index}"


def _next_snapshot_variant_path(snapshots_dir: Path, turn_index: int, kind: str) -> Path:
    prefix = f"turn_{turn_index:04d}_{kind}_"
    pattern = re.compile(rf"^{re.escape(prefix)}(?P<num>[0-9]+)\.json$")
    max_seen = 0
    if snapshots_dir.exists():
        for path in snapshots_dir.iterdir():
            if not path.is_file():
                continue
            match = pattern.match(path.name)
            if not match:
                continue
            try:
                num = int(match.group("num"))
            except (TypeError, ValueError):
                continue
            if num > max_seen:
                max_seen = num
    return snapshots_dir / f"{prefix}{max_seen + 1:04d}.json"
