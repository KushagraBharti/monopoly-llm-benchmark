from __future__ import annotations

from typing import Any

from monopoly_engine import Engine


def choose_action(decision: dict[str, Any]) -> dict[str, Any]:
    legal_actions = {entry["action"] for entry in decision.get("legal_actions", [])}
    action_name = "BUY_PROPERTY" if "BUY_PROPERTY" in legal_actions else "START_AUCTION"
    state = decision.get("state", {})
    active_player_id = state.get("active_player_id")
    space_index = 0
    for player in state.get("players", []):
        if player.get("player_id") == active_player_id:
            space_index = int(player.get("position", 0))
            break
    return {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": action_name,
        "args": {"space_index": space_index},
    }


def collect_events(engine: Engine, limit: int | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    while not engine.is_game_over():
        _, new_events, decision, _ = engine.advance_until_decision(max_steps=1)
        if new_events:
            events.extend(new_events)
        if decision is not None:
            action = choose_action(decision)
            _, action_events, _, _ = engine.apply_action(action)
            events.extend(action_events)
        if limit is not None and len(events) >= limit:
            return events[:limit]
        if not new_events and decision is None:
            break
    return events
