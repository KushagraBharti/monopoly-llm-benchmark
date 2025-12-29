from __future__ import annotations

from typing import Any

from monopoly_engine import Engine


def choose_action(decision: dict[str, Any]) -> dict[str, Any]:
    legal_actions = [entry["action"] for entry in decision.get("legal_actions", [])]
    if "buy_property" in legal_actions:
        action_name = "buy_property"
    elif "start_auction" in legal_actions:
        action_name = "start_auction"
    elif "pay_jail_fine" in legal_actions:
        action_name = "pay_jail_fine"
    elif "roll_for_doubles" in legal_actions:
        action_name = "roll_for_doubles"
    elif "use_get_out_of_jail_card" in legal_actions:
        action_name = "use_get_out_of_jail_card"
    elif legal_actions:
        action_name = legal_actions[0]
    else:
        action_name = "NOOP"
    args: dict[str, Any] = {}
    if action_name == "NOOP":
        args = {"reason": "test"}
    return {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": action_name,
        "args": args,
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
