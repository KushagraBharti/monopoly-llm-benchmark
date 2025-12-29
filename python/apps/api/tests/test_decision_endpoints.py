import json

from fastapi.testclient import TestClient

from monopoly_api.decision_index import DecisionIndex
from monopoly_api.main import app, run_manager
from monopoly_telemetry import init_run_files


def test_decision_endpoints_return_prompt_bundle(tmp_path) -> None:
    run_files = init_run_files(tmp_path, "run-decision-endpoints")
    decision_id = f"{run_files.run_id}-dec-000001"

    user_payload = {
        "schema_version": "v1",
        "full_state": {"run_id": run_files.run_id},
        "decision": {"decision_id": decision_id},
        "decision_focus": {
            "schema_version": "v1",
            "decision_id": decision_id,
            "decision_type": "BUY_OR_AUCTION_DECISION",
            "actor_player_id": "p1",
            "scenario": {
                "landed_space": "SPACE_6",
                "space_kind": "PROPERTY",
                "group": "LIGHT_BLUE",
                "price": 100,
                "house_cost": 50,
                "rent": [6, 30, 90, 270, 400, 550],
                "group_progress": {"you_own_in_group": 0, "total_in_group": 3},
            },
            "legal_tools": [
                {
                    "tool_name": "buy_property",
                    "requires": ["public_message", "private_thought"],
                    "args": {},
                },
                {
                    "tool_name": "start_auction",
                    "requires": ["public_message", "private_thought"],
                    "args": {},
                },
            ],
        },
    }
    tools = [{"type": "function", "function": {"name": "buy_property", "parameters": {"type": "object"}}}]
    response = {"ok": True, "choices": [{"message": {"role": "assistant", "content": None}}]}
    parsed = {
        "schema_version": "v1",
        "decision_id": decision_id,
        "attempt_index": 0,
        "parsed_tool_call": {"name": "buy_property", "arguments": "{}"},
        "validation_errors": [],
        "error_reason": None,
        "tool_action": {
            "schema_version": "v1",
            "decision_id": decision_id,
            "action": "buy_property",
            "args": {},
        },
        "openrouter_request_id": "req-1",
        "openrouter_status_code": 200,
        "openrouter_error_type": None,
        "final_action": {
            "schema_version": "v1",
            "decision_id": decision_id,
            "action": "buy_property",
            "args": {},
        },
        "retry_used": False,
        "fallback_used": False,
        "fallback_reason": None,
    }
    run_files.write_prompt_artifacts(
        decision_id=decision_id,
        attempt_index=0,
        system_prompt="system prompt",
        user_payload=user_payload,
        tools=tools,
        response=response,
        parsed=parsed,
    )

    run_files.write_decision(
        {
            "phase": "decision_started",
            "run_id": run_files.run_id,
            "turn_index": 1,
            "decision_id": decision_id,
            "decision_type": "BUY_OR_AUCTION_DECISION",
            "player_id": "p1",
            "player_name": "P1",
            "openrouter_model_id": "openai/gpt-oss-120b",
            "model_display_name": "gpt-oss-120b",
            "timestamp": "2025-01-01T00:00:00Z",
            "request_start_ms": 1000,
            "prompt_messages": [],
            "prompt_payload": user_payload,
            "prompt_payload_raw": json.dumps(user_payload, separators=(",", ":"), ensure_ascii=True),
        }
    )
    run_files.write_decision(
        {
            "phase": "decision_resolved",
            "run_id": run_files.run_id,
            "turn_index": 1,
            "decision_id": decision_id,
            "decision_type": "BUY_OR_AUCTION_DECISION",
            "player_id": "p1",
            "player_name": "P1",
            "openrouter_model_id": "openai/gpt-oss-120b",
            "model_display_name": "gpt-oss-120b",
            "timestamp": "2025-01-01T00:00:01Z",
            "retry_used": False,
            "fallback_used": False,
            "fallback_reason": None,
            "final_action": parsed["final_action"],
            "request_start_ms": 1000,
            "response_end_ms": 1150,
            "latency_ms": 150,
        }
    )

    previous_state = {
        "run_id": run_manager._run_id,
        "telemetry": run_manager._telemetry,
        "decision_index": run_manager._decision_index,
        "runner": run_manager._runner,
        "runner_task": run_manager._runner_task,
        "players": run_manager._players,
        "paused": run_manager._paused,
    }
    run_manager._run_id = run_files.run_id
    run_manager._telemetry = run_files
    run_manager._decision_index = DecisionIndex(run_files)
    run_manager._runner = None
    run_manager._runner_task = None
    run_manager._players = []
    run_manager._paused = False
    try:
        client = TestClient(app)
        recent = client.get("/run/decisions/recent?limit=5")
        assert recent.status_code == 200
        recent_payload = recent.json()
        assert "decisions" in recent_payload
        assert recent_payload["decisions"][0]["decision_id"] == decision_id
        assert recent_payload["decisions"][0]["retry_used"] is False
        assert recent_payload["decisions"][0]["fallback_used"] is False
        assert recent_payload["decisions"][0]["latency_ms"] == 150

        detail = client.get(f"/run/decision/{decision_id}")
        assert detail.status_code == 200
        bundle = detail.json()
        assert bundle["decision_id"] == decision_id
        assert bundle["final_action"]["action"] == "buy_property"
        assert bundle["timing"]["latency_ms"] == 150
        assert bundle["attempts"][0]["system_prompt"] == "system prompt"
        assert bundle["attempts"][0]["user_payload"]["schema_version"] == "v1"
        assert bundle["attempts"][0]["tools"][0]["function"]["name"] == "buy_property"
        assert bundle["attempts"][0]["response"]["ok"] is True
        assert bundle["attempts"][0]["parsed_tool_call"]["name"] == "buy_property"
    finally:
        run_manager._run_id = previous_state["run_id"]
        run_manager._telemetry = previous_state["telemetry"]
        run_manager._decision_index = previous_state["decision_index"]
        run_manager._runner = previous_state["runner"]
        run_manager._runner_task = previous_state["runner_task"]
        run_manager._players = previous_state["players"]
        run_manager._paused = previous_state["paused"]
