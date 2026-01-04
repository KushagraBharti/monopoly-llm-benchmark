from __future__ import annotations

import copy
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from monopoly_engine.board import (
    GROUP_INDEXES,
    HOUSE_COST_BY_GROUP,
    PROPERTY_RENT_TABLES,
    RAILROAD_RENTS,
    SPACE_INDEX_BY_KEY,
    SPACE_KEY_BY_INDEX,
    UTILITY_RENT_MULTIPLIER,
)

from .player_config import DEFAULT_SYSTEM_PROMPT, PlayerConfig


PROMPT_SCHEMA_VERSION = "v1"
JAIL_FINE = 50

def build_space_key_by_index() -> dict[int, str]:
    return dict(SPACE_KEY_BY_INDEX)


SPACE_KEY_BY_INDEX_LOOKUP = build_space_key_by_index()


def space_key_for_index(space_index: int, mapping: dict[int, str]) -> str:
    return mapping.get(space_index, f"SPACE_{space_index}")


@dataclass(slots=True)
class PromptBundle:
    system_prompt: str
    user_payload: dict[str, Any]
    user_content: str
    messages: list[dict[str, Any]]


class PromptMemory:
    def __init__(
        self,
        *,
        space_key_by_index: dict[int, str] | None = None,
        public_chat_limit: int = 20,
        recent_actions_limit: int = 20,
        private_thought_limit: int = 10,
    ) -> None:
        self._space_key_by_index = space_key_by_index or SPACE_KEY_BY_INDEX_LOOKUP
        self._public_chat: deque[dict[str, Any]] = deque(maxlen=public_chat_limit)
        self._recent_actions: deque[dict[str, Any]] = deque(maxlen=recent_actions_limit)
        self._private_thoughts: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=private_thought_limit)
        )

    def update(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        payload = event.get("payload", {})
        turn_index = event.get("turn_index")
        if event_type == "LLM_PUBLIC_MESSAGE":
            self._public_chat.append(
                {
                    "turn_index": turn_index,
                    "from_player_id": payload.get("player_id"),
                    "message": payload.get("message"),
                }
            )
            return
        if event_type == "LLM_PRIVATE_THOUGHT":
            player_id = payload.get("player_id")
            if player_id:
                self._private_thoughts[player_id].append(
                    {
                        "turn_index": turn_index,
                        "thought": payload.get("thought"),
                    }
                )
            return

        summary = _summarize_action_event(event, self._space_key_by_index)
        if summary is not None:
            self._recent_actions.append(summary)

    def snapshot_for_player(self, player_id: str) -> dict[str, Any]:
        return {
            "public_chat_last_20": list(self._public_chat),
            "recent_actions_last_20": list(self._recent_actions),
            "your_private_thoughts_last_10": list(self._private_thoughts.get(player_id, [])),
        }


def _summarize_action_event(
    event: dict[str, Any],
    space_key_by_index: dict[int, str],
) -> dict[str, Any] | None:
    event_type = event.get("type")
    payload = event.get("payload", {})
    turn_index = event.get("turn_index")
    if event_type == "PROPERTY_PURCHASED":
        space_index = payload.get("space_index")
        space_key = space_key_for_index(int(space_index), space_key_by_index) if space_index is not None else None
        return {
            "turn_index": turn_index,
            "type": "PROPERTY_PURCHASED",
            "player_id": payload.get("player_id"),
            "space_key": space_key,
            "amount": payload.get("price"),
        }
    if event_type == "RENT_PAID":
        space_index = payload.get("space_index")
        space_key = space_key_for_index(int(space_index), space_key_by_index) if space_index is not None else None
        return {
            "turn_index": turn_index,
            "type": "RENT_PAID",
            "from_player_id": payload.get("from_player_id"),
            "to_player_id": payload.get("to_player_id"),
            "space_key": space_key,
            "amount": payload.get("amount"),
        }
    if event_type == "SENT_TO_JAIL":
        return {
            "turn_index": turn_index,
            "type": "SENT_TO_JAIL",
            "player_id": payload.get("player_id"),
            "reason": payload.get("reason"),
        }
    if event_type == "CASH_CHANGED":
        reason = payload.get("reason")
        if reason not in {
            "PASS_GO",
            "TAX_INCOME",
            "TAX_LUXURY",
            "BANKRUPTCY",
            "BANKRUPTCY_ASSETS_TO_BANK",
        }:
            return None
        return {
            "turn_index": turn_index,
            "type": "CASH_CHANGED",
            "player_id": payload.get("player_id"),
            "delta": payload.get("delta"),
            "reason": reason,
        }
    return None


def build_system_prompt(player: PlayerConfig) -> str:
    if player.system_prompt:
        return player.system_prompt
    return DEFAULT_SYSTEM_PROMPT


def build_full_state(
    snapshot: dict[str, Any],
    *,
    you_player_id: str,
    memory: PromptMemory,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    players = snapshot.get("players", [])
    if len(players) != 4:
        raise ValueError("Exactly 4 players are required for LLM prompts.")
    board = snapshot.get("board", [])
    player_lookup = {player.get("player_id"): player for player in players}
    you_player = player_lookup.get(you_player_id) or player_lookup.get(snapshot.get("active_player_id"))
    if you_player is None:
        you_player = players[0]

    def build_holdings(player_id: str) -> dict[str, Any]:
        owned: list[dict[str, Any]] = []
        mortgaged: list[dict[str, Any]] = []
        for space in board:
            if space.get("owner_id") != player_id:
                continue
            space_index = int(space.get("index", 0))
            space_key = space_key_for_index(space_index, space_key_by_index)
            mortgaged_flag = bool(space.get("mortgaged"))
            owned.append(
                {
                    "space_key": space_key,
                    "houses": int(space.get("houses", 0)),
                    "hotel": bool(space.get("hotel", False)),
                    "mortgaged": mortgaged_flag,
                }
            )
            if mortgaged_flag:
                mortgaged.append({"space_key": space_key})
        return {"owned": owned, "mortgaged": mortgaged}

    def build_player_view(player: dict[str, Any]) -> dict[str, Any]:
        position_index = int(player.get("position", 0))
        return {
            "player_id": player.get("player_id"),
            "name": player.get("name"),
            "cash": player.get("cash"),
            "position": space_key_for_index(position_index, space_key_by_index),
            "in_jail": bool(player.get("in_jail")),
            "has_get_out_of_jail_card": int(player.get("get_out_of_jail_cards", 0)) > 0,
            "holdings": build_holdings(str(player.get("player_id"))),
        }

    you_view = build_player_view(you_player)
    others = [
        build_player_view(player)
        for player in players
        if player.get("player_id") != you_player.get("player_id")
    ]
    if len(others) != 3:
        raise ValueError("Expected exactly 3 other players for LLM prompts.")

    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "metadata": {
            "run_id": snapshot.get("run_id"),
            "turn_index": snapshot.get("turn_index"),
            "phase": snapshot.get("phase"),
            "active_player_id": snapshot.get("active_player_id"),
            "you_player_id": you_player.get("player_id"),
        },
        "you": you_view,
        "others": others,
        "bank": {
            "houses_remaining": snapshot.get("bank", {}).get("houses_remaining"),
            "hotels_remaining": snapshot.get("bank", {}).get("hotels_remaining"),
        },
        "memory": memory.snapshot_for_player(str(you_player.get("player_id"))),
    }


def _augment_args_schema(args_schema: dict[str, Any] | None) -> dict[str, Any]:
    schema = copy.deepcopy(args_schema or {"type": "object", "additionalProperties": False})
    properties = schema.setdefault("properties", {})
    if isinstance(properties, dict):
        properties.setdefault("public_message", {"type": "string"})
        properties.setdefault("private_thought", {"type": "string"})
    return schema


def build_compact_decision(decision: dict[str, Any]) -> dict[str, Any]:
    legal_actions = []
    for entry in decision.get("legal_actions", []):
        action_name = entry.get("action")
        if not action_name:
            continue
        args_schema = _augment_args_schema(entry.get("args_schema") or {})
        legal_actions.append(
            {
                "action": action_name,
                "args_schema": args_schema,
            }
        )
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "player_id": decision.get("player_id"),
        "legal_actions": legal_actions,
    }


def build_openrouter_tools(decision_payload: dict[str, Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for entry in decision_payload.get("legal_actions", []):
        action_name = entry.get("action")
        if not action_name:
            continue
        args_schema = copy.deepcopy(entry.get("args_schema") or {})
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": action_name,
                    "description": _describe_action(action_name),
                    "parameters": args_schema,
                },
            }
        )
    return tools


def _describe_action(action_name: str) -> str:
    descriptions = {
        "buy_property": "Buy the property at the current space.",
        "start_auction": "Decline purchase and start an auction for the current space.",
        "bid_auction": "Place a bid in the current auction.",
        "drop_out": "Drop out of the current auction.",
        "propose_trade": "Propose a trade to another player.",
        "accept_trade": "Accept the current trade offer.",
        "reject_trade": "Reject the current trade offer.",
        "counter_trade": "Counter the current trade offer.",
        "ROLL_DICE": "Roll the dice to start your move.",
        "roll_for_doubles": "Roll for doubles to attempt to leave jail.",
        "pay_jail_fine": "Pay the jail fine to leave jail.",
        "use_get_out_of_jail_card": "Use a Get Out of Jail Free card.",
        "end_turn": "End your turn.",
        "mortgage_property": "Mortgage a property you own.",
        "unmortgage_property": "Unmortgage a property you own.",
        "build_houses_or_hotel": "Build houses or a hotel on your monopolies.",
        "sell_houses_or_hotel": "Sell houses or a hotel from your monopolies.",
        "declare_bankruptcy": "Declare bankruptcy when you cannot pay.",
        "NOOP": "Take no action.",
    }
    return descriptions.get(action_name, f"Take the {action_name} action.")


def build_decision_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    decision_type = decision.get("decision_type")
    if decision_type == "BUY_OR_AUCTION_DECISION":
        return build_buy_or_auction_decision_focus(decision, space_key_by_index=space_key_by_index)
    # TODO: expand focus payloads when engine emits richer decision contexts.
    if decision_type == "JAIL_DECISION":
        return build_jail_decision_focus(decision, space_key_by_index=space_key_by_index)
    if decision_type == "POST_TURN_ACTION_DECISION":
        return build_post_turn_action_decision_focus(decision, space_key_by_index=space_key_by_index)
    if decision_type == "LIQUIDATION_DECISION":
        return build_liquidation_decision_focus(decision, space_key_by_index=space_key_by_index)
    if decision_type == "AUCTION_BID_DECISION":
        return build_auction_bid_decision_focus(decision, space_key_by_index=space_key_by_index)
    if decision_type == "TRADE_PROPOSE_DECISION":
        return build_trade_propose_decision_focus(decision)
    if decision_type == "TRADE_RESPONSE_DECISION":
        return build_trade_response_decision_focus(decision)
    if decision_type == "TRADE_RESPONSE":
        return build_trade_negotiation_focus(decision)
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "UNKNOWN_DECISION_FOCUS",
        "notes": [f"Unsupported decision_type: {decision_type}"],
    }


def _build_legal_tools(decision: dict[str, Any], *, include_args: bool) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for entry in decision.get("legal_actions", []):
        tool_name = entry.get("action")
        if not tool_name:
            continue
        tool: dict[str, Any] = {
            "tool_name": tool_name,
            "requires": ["public_message", "private_thought"],
        }
        if include_args:
            tool["args"] = {}
        tools.append(tool)
    return tools


def _rent_summary(space_kind: str | None, space_index: int) -> list[int]:
    if space_kind == "PROPERTY":
        return PROPERTY_RENT_TABLES.get(space_index, [])
    if space_kind == "RAILROAD":
        return list(RAILROAD_RENTS)
    if space_kind == "UTILITY":
        return [UTILITY_RENT_MULTIPLIER[key] for key in sorted(UTILITY_RENT_MULTIPLIER)]
    return []


def _group_progress(board: list[dict[str, Any]], player_id: str | None, group: str | None) -> dict[str, int]:
    if not group or not player_id:
        return {"you_own_in_group": 0, "total_in_group": 0}
    indices = GROUP_INDEXES.get(group, [])
    if not indices:
        return {"you_own_in_group": 0, "total_in_group": 0}
    board_by_index = {int(space.get("index", 0)): space for space in board}
    owned = sum(
        1 for index in indices if board_by_index.get(index, {}).get("owner_id") == player_id
    )
    return {"you_own_in_group": owned, "total_in_group": len(indices)}


def build_buy_or_auction_decision_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    state = decision.get("state", {})
    board = state.get("board", [])
    active_player_id = decision.get("player_id")
    active_player: dict[str, Any] = next(
        (player for player in state.get("players", []) if player.get("player_id") == active_player_id),
        {},
    )
    position_index = int(active_player.get("position", 0))
    landed_space = next((space for space in board if space.get("index") == position_index), None)
    if landed_space is None:
        landed_space = {"index": position_index}
    space_kind = landed_space.get("kind")
    raw_group = landed_space.get("group")
    group = str(raw_group) if raw_group is not None else None
    rent = _rent_summary(space_kind, position_index)
    house_cost = HOUSE_COST_BY_GROUP.get(group, 0) if space_kind == "PROPERTY" and group else 0
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": active_player_id,
        "scenario": {
            "landed_space": space_key_for_index(position_index, space_key_by_index),
            "space_kind": space_kind,
            "group": group,
            "price": landed_space.get("price"),
            "house_cost": house_cost,
            "rent": rent,
            "group_progress": _group_progress(board, active_player_id, group),
        },
        "legal_tools": _build_legal_tools(decision, include_args=True),
    }


def build_jail_decision_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    tool_names = {entry.get("action") for entry in decision.get("legal_actions", [])}
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": decision.get("player_id"),
        "scenario": {
            "jail_fine": JAIL_FINE,
            "options": {
                "can_pay_fine": "pay_jail_fine" in tool_names,
                "can_roll_for_doubles": "roll_for_doubles" in tool_names,
                "can_use_jail_card": "use_get_out_of_jail_card" in tool_names,
            },
            "notes": ["If you roll doubles, you immediately leave jail and move normally."],
        },
        "legal_tools": _build_legal_tools(decision, include_args=False),
    }


def _tool_requires(action_name: str) -> list[str]:
    if action_name == "propose_trade":
        return ["to_player_id", "offer", "request", "public_message", "private_thought"]
    if action_name == "counter_trade":
        return ["offer", "request", "public_message", "private_thought"]
    if action_name in {"accept_trade", "reject_trade"}:
        return ["public_message", "private_thought"]
    if action_name in {"mortgage_property", "unmortgage_property"}:
        return ["space_key", "public_message", "private_thought"]
    if action_name == "build_houses_or_hotel":
        return ["build_plan", "public_message", "private_thought"]
    if action_name == "sell_houses_or_hotel":
        return ["sell_plan", "public_message", "private_thought"]
    return ["public_message", "private_thought"]


def _lean_tool_entry(action_name: str, *, include_args: bool) -> dict[str, Any]:
    tool: dict[str, Any] = {
        "tool_name": action_name,
        "requires": _tool_requires(action_name),
    }
    if include_args:
        tool["args"] = {}
    return tool


def _build_post_turn_legal_tools(decision: dict[str, Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for entry in decision.get("legal_actions", []):
        action_name = entry.get("action")
        if not action_name:
            continue
        include_args = action_name in {"end_turn"}
        tools.append(_lean_tool_entry(action_name, include_args=include_args))
    return tools


def _build_liquidation_legal_tools(decision: dict[str, Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for entry in decision.get("legal_actions", []):
        action_name = entry.get("action")
        if not action_name:
            continue
        include_args = action_name in {"declare_bankruptcy"}
        tools.append(_lean_tool_entry(action_name, include_args=include_args))
    return tools


def _space_keys_for_indices(
    indices: list[int] | None,
    space_key_by_index: dict[int, str],
) -> list[str]:
    if not indices:
        return []
    return [space_key_for_index(int(index), space_key_by_index) for index in indices]


def build_post_turn_action_decision_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    post_turn = decision.get("post_turn", {})
    options = post_turn.get("options", {}) if isinstance(post_turn, dict) else {}
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": decision.get("player_id"),
        "scenario": {
            "note": "Choose ONE optional strategic action, or end your turn.",
            "options": {
                "can_trade_with": list(options.get("can_trade_with", [])),
                "mortgageable_space_keys": _space_keys_for_indices(
                    options.get("mortgageable_space_indices"),
                    space_key_by_index,
                ),
                "unmortgageable_space_keys": _space_keys_for_indices(
                    options.get("unmortgageable_space_indices"),
                    space_key_by_index,
                ),
                "buildable_space_keys": _space_keys_for_indices(
                    options.get("buildable_space_indices"),
                    space_key_by_index,
                ),
                "sellable_building_space_keys": _space_keys_for_indices(
                    options.get("sellable_building_space_indices"),
                    space_key_by_index,
                ),
            },
        },
        "legal_tools": _build_post_turn_legal_tools(decision),
    }


def build_liquidation_decision_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    liquidation = decision.get("liquidation", {})
    options = liquidation.get("options", {}) if isinstance(liquidation, dict) else {}
    scenario: dict[str, Any] = {
        "owed_amount": liquidation.get("owed_amount"),
        "reason": liquidation.get("reason"),
        "shortfall": liquidation.get("shortfall"),
        "options": {
            "mortgageable_space_keys": _space_keys_for_indices(
                options.get("mortgageable_space_indices"),
                space_key_by_index,
            ),
            "sellable_building_space_keys": _space_keys_for_indices(
                options.get("sellable_building_space_indices"),
                space_key_by_index,
            ),
        },
    }
    if liquidation.get("owed_to_player_id") is not None:
        scenario["owed_to_player_id"] = liquidation.get("owed_to_player_id")
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": decision.get("player_id"),
        "scenario": scenario,
        "legal_tools": _build_liquidation_legal_tools(decision),
    }


def build_auction_bid_decision_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    state = decision.get("state", {})
    auction = state.get("auction", {}) if isinstance(state, dict) else {}
    property_space_key = auction.get("property_space_key")
    group = None
    if property_space_key:
        space_index = SPACE_INDEX_BY_KEY.get(property_space_key)
        if space_index is not None:
            board = state.get("board", [])
            space = next((entry for entry in board if entry.get("index") == space_index), None)
            if space:
                group = space.get("group")
    current_high_bid = int(auction.get("current_high_bid", 0) or 0)
    min_next_bid = current_high_bid + 1
    active_bidders = list(auction.get("active_bidders_player_ids", []))
    leader_id = auction.get("current_leader_player_id")

    tools: list[dict[str, Any]] = []
    for entry in decision.get("legal_actions", []):
        action_name = entry.get("action")
        if action_name == "bid_auction":
            tools.append(
                {
                    "tool_name": "bid_auction",
                    "requires": ["bid_amount", "public_message", "private_thought"],
                }
            )
        elif action_name == "drop_out":
            tools.append(
                {
                    "tool_name": "drop_out",
                    "requires": ["public_message", "private_thought"],
                    "args": {},
                }
            )

    focus: dict[str, Any] = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": decision.get("player_id"),
        "scenario": {
            "property_space": property_space_key,
            "group": group,
            "current_high_bid": current_high_bid,
            "current_leader_player_id": leader_id,
            "min_next_bid": min_next_bid,
            "active_bidders_player_ids": active_bidders,
        },
        "legal_tools": tools,
    }
    return focus


def build_trade_propose_decision_focus(decision: dict[str, Any]) -> dict[str, Any]:
    state = decision.get("state", {})
    players = state.get("players", [])
    actor_id = decision.get("player_id")
    eligible = [
        player.get("player_id")
        for player in players
        if player.get("player_id") != actor_id and not player.get("bankrupt")
    ]
    tools: list[dict[str, Any]] = []
    for entry in decision.get("legal_actions", []):
        if entry.get("action") != "propose_trade":
            continue
        tools.append(
            {
                "tool_name": "propose_trade",
                "requires": ["to_player_id", "offer", "request", "public_message", "private_thought"],
            }
        )
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": actor_id,
        "scenario": {
            "max_exchanges": 5,
            "eligible_counterparties_player_ids": eligible,
        },
        "legal_tools": tools,
    }


def build_trade_response_decision_focus(decision: dict[str, Any]) -> dict[str, Any]:
    state = decision.get("state", {})
    trade = state.get("trade", {}) if isinstance(state, dict) else {}
    actor_id = decision.get("player_id")
    initiator = trade.get("initiator_player_id")
    counterparty = trade.get("counterparty_player_id")
    counterparty_id = (
        counterparty if actor_id == initiator else initiator if initiator else counterparty
    )
    history: list[dict[str, Any]] = []
    for entry in trade.get("history_last_2", []):
        if not isinstance(entry, dict):
            continue
        history.append(
            {
                "from_player_id": entry.get("from_player_id"),
                "offer": {},
                "request": {},
            }
        )
    current_offer: dict[str, dict[str, Any]] = {"offer": {}, "request": {}}
    tools: list[dict[str, Any]] = []
    for entry in decision.get("legal_actions", []):
        action_name = entry.get("action")
        if action_name == "accept_trade":
            tools.append(
                {
                    "tool_name": "accept_trade",
                    "requires": ["public_message", "private_thought"],
                    "args": {},
                }
            )
        elif action_name == "reject_trade":
            tools.append(
                {
                    "tool_name": "reject_trade",
                    "requires": ["public_message", "private_thought"],
                    "args": {},
                }
            )
        elif action_name == "counter_trade":
            tools.append(
                {
                    "tool_name": "counter_trade",
                    "requires": ["offer", "request", "public_message", "private_thought"],
                }
            )
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "decision_id": decision.get("decision_id"),
        "decision_type": decision.get("decision_type"),
        "actor_player_id": actor_id,
        "scenario": {
            "max_exchanges": trade.get("max_exchanges"),
            "exchange_index": trade.get("exchange_index"),
            "counterparty_player_id": counterparty_id,
            "history_last_2": history,
            "current_offer": current_offer,
        },
        "legal_tools": tools,
    }


def build_trade_negotiation_focus(decision: dict[str, Any]) -> dict[str, Any]:
    focus: dict[str, Any] = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "TRADE_NEGOTIATION_FOCUS",
    }
    trade = decision.get("trade", {})
    for field in ("counterparty_player_id", "offer_summary", "request_summary"):
        if field in trade:
            focus[field] = trade.get(field)
    return focus


def build_build_decision_focus(decision: dict[str, Any]) -> dict[str, Any]:
    focus: dict[str, Any] = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "BUILD_DECISION_FOCUS",
    }
    build = decision.get("build", {})
    if "buildable_space_keys" in build:
        focus["buildable_space_keys"] = build.get("buildable_space_keys")
    return focus


def build_mortgage_decision_focus(decision: dict[str, Any]) -> dict[str, Any]:
    focus: dict[str, Any] = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "MORTGAGE_DECISION_FOCUS",
    }
    mortgage = decision.get("mortgage", {})
    if "eligible_space_keys" in mortgage:
        focus["eligible_space_keys"] = mortgage.get("eligible_space_keys")
    return focus


def build_unmortgage_decision_focus(decision: dict[str, Any]) -> dict[str, Any]:
    focus: dict[str, Any] = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "UNMORTGAGE_DECISION_FOCUS",
    }
    unmortgage = decision.get("unmortgage", {})
    if "eligible_space_keys" in unmortgage:
        focus["eligible_space_keys"] = unmortgage.get("eligible_space_keys")
    return focus


def build_end_turn_focus(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "END_TURN_FOCUS",
    }


def build_prompt_bundle(
    decision: dict[str, Any],
    player: PlayerConfig,
    *,
    memory: PromptMemory,
    space_key_by_index: dict[int, str],
    retry_errors: list[str] | None = None,
) -> PromptBundle:
    system_prompt = build_system_prompt(player)
    state = decision.get("state", {})
    full_state = build_full_state(
        state,
        you_player_id=str(decision.get("player_id")),
        memory=memory,
        space_key_by_index=space_key_by_index,
    )
    compact_decision = build_compact_decision(decision)
    decision_focus = build_decision_focus(decision, space_key_by_index=space_key_by_index)
    if retry_errors:
        decision_focus = _with_retry_notes(decision_focus, retry_errors)
    payload = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "full_state": full_state,
        "decision": compact_decision,
        "decision_focus": decision_focus,
    }
    if player.reasoning is not None:
        payload["llm"] = {"reasoning": player.reasoning}
    user_content = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    return PromptBundle(
        system_prompt=system_prompt,
        user_payload=payload,
        user_content=user_content,
        messages=messages,
    )


def _with_retry_notes(decision_focus: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    focus = copy.deepcopy(decision_focus)
    target = focus.get("scenario")
    if isinstance(target, dict):
        notes = target.get("notes")
        if not isinstance(notes, list):
            notes = []
            target["notes"] = notes
    else:
        notes = focus.get("notes")
        if not isinstance(notes, list):
            notes = []
            focus["notes"] = notes
    notes.append(f"Previous validation errors: {', '.join(errors)}")
    notes.append("Respond with a valid tool call only. No freeform text.")
    return focus
