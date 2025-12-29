import asyncio
import json
from typing import Any, Callable

from monopoly_arena import OpenRouterResult
from monopoly_arena.prompting import (
    PromptMemory,
    build_openrouter_tools,
    build_prompt_bundle,
    build_space_key_by_index,
)
from monopoly_engine import Engine
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
            return _tool_call_response("start_auction", {})
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
            return _tool_call_response("start_auction", {})
        decision = payload["decision"]
        decision_focus = payload["decision_focus"]
        decision_id = decision["decision_id"]
        if decision.get("decision_type") != "BUY_OR_AUCTION_DECISION":
            tool_name, args = _choose_buy_if_legal(decision, decision_focus)
            return _tool_call_response(tool_name, args)
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
                return _tool_call_response("buy_property", {"space_index": 0})
            tool_name, args = _choose_buy_if_legal(decision, decision_focus)
            return _tool_call_response(tool_name, args)
        if decision_number == 2:
            return _tool_call_response("buy_property", {"space_index": 0})
        tool_name, args = _choose_buy_if_legal(decision, decision_focus)
        return _tool_call_response(tool_name, args)


class CaptureOpenRouter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create_chat_completion(self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> OpenRouterResult:
        self.calls.append({"model": model, "messages": messages, "kwargs": kwargs})
        payload = _extract_payload(messages)
        if payload is None:
            return _tool_call_response("start_auction", {})
        tool_name, args = _choose_buy_if_legal(payload["decision"], payload["decision_focus"])
        return _tool_call_response(tool_name, args)


def _choose_buy_if_legal(
    decision: dict[str, Any],
    decision_focus: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    legal = {entry.get("action") for entry in decision.get("legal_actions", [])}
    decision_type = decision.get("decision_type")
    if decision_type == "POST_TURN_ACTION_DECISION":
        if "end_turn" in legal:
            return "end_turn", {}
    if decision_type == "LIQUIDATION_DECISION":
        if "declare_bankruptcy" in legal:
            return "declare_bankruptcy", {}
        options = decision_focus.get("scenario", {}).get("options", {})
        mortgageable = options.get("mortgageable_space_keys", [])
        if "mortgage_property" in legal and mortgageable:
            return "mortgage_property", {"space_key": mortgageable[0]}
        sellable = options.get("sellable_building_space_keys", [])
        if "sell_houses_or_hotel" in legal and sellable:
            return "sell_houses_or_hotel", {
                "sell_plan": [{"space_key": sellable[0], "kind": "HOUSE", "count": 1}]
            }
    if "buy_property" in legal:
        return "buy_property", {}
    return "start_auction", {}


def test_retry_then_valid_action(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-retry")
    call_state = {"count": 0}

    def policy(decision: dict[str, Any], decision_focus: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if decision.get("decision_type") == "BUY_OR_AUCTION_DECISION":
            call_state["count"] += 1
            if call_state["count"] == 1:
                return "buy_property", {"space_index": 0}
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
    def policy(decision: dict[str, Any], decision_focus: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if decision.get("decision_type") == "BUY_OR_AUCTION_DECISION":
            return "buy_property", {"space_index": 0}
        return _choose_buy_if_legal(decision, decision_focus)

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
    started = next(
        entry
        for entry in entries
        if entry["phase"] == "decision_started"
        and entry.get("decision_type") == "BUY_OR_AUCTION_DECISION"
    )
    payload = started["prompt_payload"]
    raw_payload = started["prompt_payload_raw"]
    assert payload is not None
    assert raw_payload is not None
    assert json.loads(raw_payload) == payload
    assert set(payload.keys()) <= {"schema_version", "full_state", "decision", "decision_focus", "llm"}
    assert {"schema_version", "full_state", "decision", "decision_focus"}.issubset(payload.keys())

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
    assert focus["schema_version"] == "v1"
    assert focus["decision_type"] == "BUY_OR_AUCTION_DECISION"
    assert "jail_turns" not in json.dumps(focus)
    scenario = focus["scenario"]
    assert "landed_space" in scenario
    tools = focus["legal_tools"]
    tool_names = {tool["tool_name"] for tool in tools}
    assert {"buy_property", "start_auction"}.intersection(tool_names)
    for tool in tools:
        assert tool["args"] == {}


def test_jail_decision_focus_shape() -> None:
    players_state = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
        {"player_id": "p4", "name": "P4"},
    ]
    engine = Engine(seed=9, players=players_state, run_id="run-jail-shape", max_turns=3, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.in_jail = True
    player.position = 10
    player.jail_turns = 0

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "JAIL_DECISION"

    space_key_by_index = build_space_key_by_index()
    prompt = build_prompt_bundle(
        decision,
        _make_player("p1", "P1"),
        memory=PromptMemory(space_key_by_index=space_key_by_index),
        space_key_by_index=space_key_by_index,
    )
    focus = prompt.user_payload["decision_focus"]
    assert focus["decision_type"] == "JAIL_DECISION"
    assert "jail_turns" not in json.dumps(focus)
    options = focus["scenario"]["options"]
    assert isinstance(options["can_roll_for_doubles"], bool)
    tools = focus["legal_tools"]
    tool_names = {tool["tool_name"] for tool in tools}
    assert "roll_for_doubles" in tool_names
    for tool in tools:
        assert "args" not in tool


def test_post_turn_decision_focus_shape() -> None:
    players_state = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
        {"player_id": "p4", "name": "P4"},
    ]
    engine = Engine(seed=19, players=players_state, run_id="run-post-turn", max_turns=3, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    engine.state.board[1].owner_id = "p1"
    engine.state.board[3].owner_id = "p1"
    engine.state.board[1].houses = 1
    engine.state.board[5].owner_id = "p1"
    engine.state.board[12].owner_id = "p1"
    engine.state.board[12].mortgaged = True

    decision = engine._build_post_turn_action_decision(player)
    space_key_by_index = build_space_key_by_index()
    prompt = build_prompt_bundle(
        decision,
        _make_player("p1", "P1"),
        memory=PromptMemory(space_key_by_index=space_key_by_index),
        space_key_by_index=space_key_by_index,
    )
    focus = prompt.user_payload["decision_focus"]

    assert focus["decision_type"] == "POST_TURN_ACTION_DECISION"
    assert "cash" not in json.dumps(focus)
    assert "position" not in json.dumps(focus)
    assert "jail_turns" not in json.dumps(focus)
    options = focus["scenario"]["options"]
    assert isinstance(options["mortgageable_space_keys"], list)
    tools = focus["legal_tools"]
    tool_names = {tool["tool_name"] for tool in tools}
    assert "end_turn" in tool_names
    assert "propose_trade" not in tool_names
    for tool in tools:
        if tool["tool_name"] == "end_turn":
            assert tool["args"] == {}
        else:
            assert "args" not in tool

    build_tool = next(tool for tool in tools if tool["tool_name"] == "build_houses_or_hotel")
    assert "build_plan" in build_tool["requires"]
    sell_tool = next(tool for tool in tools if tool["tool_name"] == "sell_houses_or_hotel")
    assert "sell_plan" in sell_tool["requires"]
    mortgage_tool = next(tool for tool in tools if tool["tool_name"] == "mortgage_property")
    assert "space_key" in mortgage_tool["requires"]
    unmortgage_tool = next(tool for tool in tools if tool["tool_name"] == "unmortgage_property")
    assert "space_key" in unmortgage_tool["requires"]


def test_liquidation_decision_focus_shape() -> None:
    players_state = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
        {"player_id": "p4", "name": "P4"},
    ]
    engine = Engine(seed=21, players=players_state, run_id="run-liquidation-shape", max_turns=3, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.cash = 90
    engine.state.board[1].owner_id = "p1"
    engine.state.board[3].owner_id = "p1"
    engine.state.board[1].houses = 1
    engine.state.board[5].owner_id = "p1"

    payment = engine._build_payment_entry(340, "p2", "RENT", kind="RENT", space_index=14)
    options = engine._compute_liquidation_options(player)
    decision = engine._build_liquidation_decision(player, payment, options=options)

    space_key_by_index = build_space_key_by_index()
    prompt = build_prompt_bundle(
        decision,
        _make_player("p1", "P1"),
        memory=PromptMemory(space_key_by_index=space_key_by_index),
        space_key_by_index=space_key_by_index,
    )
    focus = prompt.user_payload["decision_focus"]

    assert focus["decision_type"] == "LIQUIDATION_DECISION"
    assert "cash" not in json.dumps(focus)
    assert "position" not in json.dumps(focus)
    assert "jail_turns" not in json.dumps(focus)
    scenario = focus["scenario"]
    assert scenario["owed_amount"] == 340
    assert scenario["owed_to_player_id"] == "p2"
    assert scenario["shortfall"] == 250
    tools = focus["legal_tools"]
    tool_names = {tool["tool_name"] for tool in tools}
    assert "declare_bankruptcy" in tool_names
    assert "mortgage_property" in tool_names
    assert "sell_houses_or_hotel" in tool_names
    for tool in tools:
        if tool["tool_name"] == "declare_bankruptcy":
            assert tool["args"] == {}
        else:
            assert "args" not in tool


def test_post_turn_tool_schema_includes_build_and_sell_plans() -> None:
    players_state = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
        {"player_id": "p4", "name": "P4"},
    ]
    engine = Engine(seed=29, players=players_state, run_id="run-post-turn-tools", max_turns=3, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    engine.state.board[1].owner_id = "p1"
    engine.state.board[3].owner_id = "p1"
    engine.state.board[1].houses = 1

    decision = engine._build_post_turn_action_decision(player)
    space_key_by_index = build_space_key_by_index()
    prompt = build_prompt_bundle(
        decision,
        _make_player("p1", "P1"),
        memory=PromptMemory(space_key_by_index=space_key_by_index),
        space_key_by_index=space_key_by_index,
    )
    tools = build_openrouter_tools(prompt.user_payload["decision"])

    build_tool = next(tool for tool in tools if tool["function"]["name"] == "build_houses_or_hotel")
    build_params = build_tool["function"]["parameters"]
    assert "build_plan" in build_params.get("properties", {})

    sell_tool = next(tool for tool in tools if tool["function"]["name"] == "sell_houses_or_hotel")
    sell_params = sell_tool["function"]["parameters"]
    assert "sell_plan" in sell_params.get("properties", {})

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


def test_reasoning_effort_and_free_model_propagate(tmp_path) -> None:
    players = _make_players()
    reasoning = {"effort": "high", "budget_tokens": 1200}
    players[0] = PlayerConfig(
        player_id="p1",
        name="P1",
        openrouter_model_id="openai/gpt-oss-120b:free",
        model_display_name=derive_model_display_name("openai/gpt-oss-120b:free"),
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        reasoning=reasoning,
    )
    run_files = init_run_files(tmp_path, "run-reasoning")
    openrouter = CaptureOpenRouter()
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-reasoning",
        openrouter=openrouter,
        run_files=run_files,
        event_delay_s=0,
        max_turns=20,
    )
    asyncio.run(runner.run())

    assert openrouter.calls
    matched_call = None
    for call in openrouter.calls:
        payload = _extract_payload(call["messages"])
        if payload and payload.get("decision", {}).get("player_id") == "p1":
            matched_call = call
            break
    assert matched_call is not None
    assert matched_call["model"] == "openai/gpt-oss-120b:free"
    assert matched_call["kwargs"].get("reasoning") == reasoning

    entries = [
        json.loads(line)
        for line in run_files.decisions_path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    decision_entry = next(
        entry
        for entry in entries
        if entry["phase"] == "decision_started" and entry["player_id"] == "p1"
    )
    decision_id = decision_entry["decision_id"]
    resolved = next(
        entry
        for entry in entries
        if entry["phase"] == "decision_resolved" and entry["player_id"] == "p1"
    )
    assert resolved["openrouter_model_id"] == "openai/gpt-oss-120b:free"
    assert resolved["model_display_name"] == "gpt-oss-120b:free"
    assert resolved["reasoning"] == reasoning

    prompt_payload = json.loads(
        (run_files.prompts_dir / f"decision_{decision_id}_user.json").read_text(encoding="utf-8")
    )
    assert prompt_payload["llm"]["reasoning"] == reasoning


def test_missing_reasoning_omits_openrouter_field(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-no-reasoning")
    openrouter = CaptureOpenRouter()
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-no-reasoning",
        openrouter=openrouter,
        run_files=run_files,
        event_delay_s=0,
        max_turns=2,
    )
    asyncio.run(runner.run())

    assert openrouter.calls
    first_call = openrouter.calls[0]
    assert "reasoning" not in first_call["kwargs"]


def test_request_stop_still_emits_game_ended(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-stopped")
    runner = LlmRunner(
        seed=123,
        players=players,
        run_id="run-stopped",
        openrouter=ScriptedOpenRouter(),
        run_files=run_files,
        event_delay_s=0,
        max_turns=4,
    )
    events: list[dict[str, Any]] = []

    async def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    runner.request_stop("STOPPED")
    asyncio.run(runner.run(on_event=on_event))

    game_end = next(event for event in events if event["type"] == "GAME_ENDED")
    assert game_end["payload"]["reason"] == "STOPPED"


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
        if entry.get("decision_type") != "BUY_OR_AUCTION_DECISION":
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
