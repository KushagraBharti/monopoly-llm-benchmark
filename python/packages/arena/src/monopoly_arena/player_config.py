from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SYSTEM_PROMPT_V1 = """You are an expert Monopoly player controlling EXACTLY ONE player in an ongoing 4-player Monopoly game.
Your only objective is to win the game. Win.

You will repeatedly receive the latest situation. Do NOT assume you remember prior turns unless it appears in the provided memory.
The engine is authoritative: it enforces rules, applies forced payments, and rejects illegal actions. You decide only when prompted.

You will receive:

* full_state: the latest compact game state (authoritative)
* decision: the current decision id/type and legal actions (authoritative)
* decision_focus: scenario-specific context for this decision (authoritative)
* memory: recent public chat, recent actions, and your recent private thoughts (authoritative)

Rules:

1. You MUST respond with exactly one tool call that matches one of the legal actions.
2. Never invent tools, actions, or arguments. Obey the args schema.
3. If the chosen tool supports public_message and private_thought fields, include BOTH (short, relevant).
4. Be strategic, consistent, and concise. You may adopt any personality/strategy (aggressive, deceptive, cooperative, etc.) as long as your goal is to win.
"""
DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT_V1
EXPECTED_PLAYER_COUNT = 4


def derive_model_display_name(model_id: str) -> str:
    if "/" in model_id:
        return model_id.split("/")[-1]
    return model_id


@dataclass(frozen=True)
class PlayerConfig:
    player_id: str
    name: str
    openrouter_model_id: str
    model_display_name: str
    system_prompt: str

    def to_status(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "openrouter_model_id": self.openrouter_model_id,
            "model_display_name": self.model_display_name,
        }


def _normalize_player_entry(
    entry: dict[str, Any],
    *,
    default_model_id: str,
    default_system_prompt: str,
) -> PlayerConfig:
    player_id = entry.get("player_id") or entry.get("id")
    if not player_id:
        raise ValueError("Player config missing player_id.")
    name = entry.get("name") or player_id
    model_id = entry.get("openrouter_model_id") or default_model_id
    system_prompt = entry.get("system_prompt") or default_system_prompt
    return PlayerConfig(
        player_id=player_id,
        name=name,
        openrouter_model_id=model_id,
        model_display_name=derive_model_display_name(model_id),
        system_prompt=system_prompt,
    )


def load_player_config_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        players = data.get("players", [])
    else:
        players = data
    if not isinstance(players, list):
        return []
    return [entry for entry in players if isinstance(entry, dict)]


def build_player_configs(
    *,
    requested_players: list[dict[str, Any]] | None,
    config_path: Path,
) -> list[PlayerConfig]:
    default_model_id = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
    default_system_prompt = os.getenv("OPENROUTER_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)

    file_entries = load_player_config_file(config_path)
    if not file_entries:
        raise ValueError(f"players.json missing or invalid at {config_path}.")
    _validate_player_entries(file_entries, source=f"players.json ({config_path})")
    defaults = {entry.get("player_id"): entry for entry in file_entries if entry.get("player_id")}

    if requested_players is not None:
        _validate_player_entries(requested_players, source="run/start request")
        overrides = {entry.get("player_id"): entry for entry in requested_players}
        for player_id in overrides:
            if player_id not in defaults:
                raise ValueError(f"Unknown player_id '{player_id}' in run/start request.")
        merged_entries: list[dict[str, Any]] = []
        for entry in file_entries:
            player_id = entry.get("player_id")
            merged = dict(entry)
            override = overrides.get(player_id)
            if override:
                merged.update(override)
            merged_entries.append(merged)
        return [
            _normalize_player_entry(
                entry,
                default_model_id=default_model_id,
                default_system_prompt=default_system_prompt,
            )
            for entry in merged_entries
        ]

    return [
        _normalize_player_entry(
            entry,
            default_model_id=default_model_id,
            default_system_prompt=default_system_prompt,
        )
        for entry in file_entries
    ]


def _validate_player_entries(entries: list[dict[str, Any]], *, source: str) -> None:
    if len(entries) != EXPECTED_PLAYER_COUNT:
        raise ValueError(f"{source} must define exactly {EXPECTED_PLAYER_COUNT} players.")
    seen: set[str] = set()
    for entry in entries:
        player_id = entry.get("player_id")
        if not player_id:
            raise ValueError(f"{source} contains a player without player_id.")
        if player_id in seen:
            raise ValueError(f"{source} contains duplicate player_id '{player_id}'.")
        seen.add(player_id)

