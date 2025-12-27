from __future__ import annotations

import pytest

from monopoly_engine import Engine

from .utils import collect_events


def test_headless_run_200_turns() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
    ]
    engine = Engine(seed=99, players=players, run_id="run-long", max_turns=200, ts_step_ms=1)
    events = collect_events(engine)
    assert events
    assert engine.state.turn_index <= 200

    player_ids = {player["player_id"] for player in players}
    for player in engine.state.players:
        assert isinstance(player.cash, int)
        assert 0 <= player.position <= 39
    for space in engine.state.board:
        assert space.owner_id is None or space.owner_id in player_ids


def test_deterministic_replay() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine_a = Engine(seed=202, players=players, run_id="run-det", max_turns=20, ts_step_ms=1)
    engine_b = Engine(seed=202, players=players, run_id="run-det", max_turns=20, ts_step_ms=1)

    events_a = collect_events(engine_a)
    events_b = collect_events(engine_b)

    assert events_a == events_b
    assert engine_a.get_snapshot() == engine_b.get_snapshot()


def test_buy_decision_and_purchase() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-buy", max_turns=5, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    target_index = 14
    engine.state.board[target_index].owner_id = None

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert events
    assert decision is not None
    assert decision["decision_type"] == "BUY_DECISION"
    assert engine.state.phase == "AWAITING_DECISION"
    assert any(event["type"] == "LLM_DECISION_REQUESTED" for event in events)
    assert all(event["type"] != "TURN_ENDED" for event in events)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "BUY_PROPERTY" in legal_actions

    cash_before = engine.state.players[0].cash
    price = engine.state.board[target_index].price or 0
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "BUY_PROPERTY",
        "args": {"space_index": target_index},
    }
    _, action_events, _, _ = engine.apply_action(action)

    assert engine.state.board[target_index].owner_id == "p1"
    assert engine.state.players[0].cash == cash_before - price
    assert any(event["type"] == "PROPERTY_PURCHASED" for event in action_events)
    assert any(
        event["type"] == "CASH_CHANGED" and event["payload"]["reason"] == "BUY_PROPERTY"
        for event in action_events
    )


def test_start_auction_placeholder() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-auction", max_turns=5, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    target_index = 14
    engine.state.board[target_index].owner_id = None

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert any(event["type"] == "LLM_DECISION_REQUESTED" for event in events)

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "START_AUCTION",
        "args": {"space_index": target_index},
    }
    _, action_events, _, _ = engine.apply_action(action)

    assert engine.state.board[target_index].owner_id is None
    assert any(event["type"] == "LLM_DECISION_RESPONSE" for event in action_events)
    assert any(event["type"] == "TURN_ENDED" for event in action_events)
    assert all(event["type"] != "PROPERTY_PURCHASED" for event in action_events)


def test_illegal_action_rejected() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-illegal", max_turns=5, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None

    with pytest.raises(ValueError):
        engine.apply_action(
            {
                "schema_version": "v1",
                "decision_id": decision["decision_id"],
                "action": "END_TURN",
                "args": {},
            }
        )


def test_rent_payment() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-rent", max_turns=3, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    rent_index = 14
    engine.state.board[rent_index].owner_id = "p2"

    cash_p1 = engine.state.players[0].cash
    cash_p2 = engine.state.players[1].cash

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is None
    rent_event = next(event for event in events if event["type"] == "RENT_PAID")
    assert rent_event["payload"]["amount"] == 12
    assert engine.state.players[0].cash == cash_p1 - 12
    assert engine.state.players[1].cash == cash_p2 + 12


def test_monopoly_doubles_base_rent() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-monopoly", max_turns=3, ts_step_ms=1)
    engine.state.players[0].position = 37
    engine.state.active_player_id = "p1"
    engine.state.board[1].owner_id = "p2"
    engine.state.board[3].owner_id = "p2"

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is None
    rent_event = next(event for event in events if event["type"] == "RENT_PAID")
    assert rent_event["payload"]["amount"] == 4


def test_bankruptcy_on_rent_transfers_assets() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-bankrupt", max_turns=3, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    engine.state.players[0].cash = 5
    engine.state.board[1].owner_id = "p1"
    rent_index = 14
    engine.state.board[rent_index].owner_id = "p2"
    cash_p2 = engine.state.players[1].cash

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is None
    rent_event = next(event for event in events if event["type"] == "RENT_PAID")
    assert rent_event["payload"]["amount"] == 5

    assert engine.state.players[0].bankrupt is True
    assert engine.state.players[0].bankrupt_to == "p2"
    assert engine.state.players[0].cash == 0
    assert engine.state.players[1].cash == cash_p2 + 5
    assert engine.state.board[1].owner_id == "p2"
    assert engine.state.active_player_id == "p2"
