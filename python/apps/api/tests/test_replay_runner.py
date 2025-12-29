import asyncio
import json
from typing import Any, Callable

from monopoly_arena import OpenRouterResult
from monopoly_engine import canonical_event_lines, load_jsonl, replay_actions
from monopoly_telemetry import init_run_files

from monopoly_api.llm_runner import LlmRunner
from monopoly_api.player_config import PlayerConfig, derive_model_display_name, DEFAULT_SYSTEM_PROMPT


def _make_player(player_id: str, name: str) -> PlayerConfig:
    model_id = "openai/gpt-oss-120b"
    return PlayerConfig(
        player_id=player_id,
        name=name,
        openrouter_model_id=model_id,
        model_display_name=derive_model_display_name(model_id),
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        reasoning=None,
    )


def _make_players() -> list[PlayerConfig]:
    return [
        _make_player("p1", "P1"),
        _make_player("p2", "P2"),
        _make_player("p3", "P3"),
        _make_player("p4", "P4"),
    ]


def _tool_call_response(name: str, args: dict[str, Any]) -> OpenRouterResult:
    payload = {
        "id": "resp-1",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args),
                            },
                        }
                    ],
                }
            }
        ],
    }
    return OpenRouterResult(
        ok=True,
        status_code=200,
        response_json=payload,
        error=None,
        error_type=None,
        request_id="req-1",
    )


def _extract_payload(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    for message in messages:
        if message.get("role") != "user":
            continue
        try:
            payload = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            continue
        if "decision" in payload and "full_state" in payload:
            return payload
    return None


class TradeOpenRouter:
    def __init__(
        self,
        policy: Callable[[dict[str, Any], dict[str, Any]], tuple[str, dict[str, Any]]],
    ) -> None:
        self._policy = policy

    async def create_chat_completion(self, *, messages: list[dict[str, Any]], **_: Any) -> OpenRouterResult:
        payload = _extract_payload(messages)
        if payload is None:
            return _tool_call_response("end_turn", {})
        decision = payload["decision"]
        focus = payload["decision_focus"]
        tool_name, args = self._policy(decision, focus)
        return _tool_call_response(tool_name, args)


def _policy(decision: dict[str, Any], focus: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    legal = {entry.get("action") for entry in decision.get("legal_actions", [])}
    decision_type = decision.get("decision_type")
    if decision_type == "POST_TURN_ACTION_DECISION" and "propose_trade" in legal:
        options = focus.get("scenario", {}).get("options", {})
        targets = options.get("can_trade_with", [])
        if targets:
            return "propose_trade", {
                "to_player_id": targets[0],
                "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
            }
    if decision_type == "TRADE_RESPONSE_DECISION":
        if "accept_trade" in legal:
            return "accept_trade", {}
        if "reject_trade" in legal:
            return "reject_trade", {}
    if "buy_property" in legal:
        return "buy_property", {}
    if "start_auction" in legal:
        return "start_auction", {}
    if "end_turn" in legal:
        return "end_turn", {}
    return next(iter(legal)), {}


def test_replay_matches_event_stream_with_trade(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-replay")
    runner = LlmRunner(
        seed=101,
        players=players,
        run_id="run-replay",
        openrouter=TradeOpenRouter(_policy),
        run_files=run_files,
        event_delay_s=0,
        max_turns=6,
        ts_step_ms=1,
    )
    asyncio.run(runner.run())

    events = load_jsonl(run_files.events_path)
    actions = load_jsonl(run_files.actions_path)
    assert actions
    assert any(event.get("type") == "TRADE_PROPOSED" for event in events)

    replayed = replay_actions(
        seed=101,
        players=[{"player_id": player.player_id, "name": player.name} for player in players],
        run_id="run-replay",
        actions=actions,
        max_turns=6,
        start_ts_ms=0,
        ts_step_ms=1,
    )

    assert canonical_event_lines(events) == canonical_event_lines(replayed)
