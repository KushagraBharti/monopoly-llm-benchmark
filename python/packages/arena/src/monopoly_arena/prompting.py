from __future__ import annotations

import copy
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from monopoly_engine.board import (
    BOARD_SPEC,
    GROUP_INDEXES,
    PROPERTY_RENT_TABLES,
    RAILROAD_RENTS,
    UTILITY_RENT_MULTIPLIER,
)

from .player_config import DEFAULT_SYSTEM_PROMPT, PlayerConfig


PROMPT_SCHEMA_VERSION = "v1"
JAIL_FINE = 50

HOUSE_COST_BY_GROUP = {
    "BROWN": 50,
    "LIGHT_BLUE": 50,
    "PINK": 100,
    "ORANGE": 100,
    "RED": 150,
    "YELLOW": 150,
    "GREEN": 200,
    "DARK_BLUE": 200,
}


def normalize_space_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    return cleaned.strip("_").upper()


def build_space_key_by_index() -> dict[int, str]:
    return {index: normalize_space_key(name) for index, _, name, _, _ in BOARD_SPEC}


SPACE_KEY_BY_INDEX = build_space_key_by_index()


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
        self._space_key_by_index = space_key_by_index or SPACE_KEY_BY_INDEX
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
    active_player_id = snapshot.get("active_player_id")
    if active_player_id and you_player_id and active_player_id != you_player_id:
        raise ValueError("Prompt player_id must match active_player_id.")
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
        "ROLL_DICE": "Roll the dice to start your move.",
        "roll_for_doubles": "Roll for doubles to attempt to leave jail.",
        "pay_jail_fine": "Pay the jail fine to leave jail.",
        "use_get_out_of_jail_card": "Use a Get Out of Jail Free card.",
        "END_TURN": "End your turn.",
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
    if decision_type == "AUCTION_BID":
        return build_auction_bid_focus(decision, space_key_by_index=space_key_by_index)
    if decision_type == "TRADE_RESPONSE":
        return build_trade_negotiation_focus(decision)
    if decision_type == "END_TURN":
        return build_end_turn_focus(decision)
    if decision_type == "BUILD_DECISION":
        return build_build_decision_focus(decision)
    if decision_type == "MORTGAGE_DECISION":
        return build_mortgage_decision_focus(decision)
    if decision_type == "UNMORTGAGE_DECISION":
        return build_unmortgage_decision_focus(decision)
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
    active_player = next(
        (player for player in state.get("players", []) if player.get("player_id") == active_player_id),
        {},
    )
    position_index = int(active_player.get("position", 0))
    landed_space = next((space for space in board if space.get("index") == position_index), None)
    if landed_space is None:
        landed_space = {"index": position_index}
    space_kind = landed_space.get("kind")
    group = landed_space.get("group")
    rent = _rent_summary(space_kind, position_index)
    house_cost = HOUSE_COST_BY_GROUP.get(group, 0) if space_kind == "PROPERTY" else 0
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


def build_auction_bid_focus(
    decision: dict[str, Any],
    *,
    space_key_by_index: dict[int, str],
) -> dict[str, Any]:
    auction = decision.get("auction", {})
    space_index = auction.get("space_index")
    focus: dict[str, Any] = {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "focus_type": "AUCTION_BID_DECISION_FOCUS",
    }
    if space_index is not None:
        focus["space_key"] = space_key_for_index(int(space_index), space_key_by_index)
        focus["space_index"] = space_index
    for field in ("current_bid", "min_bid_increment", "high_bidder_player_id"):
        if field in auction:
            focus[field] = auction.get(field)
    return focus


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
