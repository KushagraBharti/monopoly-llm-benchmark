import asyncio
import json
from typing import Any, Callable

from monopoly_arena import OpenRouterResult
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
    )


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


class PolicyOpenRouter:
    def __init__(self, policy: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]]) -> None:
        self._policy = policy

    async def create_chat_completion(self, *, messages: list[dict[str, Any]], **_: Any) -> OpenRouterResult:
        decision = None
        for message in messages:
            if message.get("role") != "user":
                continue
            try:
                payload = json.loads(message.get("content", "{}"))
            except json.JSONDecodeError:
                continue
            if "decision" in payload:
                decision = payload["decision"]
                break
        if decision is None:
            return _tool_call_response("start_auction", {"space_index": 0})
        tool_name, args = self._policy(decision)
        return _tool_call_response(tool_name, args)


def _choose_buy_if_legal(decision: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    legal = {entry.get("action") for entry in decision.get("legal_actions", [])}
    state = decision.get("state", {})
    active_player_id = state.get("active_player_id")
    position = 0
    for player in state.get("players", []):
        if player.get("player_id") == active_player_id:
            position = int(player.get("position", 0))
            break
    if "BUY_PROPERTY" in legal:
        return "buy_property", {"space_index": position}
    return "start_auction", {"space_index": position}


def test_retry_then_valid_action(tmp_path) -> None:
    players = [_make_player("p1", "P1"), _make_player("p2", "P2")]
    run_files = init_run_files(tmp_path, "run-retry")
    call_state = {"count": 0}

    def policy(decision: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        call_state["count"] += 1
        if call_state["count"] == 1:
            return "buy_property", {}
        return _choose_buy_if_legal(decision)

    fake = PolicyOpenRouter(policy)
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-retry",
        openrouter=fake,
        run_files=run_files,
        event_delay_s=0,
        max_turns=4,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    asyncio.run(runner.run(on_event=on_event))

    decisions_path = run_files.decisions_path
    lines = decisions_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    decision_entry = json.loads(lines[0])
    assert decision_entry["retry_used"] is True
    assert decision_entry["fallback_used"] is False
    assert len(decision_entry["attempts"]) == 2

    response_events = [event for event in events if event["type"] == "LLM_DECISION_RESPONSE"]
    assert response_events
    assert response_events[0]["payload"]["valid"] is True


def test_invalid_twice_fallback(tmp_path) -> None:
    players = [_make_player("p1", "P1"), _make_player("p2", "P2")]
    run_files = init_run_files(tmp_path, "run-fallback")
    def policy(_: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return "buy_property", {}

    fake = PolicyOpenRouter(policy)
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-fallback",
        openrouter=fake,
        run_files=run_files,
        event_delay_s=0,
        max_turns=4,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    asyncio.run(runner.run(on_event=on_event))

    decision_entry = json.loads(run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()[0])
    assert decision_entry["retry_used"] is True
    assert decision_entry["fallback_used"] is True
    assert decision_entry["fallback_reason"] == "invalid_tool_call"

    response_events = [event for event in events if event["type"] == "LLM_DECISION_RESPONSE"]
    assert response_events
    assert response_events[0]["payload"]["valid"] is False
    assert response_events[0]["payload"]["error"].startswith("fallback:")


def test_two_llms_deterministic_replay() -> None:
    players = [_make_player("p1", "P1"), _make_player("p2", "P2")]
    policy_client = PolicyOpenRouter(_choose_buy_if_legal)

    async def run_once() -> list[dict[str, Any]]:
        runner = LlmRunner(
            seed=2024,
            players=players,
            run_id="run-deterministic",
            openrouter=policy_client,
            event_delay_s=0,
            max_turns=20,
        )
        collected: list[dict[str, Any]] = []

        async def on_event(event: dict[str, Any]) -> None:
            collected.append(event)

        await runner.run(on_event=on_event)
        return collected

    events_a = asyncio.run(run_once())
    events_b = asyncio.run(run_once())
    assert events_a == events_b
