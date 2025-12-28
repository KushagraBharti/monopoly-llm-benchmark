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


def _error_response(error_type: str, status_code: int | None = None) -> OpenRouterResult:
    return OpenRouterResult(
        ok=False,
        status_code=status_code,
        response_json=None,
        error="error",
        error_type=error_type,
        request_id="req-err",
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


class PolicyOpenRouter:
    def __init__(
        self,
        policy: Callable[[dict[str, Any], dict[str, Any]], tuple[str, dict[str, Any]]],
    ) -> None:
        self._policy = policy

    async def create_chat_completion(self, *, messages: list[dict[str, Any]], **_: Any) -> OpenRouterResult:
        payload = _extract_payload(messages)
        if payload is None:
            return _tool_call_response("START_AUCTION", {"space_index": 0})
        tool_name, args = self._policy(payload["decision"], payload["decision_focus"])
        return _tool_call_response(tool_name, args)


class ErrorOpenRouter:
    def __init__(self, error_type: str, status_code: int | None = None) -> None:
        self._error_type = error_type
        self._status_code = status_code

    async def create_chat_completion(self, *_: Any, **__: Any) -> OpenRouterResult:
        return _error_response(self._error_type, self._status_code)


class ScriptedOpenRouter:
    def __init__(self) -> None:
        self._decision_index: dict[str, int] = {}
        self._decision_attempts: dict[str, int] = {}

    async def create_chat_completion(self, *, messages: list[dict[str, Any]], **_: Any) -> OpenRouterResult:
        payload = _extract_payload(messages)
        if payload is None:
            return _tool_call_response("START_AUCTION", {"space_index": 0})
        decision = payload["decision"]
        decision_focus = payload["decision_focus"]
        decision_id = decision["decision_id"]
        if decision_id not in self._decision_index:
            self._decision_index[decision_id] = len(self._decision_index)
            self._decision_attempts[decision_id] = 0
        attempt = self._decision_attempts[decision_id]
        self._decision_attempts[decision_id] = attempt + 1

        decision_number = self._decision_index[decision_id]
        if decision_number == 0:
            tool_name, args = _choose_buy_if_legal(decision, decision_focus)
            return _tool_call_response(tool_name, args)
        if decision_number == 1:
            if attempt == 0:
                return _tool_call_response("BUY_PROPERTY", {})
            tool_name, args = _choose_buy_if_legal(decision, decision_focus)
            return _tool_call_response(tool_name, args)
        if decision_number == 2:
            return _tool_call_response("BUY_PROPERTY", {})
        tool_name, args = _choose_buy_if_legal(decision, decision_focus)
        return _tool_call_response(tool_name, args)


def _choose_buy_if_legal(
    decision: dict[str, Any],
    decision_focus: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    legal = {entry.get("action") for entry in decision.get("legal_actions", [])}
    landed_space = decision_focus.get("landed_space", {})
    position = int(landed_space.get("space_index", 0))
    if "BUY_PROPERTY" in legal:
        return "BUY_PROPERTY", {"space_index": position}
    return "START_AUCTION", {"space_index": position}


def test_retry_then_valid_action(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-retry")
    call_state = {"count": 0}

    def policy(decision: dict[str, Any], decision_focus: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        call_state["count"] += 1
        if call_state["count"] == 1:
            return "BUY_PROPERTY", {}
        return _choose_buy_if_legal(decision, decision_focus)

    fake = PolicyOpenRouter(policy)
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-retry",
        openrouter=fake,
        run_files=run_files,
        event_delay_s=0,
        max_turns=8,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    asyncio.run(runner.run(on_event=on_event))

    decisions_path = run_files.decisions_path
    lines = decisions_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    entries = [json.loads(line) for line in lines if line.strip()]
    decision_id = entries[0]["decision_id"]
    decision_entries = [entry for entry in entries if entry["decision_id"] == decision_id]
    started = next(entry for entry in decision_entries if entry["phase"] == "decision_started")
    resolved = next(entry for entry in decision_entries if entry["phase"] == "decision_resolved")
    assert started["request_start_ms"] is not None
    assert resolved["retry_used"] is True
    assert resolved["fallback_used"] is False
    assert len(resolved["attempts"]) == 2
    assert resolved["request_start_ms"] is not None
    assert resolved["response_end_ms"] is not None
    assert resolved["latency_ms"] is not None
    assert resolved["applied"] is True
    assert "LLM_DECISION_RESPONSE" in resolved["emitted_event_types"]
    assert resolved["emitted_event_seq_start"] <= resolved["emitted_event_seq_end"]

    response_events = [event for event in events if event["type"] == "LLM_DECISION_RESPONSE"]
    assert response_events
    assert response_events[0]["payload"]["valid"] is True


def test_invalid_twice_fallback(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-fallback")
    def policy(_: dict[str, Any], __: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return "BUY_PROPERTY", {}

    fake = PolicyOpenRouter(policy)
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-fallback",
        openrouter=fake,
        run_files=run_files,
        event_delay_s=0,
        max_turns=8,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    asyncio.run(runner.run(on_event=on_event))

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    decision_id = entries[0]["decision_id"]
    resolved = next(entry for entry in entries if entry["decision_id"] == decision_id and entry["phase"] == "decision_resolved")
    assert resolved["retry_used"] is True
    assert resolved["fallback_used"] is True
    assert resolved["fallback_reason"] == "invalid_action"
    assert resolved["applied"] is True
    assert "LLM_DECISION_RESPONSE" in resolved["emitted_event_types"]

    response_events = [event for event in events if event["type"] == "LLM_DECISION_RESPONSE"]
    assert response_events
    assert response_events[0]["payload"]["valid"] is False
    assert response_events[0]["payload"]["error"].startswith("fallback:")


def test_prompt_payload_shape(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-prompt")
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-prompt",
        openrouter=PolicyOpenRouter(_choose_buy_if_legal),
        run_files=run_files,
        event_delay_s=0,
        max_turns=6,
    )
    asyncio.run(runner.run())

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    started = next(entry for entry in entries if entry["phase"] == "decision_started")
    payload = started["prompt_payload"]
    raw_payload = started["prompt_payload_raw"]
    assert payload is not None
    assert raw_payload is not None
    assert json.loads(raw_payload) == payload
    assert set(payload.keys()) == {"schema_version", "full_state", "decision", "decision_focus"}

    full_state = payload["full_state"]
    assert "board" not in full_state
    assert "space_name" not in json.dumps(full_state)
    assert len(full_state["others"]) == 3
    assert isinstance(full_state["you"]["position"], str)
    for player in [full_state["you"], *full_state["others"]]:
        for holding in player["holdings"]["owned"]:
            assert "space_key" in holding
            assert "name" not in holding

    decision = payload["decision"]
    assert "state" not in decision
    assert "run_id" not in decision

    focus = payload["decision_focus"]
    assert focus["focus_type"] == "BUY_DECISION_FOCUS"
    assert "landed_space" in focus
    assert "can_afford" in focus


def test_two_llms_deterministic_replay() -> None:
    players = _make_players()
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


def test_openrouter_http_429_fallback_reason(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-http-429")
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-http-429",
        openrouter=ErrorOpenRouter("http_429", 429),
        run_files=run_files,
        event_delay_s=0,
        max_turns=8,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    asyncio.run(runner.run(on_event=on_event))

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    resolved = next(entry for entry in entries if entry["phase"] == "decision_resolved")
    assert resolved["fallback_reason"] == "openrouter_http_429"

    response_events = [event for event in events if event["type"] == "LLM_DECISION_RESPONSE"]
    assert response_events
    assert response_events[0]["payload"]["error"] == "fallback:openrouter_http_429"


def test_openrouter_http_5xx_fallback_reason(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-http-5xx")
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-http-5xx",
        openrouter=ErrorOpenRouter("http_5xx", 503),
        run_files=run_files,
        event_delay_s=0,
        max_turns=8,
    )
    asyncio.run(runner.run())

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    resolved = next(entry for entry in entries if entry["phase"] == "decision_resolved")
    assert resolved["fallback_reason"] == "openrouter_http_5xx"


def test_openrouter_http_4xx_fallback_reason(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-http-4xx")
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-http-4xx",
        openrouter=ErrorOpenRouter("http_4xx", 401),
        run_files=run_files,
        event_delay_s=0,
        max_turns=8,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    asyncio.run(runner.run(on_event=on_event))

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    resolved = next(entry for entry in entries if entry["phase"] == "decision_resolved")
    assert resolved["fallback_used"] is True
    assert resolved["fallback_reason"] == "openrouter_http_4xx"

    response_events = [event for event in events if event["type"] == "LLM_DECISION_RESPONSE"]
    assert response_events
    assert response_events[0]["payload"]["valid"] is False
    assert response_events[0]["payload"]["error"].startswith("fallback:")


def test_openrouter_network_error_fallback_reason(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-network-error")
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-network-error",
        openrouter=ErrorOpenRouter("network_error"),
        run_files=run_files,
        event_delay_s=0,
        max_turns=8,
    )
    asyncio.run(runner.run())

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    resolved = next(entry for entry in entries if entry["phase"] == "decision_resolved")
    assert resolved["fallback_reason"] == "openrouter_network_error"


def test_decisions_jsonl_pairs_and_applied(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-sample")
    runner = LlmRunner(
        seed=2024,
        players=players,
        run_id="run-sample",
        openrouter=ScriptedOpenRouter(),
        run_files=run_files,
        event_delay_s=0,
        max_turns=40,
    )
    asyncio.run(runner.run())

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    decision_order: list[str] = []
    for entry in entries:
        if entry["phase"] != "decision_started":
            continue
        decision_id = entry["decision_id"]
        if decision_id not in decision_order:
            decision_order.append(decision_id)
    assert len(decision_order) >= 3

    resolved_by_id = {
        entry["decision_id"]: entry
        for entry in entries
        if entry["phase"] == "decision_resolved"
    }
    for decision_id in decision_order[:3]:
        started = next(
            entry for entry in entries if entry["decision_id"] == decision_id and entry["phase"] == "decision_started"
        )
        resolved = resolved_by_id[decision_id]
        assert started["decision_id"] == resolved["decision_id"]
        assert resolved["applied"] is True
        assert "LLM_DECISION_RESPONSE" in resolved["emitted_event_types"]

    first_id, second_id, third_id = decision_order[:3]
    assert resolved_by_id[first_id]["retry_used"] is False
    assert resolved_by_id[first_id]["fallback_used"] is False
    assert resolved_by_id[second_id]["retry_used"] is True
    assert resolved_by_id[second_id]["fallback_used"] is False
    assert resolved_by_id[third_id]["retry_used"] is True
    assert resolved_by_id[third_id]["fallback_used"] is True
