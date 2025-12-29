from __future__ import annotations

from typing import Any

from monopoly_engine import Engine


def choose_action(decision: dict[str, Any]) -> dict[str, Any]:
    decision_type = decision.get("decision_type")
    legal_actions = [entry["action"] for entry in decision.get("legal_actions", [])]
    if decision_type == "AUCTION_BID_DECISION":
        auction = decision.get("state", {}).get("auction", {})
        current_high_bid = int(auction.get("current_high_bid", 0) or 0)
        min_next_bid = current_high_bid + 1
        player_cash = None
        for player in decision.get("state", {}).get("players", []):
            if player.get("player_id") == decision.get("player_id"):
                player_cash = int(player.get("cash", 0))
                break
        if "bid_auction" in legal_actions and player_cash is not None and player_cash >= min_next_bid:
            action_name = "bid_auction"
            args = {"bid_amount": min_next_bid}
            return {
                "schema_version": "v1",
                "decision_id": decision["decision_id"],
                "action": action_name,
                "args": args,
            }
        if "drop_out" in legal_actions:
            action_name = "drop_out"
            args: dict[str, Any] = {}
            return {
                "schema_version": "v1",
                "decision_id": decision["decision_id"],
                "action": action_name,
                "args": args,
            }
    if decision_type == "TRADE_RESPONSE_DECISION":
        if "reject_trade" in legal_actions:
            return {
                "schema_version": "v1",
                "decision_id": decision["decision_id"],
                "action": "reject_trade",
                "args": {},
            }
        if "accept_trade" in legal_actions:
            return {
                "schema_version": "v1",
                "decision_id": decision["decision_id"],
                "action": "accept_trade",
                "args": {},
            }
        if "counter_trade" in legal_actions:
            return {
                "schema_version": "v1",
                "decision_id": decision["decision_id"],
                "action": "counter_trade",
                "args": {
                    "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                    "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                },
            }
    if decision_type == "POST_TURN_ACTION_DECISION" and "end_turn" in legal_actions:
        action_name = "end_turn"
    elif decision_type == "LIQUIDATION_DECISION" and "declare_bankruptcy" in legal_actions:
        action_name = "declare_bankruptcy"
    elif "buy_property" in legal_actions:
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
