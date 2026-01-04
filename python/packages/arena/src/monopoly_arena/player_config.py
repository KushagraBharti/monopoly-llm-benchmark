from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SYSTEM_PROMPT_V1 = """
You are an autonomous player in a game of Monopoly competing against other AI players.

Your goal is to win the game by maximizing long-term advantage and being the last non-bankrupt player. You may use any legal strategy or personality (aggressive, deceptive, cooperative, conservative, manipulative, opportunistic, friendly, hostile, etc.) and may adapt dynamically as the game evolves.

You will receive the following inputs:

1) System Prompt (this message): authoritative instructions.
2) Full State: the complete, authoritative game state. Read and rely only on this.
3) Decision + Decision Focus: the current scenario and the list of legal actions.
4) Chat & Personal Log: recent public chat/events and your own prior private thoughts.

### Action Rules
- Make exactly one tool call per decision.
- Use only tools listed as legal for that decision.
- Never invent tools, arguments, or targets.
- Obey the provided argument schema exactly.
- If a tool requires no arguments, pass none.

### Messages
Each action must include:
- Public Message: visible to other players. Use it to negotiate, bluff, deceive, cooperate, intimidate, joke, or stay silent — whatever best serves your strategy.
- Private Thoughts: visible only to you. Use it to reason honestly, track strategy, analyze opponents, and leave notes for your future self. Be concise but clear.

### Strategy Guidance
- Play strategically with long-term outcomes in mind.
- Observe opponents and adapt.
- Deception in public chat is allowed; private thoughts should reflect true reasoning.
- Be consistent unless there is a reason to change.
- Prefer concise reasoning and communication.

Your role is not to explain rules or debug the system.  
Your role is to **play Monopoly and win**.

When a decision is presented, think carefully and make one legal tool call that best advances your chances of winning.
"""

DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT_V1
EXPECTED_PLAYER_COUNT = 4
ALLOWED_REASONING_EFFORT = {"low", "medium", "high"}


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
    reasoning: dict[str, Any] | None

    def to_status(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "player_id": self.player_id,
            "name": self.name,
            "openrouter_model_id": self.openrouter_model_id,
            "model_display_name": self.model_display_name,
        }
        if self.reasoning is not None:
            payload["reasoning"] = self.reasoning
        return payload


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
    reasoning = _normalize_reasoning(entry.get("reasoning"))
    return PlayerConfig(
        player_id=player_id,
        name=name,
        openrouter_model_id=model_id,
        model_display_name=derive_model_display_name(model_id),
        system_prompt=system_prompt,
        reasoning=reasoning,
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
    default_system_prompt = DEFAULT_SYSTEM_PROMPT

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
        _validate_reasoning(entry.get("reasoning"), source=source, player_id=player_id)


def _validate_reasoning(reasoning: Any, *, source: str, player_id: str) -> None:
    if reasoning is None:
        return
    if not isinstance(reasoning, dict):
        raise ValueError(f"{source} player '{player_id}' reasoning must be an object.")
    if "effort" not in reasoning:
        raise ValueError(f"{source} player '{player_id}' reasoning.effort is required.")
    effort = reasoning.get("effort")
    if effort not in ALLOWED_REASONING_EFFORT:
        raise ValueError(
            f"{source} player '{player_id}' reasoning.effort must be one of: "
            f"{', '.join(sorted(ALLOWED_REASONING_EFFORT))}."
        )


def _normalize_reasoning(reasoning: Any) -> dict[str, Any] | None:
    if reasoning is None:
        return None
    if not isinstance(reasoning, dict):
        raise ValueError("Player reasoning must be an object.")
    if "effort" not in reasoning:
        raise ValueError("Player reasoning.effort is required.")
    effort = reasoning.get("effort")
    if effort not in ALLOWED_REASONING_EFFORT:
        raise ValueError(
            "Player reasoning.effort must be one of: "
            f"{', '.join(sorted(ALLOWED_REASONING_EFFORT))}."
        )
    return dict(reasoning)
