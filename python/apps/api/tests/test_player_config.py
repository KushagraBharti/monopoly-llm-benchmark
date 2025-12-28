import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from monopoly_api.main import app, run_manager
from monopoly_api.player_config import (
    DEFAULT_SYSTEM_PROMPT,
    PlayerConfig,
    build_player_configs,
    derive_model_display_name,
)


def _write_players(path: Path, count: int) -> None:
    players = []
    for idx in range(count):
        players.append(
            {
                "player_id": f"p{idx + 1}",
                "name": f"Player {idx + 1}",
                "openrouter_model_id": "openai/gpt-oss-120b",
            }
        )
    path.write_text(json.dumps({"players": players}), encoding="utf-8")


def _make_player_config(player_id: str, name: str, model_id: str) -> PlayerConfig:
    return PlayerConfig(
        player_id=player_id,
        name=name,
        openrouter_model_id=model_id,
        model_display_name=derive_model_display_name(model_id),
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        reasoning=None,
    )


def test_players_file_wrong_count(tmp_path) -> None:
    config_path = tmp_path / "players.json"
    _write_players(config_path, 3)
    with pytest.raises(ValueError, match="exactly 4 players"):
        build_player_configs(requested_players=None, config_path=config_path)


def test_players_file_too_many(tmp_path) -> None:
    config_path = tmp_path / "players.json"
    _write_players(config_path, 5)
    with pytest.raises(ValueError, match="exactly 4 players"):
        build_player_configs(requested_players=None, config_path=config_path)


def test_players_file_requires_reasoning_effort(tmp_path) -> None:
    config_path = tmp_path / "players.json"
    players = [
        {
            "player_id": "p1",
            "name": "Player 1",
            "openrouter_model_id": "openai/gpt-oss-120b",
            "reasoning": {"budget_tokens": 1200},
        },
        {"player_id": "p2", "name": "Player 2", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p3", "name": "Player 3", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p4", "name": "Player 4", "openrouter_model_id": "openai/gpt-oss-120b"},
    ]
    config_path.write_text(json.dumps({"players": players}), encoding="utf-8")
    with pytest.raises(ValueError, match="reasoning.effort"):
        build_player_configs(requested_players=None, config_path=config_path)


def test_requested_players_wrong_count(tmp_path) -> None:
    config_path = tmp_path / "players.json"
    _write_players(config_path, 4)
    requested = [
        {"player_id": "p1", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p2", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p3", "openrouter_model_id": "openai/gpt-oss-120b"},
    ]
    with pytest.raises(ValueError, match="exactly 4 players"):
        build_player_configs(requested_players=requested, config_path=config_path)


def test_requested_players_unknown_id(tmp_path) -> None:
    config_path = tmp_path / "players.json"
    _write_players(config_path, 4)
    requested = [
        {"player_id": "p1", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p2", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p3", "openrouter_model_id": "openai/gpt-oss-120b"},
        {"player_id": "p9", "openrouter_model_id": "openai/gpt-oss-120b"},
    ]
    with pytest.raises(ValueError, match="Unknown player_id"):
        build_player_configs(requested_players=requested, config_path=config_path)


def test_run_start_rejects_wrong_count() -> None:
    client = TestClient(app)
    payload = {
        "seed": 123,
        "players": [
            {"player_id": "p1", "name": "P1"},
            {"player_id": "p2", "name": "P2"},
            {"player_id": "p3", "name": "P3"},
        ],
    }
    response = client.post("/run/start", json=payload)
    assert response.status_code == 400


def test_run_start_rejects_too_many_players() -> None:
    client = TestClient(app)
    payload = {
        "seed": 123,
        "players": [
            {"player_id": "p1", "name": "P1"},
            {"player_id": "p2", "name": "P2"},
            {"player_id": "p3", "name": "P3"},
            {"player_id": "p4", "name": "P4"},
            {"player_id": "p5", "name": "P5"},
        ],
    }
    response = client.post("/run/start", json=payload)
    assert response.status_code == 400


def test_run_status_preserves_free_model_id() -> None:
    previous_state = {
        "run_id": run_manager._run_id,
        "runner_task": run_manager._runner_task,
        "players": run_manager._players,
        "paused": run_manager._paused,
    }
    run_manager._run_id = "run-free-model"
    run_manager._runner_task = None
    run_manager._paused = False
    run_manager._players = [
        _make_player_config("p1", "P1", "openai/gpt-oss-120b:free"),
        _make_player_config("p2", "P2", "openai/gpt-oss-120b"),
        _make_player_config("p3", "P3", "openai/gpt-oss-120b"),
        _make_player_config("p4", "P4", "openai/gpt-oss-120b"),
    ]
    try:
        client = TestClient(app)
        response = client.get("/run/status")
        assert response.status_code == 200
        payload = response.json()
        player = next(item for item in payload.get("players", []) if item["player_id"] == "p1")
        assert player["openrouter_model_id"] == "openai/gpt-oss-120b:free"
        assert player["model_display_name"] == "gpt-oss-120b:free"
    finally:
        run_manager._run_id = previous_state["run_id"]
        run_manager._runner_task = previous_state["runner_task"]
        run_manager._players = previous_state["players"]
        run_manager._paused = previous_state["paused"]
