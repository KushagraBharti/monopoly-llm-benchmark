from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from monopoly_telemetry import RunFiles


@dataclass
class DecisionSummary:
    decision_id: str
    turn_index: int | None = None
    player_id: str | None = None
    decision_type: str | None = None
    retry_used: bool | None = None
    fallback_used: bool | None = None
    timestamp: str | None = None
    request_start_ms: int | None = None
    response_end_ms: int | None = None
    latency_ms: int | None = None
    phase: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "turn_index": self.turn_index,
            "player_id": self.player_id,
            "decision_type": self.decision_type,
            "retry_used": self.retry_used,
            "fallback_used": self.fallback_used,
            "timestamp": self.timestamp,
            "request_start_ms": self.request_start_ms,
            "response_end_ms": self.response_end_ms,
            "latency_ms": self.latency_ms,
            "phase": self.phase,
        }


class DecisionIndex:
    def __init__(self, run_files: RunFiles) -> None:
        self._run_files = run_files
        self._summaries: dict[str, DecisionSummary] = {}
        self._resolved_entries: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._prompt_prefixes: dict[str, str] = {}
        self._loaded = False

    def record_entry(self, entry: dict[str, Any]) -> None:
        decision_id = entry.get("decision_id")
        if not decision_id:
            return
        summary = self._summaries.get(decision_id)
        if summary is None:
            summary = DecisionSummary(decision_id=str(decision_id))
            self._summaries[decision_id] = summary
            self._order.append(decision_id)
            self._prompt_prefixes[decision_id] = f"decision_{_safe_decision_id(str(decision_id))}"
        summary.turn_index = entry.get("turn_index", summary.turn_index)
        summary.player_id = entry.get("player_id", summary.player_id)
        summary.decision_type = entry.get("decision_type", summary.decision_type)
        summary.timestamp = entry.get("timestamp", summary.timestamp)
        summary.phase = entry.get("phase", summary.phase)
        summary.request_start_ms = entry.get("request_start_ms", summary.request_start_ms)
        summary.response_end_ms = entry.get("response_end_ms", summary.response_end_ms)
        summary.latency_ms = entry.get("latency_ms", summary.latency_ms)
        if entry.get("phase") == "decision_resolved":
            summary.retry_used = entry.get("retry_used", summary.retry_used)
            summary.fallback_used = entry.get("fallback_used", summary.fallback_used)
            self._resolved_entries[decision_id] = entry

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_loaded()
        limit = max(0, int(limit))
        results: list[dict[str, Any]] = []
        for decision_id in reversed(self._order):
            summary = self._summaries.get(decision_id)
            if summary is None:
                continue
            results.append(summary.to_dict())
            if len(results) >= limit:
                break
        return results

    def ordered(self, limit: int | None = None) -> list[dict[str, Any]]:
        self._ensure_loaded()
        results: list[dict[str, Any]] = []
        for decision_id in self._order:
            summary = self._summaries.get(decision_id)
            if summary is None:
                continue
            results.append(summary.to_dict())
            if limit is not None and len(results) >= limit:
                break
        return results

    def get_bundle(self, decision_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        summary = self._summaries.get(decision_id)
        attempts = self._load_attempts(decision_id)
        resolved = self._resolved_entries.get(decision_id)
        if summary is None and not attempts and resolved is None:
            return None

        final_action = None
        retry_used = None
        fallback_used = None
        fallback_reason = None
        if resolved:
            final_action = resolved.get("final_action")
            retry_used = resolved.get("retry_used")
            fallback_used = resolved.get("fallback_used")
            fallback_reason = resolved.get("fallback_reason")

        if attempts:
            parsed = attempts[-1].get("parsed")
            if isinstance(parsed, dict):
                final_action = final_action or parsed.get("final_action")
                retry_used = retry_used if retry_used is not None else parsed.get("retry_used")
                fallback_used = fallback_used if fallback_used is not None else parsed.get("fallback_used")
                fallback_reason = fallback_reason if fallback_reason is not None else parsed.get("fallback_reason")

        timing = {
            "request_start_ms": None,
            "response_end_ms": None,
            "latency_ms": None,
        }
        if resolved:
            timing["request_start_ms"] = resolved.get("request_start_ms")
            timing["response_end_ms"] = resolved.get("response_end_ms")
            timing["latency_ms"] = resolved.get("latency_ms")
        elif summary is not None:
            timing["request_start_ms"] = summary.request_start_ms
            timing["response_end_ms"] = summary.response_end_ms
            timing["latency_ms"] = summary.latency_ms

        return {
            "decision_id": decision_id,
            "summary": summary.to_dict() if summary else None,
            "attempts": [
                {
                    "attempt_index": attempt.get("attempt_index"),
                    "system_prompt": attempt.get("system"),
                    "user_payload": attempt.get("user"),
                    "tools": attempt.get("tools"),
                    "response": attempt.get("response"),
                    "parsed_tool_call": attempt.get("parsed_tool_call"),
                    "validation_errors": attempt.get("validation_errors"),
                    "error_reason": attempt.get("error_reason"),
                    "tool_action": attempt.get("tool_action"),
                }
                for attempt in attempts
            ],
            "final_action": final_action,
            "retry_used": retry_used,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "timing": timing,
        }

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._run_files.decisions_path.exists():
            return
        for line in self._run_files.decisions_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                self.record_entry(entry)

    def _load_attempts(self, decision_id: str) -> list[dict[str, Any]]:
        prompts_dir = self._run_files.prompts_dir
        if not prompts_dir.exists():
            return []
        safe = _safe_decision_id(decision_id)
        base_prefix = self._prompt_prefixes.get(decision_id, f"decision_{safe}")
        attempts: dict[int, dict[str, Any]] = {}
        for path in prompts_dir.iterdir():
            if not path.is_file():
                continue
            name = path.name
            if not name.startswith(base_prefix):
                continue
            suffix = name[len(base_prefix):]
            if not suffix.startswith("_"):
                continue
            attempt_index = 0
            remainder = suffix[1:]
            if remainder.startswith("retry"):
                remainder = remainder[len("retry"):]
                attempt_split = remainder.split("_", 1)
                if len(attempt_split) != 2:
                    continue
                try:
                    attempt_index = int(attempt_split[0])
                except ValueError:
                    continue
                remainder = attempt_split[1]
            kind_split = remainder.split(".", 1)
            if len(kind_split) != 2:
                continue
            kind = kind_split[0]
            if kind not in {"system", "user", "tools", "response", "parsed"}:
                continue
            attempt = attempts.setdefault(attempt_index, {"attempt_index": attempt_index})
            if kind == "system":
                attempt["system"] = path.read_text(encoding="utf-8")
                continue
            parsed = _load_json(path)
            attempt[kind] = parsed
            if kind == "parsed" and isinstance(parsed, dict):
                attempt["parsed_tool_call"] = parsed.get("parsed_tool_call")
                attempt["validation_errors"] = parsed.get("validation_errors") or []
                attempt["error_reason"] = parsed.get("error_reason")
                attempt["tool_action"] = parsed.get("tool_action")
        return [attempts[idx] for idx in sorted(attempts)]


def _safe_decision_id(decision_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", decision_id.strip())
    safe = safe.strip("._-") or "decision"
    return safe


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
