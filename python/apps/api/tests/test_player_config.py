import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from monopoly_api.main import app
from monopoly_api.player_config import build_player_configs


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
