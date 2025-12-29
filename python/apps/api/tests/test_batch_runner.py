import asyncio
import json
from pathlib import Path
from typing import Any

from monopoly_arena import OpenRouterResult
from monopoly_arena.batch_run import run_batch
from monopoly_arena.paths import default_players_config_path


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


class DeterministicOpenRouter:
    async def create_chat_completion(self, *, messages: list[dict[str, Any]], **_: Any):
        payload = _extract_payload(messages)
        decision = payload["decision"] if payload else {}
        legal = {entry.get("action") for entry in decision.get("legal_actions", [])}
        if "buy_property" in legal:
            action_name, args = "buy_property", {}
        elif "start_auction" in legal:
            action_name, args = "start_auction", {}
        elif "end_turn" in legal:
            action_name, args = "end_turn", {}
        elif "reject_trade" in legal:
            action_name, args = "reject_trade", {}
        else:
            action_name, args = next(iter(legal)), {}
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
                                    "name": action_name,
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


def test_batch_runner_writes_index_and_summaries(tmp_path: Path) -> None:
    config_path = tmp_path / "batch.json"
    config = {
        "batch_id": "batch-test",
        "seeds": [11, 12],
        "matches": 2,
        "players": str(default_players_config_path()),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    index_path = asyncio.run(
        run_batch(
            json.loads(config_path.read_text(encoding="utf-8")),
            runs_dir=tmp_path,
            openrouter_factory=DeterministicOpenRouter,
        )
    )

    assert index_path.exists()
    lines = [line for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    for line in lines:
        entry = json.loads(line)
        run_dir = Path(entry["run_dir"])
        summary_path = run_dir / "summary.json"
        assert summary_path.exists()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert "players" in summary
        assert "decision_stats" in summary
        assert "property_acquisition_timeline" in summary
