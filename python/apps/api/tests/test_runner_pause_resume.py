import asyncio
import json
from typing import Any

from monopoly_arena import OpenRouterResult
from monopoly_api.llm_runner import LlmRunner
from monopoly_api.player_config import DEFAULT_SYSTEM_PROMPT, PlayerConfig, derive_model_display_name
from monopoly_telemetry import init_run_files


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


class ImmediateOpenRouter:
    async def create_chat_completion(self, *_: Any, **__: Any) -> OpenRouterResult:
        return _tool_call_response("buy_property", {})


class DelayedOpenRouter:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.allow_response = asyncio.Event()

    async def create_chat_completion(self, *_: Any, **__: Any) -> OpenRouterResult:
        self.started.set()
        await self.allow_response.wait()
        return _tool_call_response("buy_property", {})


def test_pause_blocks_event_advancement_until_resume(tmp_path) -> None:
    async def run_case() -> None:
        players = _make_players()
        run_files = init_run_files(tmp_path, "run-pause-block")
        runner = LlmRunner(
            seed=123,
            players=players,
            run_id="run-pause-block",
            openrouter=ImmediateOpenRouter(),
            run_files=run_files,
            event_delay_s=0,
            max_turns=6,
        )
        events: list[dict[str, Any]] = []
        paused = asyncio.Event()

        async def on_event(event: dict[str, Any]) -> None:
            events.append(event)
            if event["type"] == "LLM_DECISION_REQUESTED" and not paused.is_set():
                runner.pause()
                paused.set()

        task = asyncio.create_task(runner.run(on_event=on_event))
        await asyncio.wait_for(paused.wait(), timeout=2)
        count_before = len(events)
        await asyncio.sleep(0.05)
        assert len(events) == count_before
        runner.resume()
        await asyncio.wait_for(task, timeout=2)
        assert any(event["type"] == "LLM_DECISION_RESPONSE" for event in events)

    asyncio.run(run_case())


def test_pause_during_openrouter_delays_apply_action(tmp_path) -> None:
    async def run_case() -> None:
        players = _make_players()
        run_files = init_run_files(tmp_path, "run-pause-openrouter")
        openrouter = DelayedOpenRouter()
        runner = LlmRunner(
            seed=123,
            players=players,
            run_id="run-pause-openrouter",
            openrouter=openrouter,
            run_files=run_files,
            event_delay_s=0,
            max_turns=4,
        )
        events: list[dict[str, Any]] = []
        decision_requested = asyncio.Event()
        decision_id: dict[str, str] = {}

        async def on_event(event: dict[str, Any]) -> None:
            events.append(event)
            if event["type"] == "LLM_DECISION_REQUESTED":
                decision_id["value"] = event["payload"]["decision_id"]
                decision_requested.set()

        task = asyncio.create_task(runner.run(on_event=on_event))
        await asyncio.wait_for(decision_requested.wait(), timeout=2)
        await asyncio.wait_for(openrouter.started.wait(), timeout=2)
        runner.pause()
        openrouter.allow_response.set()

        response_path = run_files.prompts_dir / f"decision_{decision_id['value']}_response.json"
        for _ in range(50):
            if response_path.exists():
                break
            await asyncio.sleep(0.02)
        assert response_path.exists()
        assert not any(event["type"] == "LLM_DECISION_RESPONSE" for event in events)

        runner.resume()
        await asyncio.wait_for(task, timeout=2)
        assert any(event["type"] == "LLM_DECISION_RESPONSE" for event in events)

    asyncio.run(run_case())
