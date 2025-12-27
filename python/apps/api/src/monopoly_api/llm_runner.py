from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterable, Awaitable, Callable

from monopoly_engine import Engine
from monopoly_engine.board import (
    PROPERTY_RENT_TABLES,
    RAILROAD_RENTS,
    UTILITY_RENT_MULTIPLIER,
)
from monopoly_telemetry import RunFiles

from monopoly_arena import OpenRouterClient, OpenRouterResult

from .action_validation import validate_action_payload
from .player_config import PlayerConfig


DecisionCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class DecisionAttempt:
    prompt_messages: list[dict[str, Any]]
    raw_response: dict[str, Any] | None
    assistant_content: str | None
    parsed_tool_call: dict[str, Any] | None
    validation_errors: list[str]
    openrouter_request_id: str | None
    error_type: str | None
    error_message: str | None


@dataclass(slots=True)
class DecisionOutcome:
    action: dict[str, Any]
    decision_meta: dict[str, Any]
    log_entry: dict[str, Any]


class LlmRunner:
    def __init__(
        self,
        *,
        seed: int,
        players: list[PlayerConfig],
        run_id: str,
        openrouter: OpenRouterClient,
        run_files: RunFiles | None = None,
        max_turns: int = 200,
        event_delay_s: float = 0.25,
        start_ts_ms: int = 0,
        ts_step_ms: int = 250,
    ) -> None:
        self.run_id = run_id
        self._player_configs = {player.player_id: player for player in players}
        self._openrouter = openrouter
        self._run_files = run_files
        self._engine = Engine(
            seed=seed,
            players=[{"player_id": p.player_id, "name": p.name} for p in players],
            run_id=run_id,
            max_turns=max_turns,
            start_ts_ms=start_ts_ms,
            ts_step_ms=ts_step_ms,
        )
        self._event_delay_s = event_delay_s

    def request_stop(self, reason: str = "STOPPED") -> None:
        self._engine.request_stop(reason)

    def get_snapshot(self) -> dict[str, Any]:
        return self._engine.get_snapshot()

    async def run(
        self,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_snapshot: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_summary: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_decision: DecisionCallback | None = None,
    ) -> None:
        async for event in self._event_stream(on_decision=on_decision):
            if on_event is not None:
                await on_event(event)
            if on_snapshot is not None and event["type"] in {"TURN_ENDED", "GAME_ENDED"}:
                await on_snapshot(self.get_snapshot())
            if self._event_delay_s > 0:
                await asyncio.sleep(self._event_delay_s)
        if on_summary is not None:
            await on_summary(self._engine.build_summary())

    async def _event_stream(
        self,
        on_decision: DecisionCallback | None = None,
    ) -> AsyncIterable[dict[str, Any]]:
        while True:
            _, events, decision, _ = self._engine.advance_until_decision(max_steps=1)
            if not events:
                break
            for event in events:
                yield event
            if decision is not None:
                outcome = await self._resolve_decision(decision)
                _, action_events, _, _ = self._engine.apply_action(
                    outcome.action,
                    decision_meta=outcome.decision_meta,
                )
                for event in action_events:
                    yield event
                if on_decision is not None:
                    await on_decision(outcome.log_entry)
                elif self._run_files is not None:
                    self._run_files.write_decision(outcome.log_entry)
                if self._engine.is_game_over():
                    break
                continue
            if self._engine.is_game_over():
                break

    async def _resolve_decision(self, decision: dict[str, Any]) -> DecisionOutcome:
        player_id = decision["player_id"]
        player_config = self._player_configs[player_id]
        attempts: list[DecisionAttempt] = []

        if decision.get("decision_type") != "BUY_DECISION":
            action = self._fallback_action(decision)
            return self._build_decision_outcome(
                decision=decision,
                player_config=player_config,
                action=action,
                attempts=attempts,
                retry_used=False,
                fallback_used=True,
                fallback_reason="unsupported_decision_type",
            )

        tools = build_buy_tools()
        prompt = build_prompt(decision, player_config)
        result = await self._openrouter.create_chat_completion(
            model=player_config.openrouter_model_id,
            messages=prompt,
            tools=tools,
            tool_choice="required",
        )
        attempt = self._attempt_from_response(prompt, result)
        attempts.append(attempt)
        if not result.ok:
            fallback_reason = "no_api_key" if result.error_type == "no_api_key" else "openrouter_error"
            fallback = self._fallback_action(decision)
            return self._build_decision_outcome(
                decision=decision,
                player_config=player_config,
                action=fallback,
                attempts=attempts,
                retry_used=False,
                fallback_used=True,
                fallback_reason=fallback_reason,
            )
        action, errors = self._build_action_from_attempt(decision, attempt)
        if errors:
            retry_prompt = build_retry_prompt(decision, player_config, errors)
            retry_result = await self._openrouter.create_chat_completion(
                model=player_config.openrouter_model_id,
                messages=retry_prompt,
                tools=tools,
                tool_choice="required",
            )
            retry_attempt = self._attempt_from_response(retry_prompt, retry_result)
            attempts.append(retry_attempt)
            action, errors = self._build_action_from_attempt(decision, retry_attempt)
            if errors:
                fallback = self._fallback_action(decision)
                return self._build_decision_outcome(
                    decision=decision,
                    player_config=player_config,
                    action=fallback,
                    attempts=attempts,
                    retry_used=True,
                    fallback_used=True,
                    fallback_reason="invalid_tool_call",
                )
            return self._build_decision_outcome(
                decision=decision,
                player_config=player_config,
                action=action,
                attempts=attempts,
                retry_used=True,
                fallback_used=False,
                fallback_reason=None,
            )
        return self._build_decision_outcome(
            decision=decision,
            player_config=player_config,
            action=action,
            attempts=attempts,
            retry_used=False,
            fallback_used=False,
            fallback_reason=None,
        )

    def _attempt_from_response(
        self,
        prompt: list[dict[str, Any]],
        result: OpenRouterResult,
    ) -> DecisionAttempt:
        response_json = result.response_json if result.ok else None
        assistant_content = None
        tool_call = None
        errors: list[str] = []
        if response_json is None:
            errors.append(result.error or "OpenRouter error")
        else:
            assistant_content = (
                response_json.get("choices", [{}])[0].get("message", {}).get("content")
            )
            tool_call, parse_error = parse_tool_call(response_json)
            if parse_error:
                errors.append(parse_error)
        return DecisionAttempt(
            prompt_messages=prompt,
            raw_response=response_json,
            assistant_content=assistant_content,
            parsed_tool_call=tool_call,
            validation_errors=errors,
            openrouter_request_id=result.request_id,
            error_type=result.error_type,
            error_message=result.error,
        )

    def _build_action_from_attempt(
        self,
        decision: dict[str, Any],
        attempt: DecisionAttempt,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        if attempt.parsed_tool_call is None:
            return None, attempt.validation_errors or ["Missing tool call"]
        action = tool_call_to_action(decision, attempt.parsed_tool_call)
        if action is None:
            return None, ["Unable to map tool call to action"]
        errors = validate_decision_action(decision, action)
        return action, errors

    def _build_decision_outcome(
        self,
        *,
        decision: dict[str, Any],
        player_config: PlayerConfig,
        action: dict[str, Any],
        attempts: list[DecisionAttempt],
        retry_used: bool,
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> DecisionOutcome:
        decision_meta: dict[str, Any] = {"valid": True, "error": None}
        if fallback_used:
            decision_meta = {
                "valid": False,
                "error": f"fallback:{fallback_reason}",
            }
        log_entry = {
            "run_id": decision["run_id"],
            "turn_index": decision["turn_index"],
            "decision_id": decision["decision_id"],
            "decision_type": decision["decision_type"],
            "player_id": decision["player_id"],
            "player_name": player_config.name,
            "openrouter_model_id": player_config.openrouter_model_id,
            "model_display_name": player_config.model_display_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempts": [
                {
                    "prompt_messages": attempt.prompt_messages,
                    "raw_response": attempt.raw_response,
                    "assistant_content": attempt.assistant_content,
                    "parsed_tool_call": attempt.parsed_tool_call,
                    "validation_errors": attempt.validation_errors,
                    "openrouter_request_id": attempt.openrouter_request_id,
                    "error_type": attempt.error_type,
                    "error_message": attempt.error_message,
                }
                for attempt in attempts
            ],
            "retry_used": retry_used,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "final_action": action,
        }
        if fallback_used:
            log_entry["fallback_action"] = action
        return DecisionOutcome(action=action, decision_meta=decision_meta, log_entry=log_entry)

    @staticmethod
    def _fallback_action(decision: dict[str, Any]) -> dict[str, Any]:
        legal_actions = [entry["action"] for entry in decision.get("legal_actions", [])]
        if "BUY_PROPERTY" in legal_actions:
            action_name = "BUY_PROPERTY"
        elif "START_AUCTION" in legal_actions:
            action_name = "START_AUCTION"
        elif legal_actions:
            action_name = legal_actions[0]
        else:
            action_name = "NOOP"

        args: dict[str, Any] = {}
        if action_name in {"BUY_PROPERTY", "START_AUCTION", "DECLINE_PROPERTY"}:
            state = decision.get("state", {})
            active_player_id = state.get("active_player_id")
            space_index = 0
            for player in state.get("players", []):
                if player.get("player_id") == active_player_id:
                    space_index = int(player.get("position", 0))
                    break
            args = {"space_index": space_index}
        elif action_name == "NOOP":
            args = {"reason": "fallback"}

        return {
            "schema_version": "v1",
            "decision_id": decision["decision_id"],
            "action": action_name,
            "args": args,
        }


def build_buy_tools() -> list[dict[str, Any]]:
    parameters = {
        "type": "object",
        "additionalProperties": False,
        "required": ["space_index"],
        "properties": {
            "space_index": {"type": "integer", "minimum": 0, "maximum": 39},
            "public_message": {"type": "string"},
            "private_thought": {"type": "string"},
        },
    }
    return [
        {
            "type": "function",
            "function": {
                "name": "buy_property",
                "description": "Buy the property at the current space.",
                "parameters": parameters,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "start_auction",
                "description": "Decline purchase and start an auction for the current space.",
                "parameters": parameters,
            },
        },
    ]


def build_prompt(decision: dict[str, Any], player: PlayerConfig) -> list[dict[str, Any]]:
    summary = build_summary(decision)
    rules = [
        "Choose exactly one legal action using a tool call.",
        "Only BUY_PROPERTY or START_AUCTION are allowed for BUY_DECISION.",
        "BUY_PROPERTY is legal only if you can afford the price.",
        "If unsure or unaffordable, choose START_AUCTION.",
    ]
    payload = {
        "decision": decision,
        "state_snapshot": decision.get("state", {}),
        "summary": summary,
        "rules": rules,
    }
    return [
        {
            "role": "system",
            "content": player.system_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
        },
    ]


def build_retry_prompt(
    decision: dict[str, Any],
    player: PlayerConfig,
    errors: list[str],
) -> list[dict[str, Any]]:
    base_prompt = build_prompt(decision, player)
    correction = {
        "validation_errors": errors,
        "legal_actions": decision.get("legal_actions", []),
        "instruction": "Respond with a valid tool call only. No freeform text.",
    }
    base_prompt.append(
        {
            "role": "user",
            "content": json.dumps(correction, ensure_ascii=True, separators=(",", ":")),
        }
    )
    return base_prompt


def parse_tool_call(response_json: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    choices = response_json.get("choices", [])
    if not choices:
        return None, "No choices in response"
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        call = tool_calls[0]
        func = call.get("function", {})
        return {
            "name": func.get("name"),
            "arguments": func.get("arguments"),
        }, None
    function_call = message.get("function_call")
    if function_call:
        return {
            "name": function_call.get("name"),
            "arguments": function_call.get("arguments"),
        }, None
    return None, "No tool call found"


def tool_call_to_action(decision: dict[str, Any], tool_call: dict[str, Any]) -> dict[str, Any] | None:
    tool_name = tool_call.get("name")
    if tool_name == "buy_property":
        action_name = "BUY_PROPERTY"
    elif tool_name == "start_auction":
        action_name = "START_AUCTION"
    else:
        return None

    arguments = tool_call.get("arguments")
    if isinstance(arguments, str):
        try:
            args_payload = json.loads(arguments)
        except json.JSONDecodeError:
            return None
    elif isinstance(arguments, dict):
        args_payload = arguments
    else:
        args_payload = {}

    args: dict[str, Any] = {}
    if "space_index" in args_payload:
        args["space_index"] = args_payload.get("space_index")
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": action_name,
        "args": args,
    }
    public_message = args_payload.get("public_message")
    private_thought = args_payload.get("private_thought")
    if isinstance(public_message, str):
        action["public_message"] = public_message
    if isinstance(private_thought, str):
        action["private_thought"] = private_thought
    return action


def validate_decision_action(decision: dict[str, Any], action: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_errors = validate_action_payload(action)
    if not schema_ok:
        errors.extend(schema_errors)

    legal_actions = decision.get("legal_actions", [])
    allowed = {entry.get("action") for entry in legal_actions}
    if action.get("action") not in allowed:
        errors.append("Action not in legal_actions")

    if decision.get("decision_type") == "BUY_DECISION":
        state = decision.get("state", {})
        active_player_id = state.get("active_player_id")
        active_player = next(
            (player for player in state.get("players", []) if player.get("player_id") == active_player_id),
            None,
        )
        if active_player is None:
            errors.append("Missing active player in state snapshot")
        else:
            expected_index = int(active_player.get("position", 0))
            actual_index = action.get("args", {}).get("space_index")
            if actual_index != expected_index:
                errors.append("space_index does not match current player position")

    return errors


def build_summary(decision: dict[str, Any]) -> dict[str, Any]:
    state = decision.get("state", {})
    board = state.get("board", [])
    active_player_id = state.get("active_player_id")
    players = state.get("players", [])
    active_player = next(
        (player for player in players if player.get("player_id") == active_player_id),
        {},
    )

    group_to_spaces: dict[str, list[dict[str, Any]]] = {}
    for space in board:
        group = space.get("group")
        if not group:
            continue
        group_to_spaces.setdefault(group, []).append(space)

    monopolies_by_player: dict[str, list[str]] = {}
    for group, spaces in group_to_spaces.items():
        owners = {space.get("owner_id") for space in spaces}
        if len(owners) == 1:
            owner = next(iter(owners))
            if owner:
                monopolies_by_player.setdefault(owner, []).append(group)

    owned_by_player: dict[str, list[dict[str, Any]]] = {p.get("player_id"): [] for p in players}
    for space in board:
        owner_id = space.get("owner_id")
        if owner_id:
            owned_by_player.setdefault(owner_id, []).append(space)

    railroad_counts = _count_group_by_owner(board, "RAILROAD")
    utility_counts = _count_group_by_owner(board, "UTILITY")

    offer_space = None
    if active_player:
        pos = int(active_player.get("position", 0))
        offer_space = next((space for space in board if space.get("index") == pos), None)

    offer_summary = _build_offer_summary(
        offer_space, active_player, monopolies_by_player, board, railroad_counts, utility_counts
    )

    opponents = []
    for player in players:
        if player.get("player_id") == active_player_id:
            continue
        opponent_id = player.get("player_id")
        opponent_spaces = owned_by_player.get(opponent_id, [])
        opponents.append(
            {
                "player_id": opponent_id,
                "cash": player.get("cash"),
                "property_count": len(opponent_spaces),
                "monopolies": monopolies_by_player.get(opponent_id, []),
                "railroads_owned": railroad_counts.get(opponent_id, 0),
                "utilities_owned": utility_counts.get(opponent_id, 0),
            }
        )

    rent_stats = _rent_exposure(board, monopolies_by_player, railroad_counts, utility_counts, active_player_id)

    return {
        "active_player": {
            "player_id": active_player_id,
            "cash": active_player.get("cash"),
            "position": active_player.get("position"),
            "owned_properties": [
                {
                    "index": space.get("index"),
                    "name": space.get("name"),
                    "group": space.get("group"),
                    "mortgaged": space.get("mortgaged"),
                }
                for space in owned_by_player.get(active_player_id, [])
            ],
            "monopolies": monopolies_by_player.get(active_player_id, []),
        },
        "opponents": opponents,
        "offer": offer_summary,
        "rent_exposure": rent_stats,
    }


def _count_group_by_owner(board: list[dict[str, Any]], group_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for space in board:
        if space.get("group") != group_name:
            continue
        owner_id = space.get("owner_id")
        if owner_id:
            counts[owner_id] = counts.get(owner_id, 0) + 1
    return counts


def _rent_exposure(
    board: list[dict[str, Any]],
    monopolies_by_player: dict[str, list[str]],
    railroad_counts: dict[str, int],
    utility_counts: dict[str, int],
    active_player_id: str | None,
) -> dict[str, Any]:
    rents: list[int] = []
    for space in board:
        owner_id = space.get("owner_id")
        if not owner_id or owner_id == active_player_id:
            continue
        rent = _estimate_rent(
            space,
            owner_id,
            monopolies_by_player,
            railroad_counts,
            utility_counts,
        )
        if rent > 0:
            rents.append(rent)
    if not rents:
        return {"max_rent": 0, "avg_rent": 0}
    return {
        "max_rent": max(rents),
        "avg_rent": int(sum(rents) / len(rents)),
    }


def _estimate_rent(
    space: dict[str, Any],
    owner_id: str,
    monopolies_by_player: dict[str, list[str]],
    railroad_counts: dict[str, int],
    utility_counts: dict[str, int],
) -> int:
    kind = space.get("kind")
    if kind == "RAILROAD":
        owned = railroad_counts.get(owner_id, 0)
        if owned <= 0:
            return 0
        return RAILROAD_RENTS[min(owned, 4) - 1]
    if kind == "UTILITY":
        owned = utility_counts.get(owner_id, 0)
        multiplier = UTILITY_RENT_MULTIPLIER.get(owned, 4)
        return 7 * multiplier
    if kind == "PROPERTY":
        rent_table = PROPERTY_RENT_TABLES.get(space.get("index"))
        if not rent_table:
            return 0
        if space.get("hotel"):
            return rent_table[5]
        houses = int(space.get("houses", 0))
        if houses > 0:
            return rent_table[min(houses, 4)]
        base_rent = rent_table[0]
        group = space.get("group")
        if group and group in monopolies_by_player.get(owner_id, []):
            base_rent *= 2
        return base_rent
    return 0


def _build_offer_summary(
    space: dict[str, Any] | None,
    active_player: dict[str, Any],
    monopolies_by_player: dict[str, list[str]],
    board: list[dict[str, Any]],
    railroad_counts: dict[str, int],
    utility_counts: dict[str, int],
) -> dict[str, Any]:
    if not space:
        return {}
    price = space.get("price")
    group = space.get("group")
    active_id = active_player.get("player_id")
    cash = active_player.get("cash")
    completes_monopoly = False
    if group:
        group_spaces = [s for s in board if s.get("group") == group]
        owned = [s for s in group_spaces if s.get("owner_id") == active_id]
        completes_monopoly = len(owned) == len(group_spaces) - 1

    base_rent = _estimate_rent(
        space,
        active_id,
        monopolies_by_player,
        railroad_counts,
        utility_counts,
    )

    return {
        "space_index": space.get("index"),
        "name": space.get("name"),
        "kind": space.get("kind"),
        "group": group,
        "price": price,
        "base_rent": base_rent,
        "can_afford": price is not None and cash is not None and cash >= price,
        "cash_after_purchase": cash - price if price is not None and cash is not None else None,
        "completes_monopoly": completes_monopoly,
    }
