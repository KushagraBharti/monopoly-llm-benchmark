import asyncio
import json
from typing import Any, Callable

from monopoly_arena import OpenRouterResult
from monopoly_telemetry import init_run_files

from monopoly_api.llm_runner import LlmRunner
from monopoly_api.player_config import DEFAULT_SYSTEM_PROMPT, PlayerConfig, derive_model_display_name


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


def _choose_buy_if_legal(decision: dict[str, Any], focus: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    legal = {entry.get("action") for entry in decision.get("legal_actions", [])}
    space_index = focus.get("landed_space", {}).get("space_index", 0)
    if "BUY_PROPERTY" in legal:
        return "BUY_PROPERTY", {"space_index": int(space_index)}
    if "START_AUCTION" in legal:
        return "START_AUCTION", {"space_index": int(space_index)}
    return next(iter(legal)), {}


class ScriptedOpenRouter:
    def __init__(
        self,
        policy: Callable[[int, int, dict[str, Any], dict[str, Any]], tuple[str, dict[str, Any]]],
    ) -> None:
        self._decision_index: dict[str, int] = {}
        self._decision_attempts: dict[str, int] = {}
        self._policy = policy

    async def create_chat_completion(self, *, messages: list[dict[str, Any]], **_: Any) -> OpenRouterResult:
        payload = _extract_payload(messages)
        if payload is None:
            return _tool_call_response("START_AUCTION", {"space_index": 0})
        decision = payload["decision"]
        focus = payload["decision_focus"]
        decision_id = decision["decision_id"]
        if decision_id not in self._decision_index:
            self._decision_index[decision_id] = len(self._decision_index)
            self._decision_attempts[decision_id] = 0
        decision_number = self._decision_index[decision_id]
        attempt = self._decision_attempts[decision_id]
        self._decision_attempts[decision_id] = attempt + 1
        tool_name, args = self._policy(decision_number, attempt, decision, focus)
        return _tool_call_response(tool_name, args)


def _policy(decision_number: int, attempt: int, decision: dict[str, Any], focus: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if decision_number == 0:
        return _choose_buy_if_legal(decision, focus)
    if decision_number == 1:
        if attempt == 0:
            return "BUY_PROPERTY", {}
        return _choose_buy_if_legal(decision, focus)
    if decision_number == 2:
        return "BUY_PROPERTY", {}
    return _choose_buy_if_legal(decision, focus)


def _expect_attempt_files(prompts_dir, prefix: str) -> None:
    assert (prompts_dir / f"{prefix}_system.txt").exists()
    assert (prompts_dir / f"{prefix}_user.json").exists()
    assert (prompts_dir / f"{prefix}_tools.json").exists()
    assert (prompts_dir / f"{prefix}_response.json").exists()
    assert (prompts_dir / f"{prefix}_parsed.json").exists()


def test_prompt_artifacts_written_for_normal_retry_and_fallback(tmp_path) -> None:
    players = _make_players()
    run_files = init_run_files(tmp_path, "run-artifacts")
    runner = LlmRunner(
        seed=2024,
        players=players,
        run_id="run-artifacts",
        openrouter=ScriptedOpenRouter(_policy),
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
    first_id, second_id, third_id = decision_order[:3]

    prompts_dir = run_files.prompts_dir
    assert prompts_dir.exists()

    _expect_attempt_files(prompts_dir, f"decision_{first_id}")
    _expect_attempt_files(prompts_dir, f"decision_{second_id}")
    _expect_attempt_files(prompts_dir, f"decision_{second_id}_retry1")
    _expect_attempt_files(prompts_dir, f"decision_{third_id}")
    _expect_attempt_files(prompts_dir, f"decision_{third_id}_retry1")

    parsed = json.loads((prompts_dir / f"decision_{second_id}_retry1_parsed.json").read_text(encoding="utf-8"))
    assert parsed["decision_id"] == second_id
    assert "final_action" in parsed
    assert "validation_errors" in parsed
