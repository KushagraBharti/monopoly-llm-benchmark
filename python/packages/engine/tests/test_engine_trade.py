from __future__ import annotations

import pytest

from monopoly_engine import Engine


def _start_post_turn(engine: Engine, player_id: str) -> dict[str, object]:
    player = next(player for player in engine.state.players if player.player_id == player_id)
    engine.state.active_player_id = player_id
    decision = engine._build_post_turn_action_decision(player)
    engine.state.phase = "AWAITING_DECISION"
    engine._pending_decision = decision
    engine._pending_turn = {
        "player_id": player_id,
        "decision_type": "POST_TURN_ACTION_DECISION",
        "rolled_double": False,
    }
    return decision


def test_trade_happy_path_accept_transfers_cash_and_property() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=77, players=players, run_id="run-trade-accept", max_turns=3, ts_step_ms=1)
    engine.state.board[1].owner_id = "p1"
    engine.state.board[3].owner_id = "p2"
    engine.state.players[0].cash = 500
    engine.state.players[1].cash = 300

    decision = _start_post_turn(engine, "p1")
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "propose_trade",
        "args": {
            "to_player_id": "p2",
            "offer": {"cash": 100, "properties": ["MEDITERRANEAN_AVENUE"], "get_out_of_jail_cards": 0},
            "request": {"cash": 0, "properties": ["BALTIC_AVENUE"], "get_out_of_jail_cards": 0},
        },
    }
    _, propose_events, trade_decision, _ = engine.apply_action(action)
    assert trade_decision is not None
    assert trade_decision["decision_type"] == "TRADE_RESPONSE_DECISION"
    assert any(event["type"] == "TRADE_PROPOSED" for event in propose_events)

    accept_action = {
        "schema_version": "v1",
        "decision_id": trade_decision["decision_id"],
        "action": "accept_trade",
        "args": {},
    }
    _, accept_events, _, _ = engine.apply_action(accept_action)

    assert engine.state.board[1].owner_id == "p2"
    assert engine.state.board[3].owner_id == "p1"
    assert engine.state.players[0].cash == 400
    assert engine.state.players[1].cash == 400
    assert any(event["type"] == "TRADE_ACCEPTED" for event in accept_events)
    transfer_events = [event for event in accept_events if event["type"] == "PROPERTY_TRANSFERRED"]
    assert len(transfer_events) == 2


def test_trade_counter_flips_actor_and_caps_at_max_exchanges() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=78, players=players, run_id="run-trade-counter", max_turns=3, ts_step_ms=1)
    decision = _start_post_turn(engine, "p1")
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "propose_trade",
        "args": {
            "to_player_id": "p2",
            "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
            "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
        },
    }
    _, _, trade_decision, _ = engine.apply_action(action)
    assert trade_decision is not None
    assert engine.state.trade is not None

    next_decision = trade_decision
    expected_actor = "p1"
    for step in range(5):
        counter_action = {
            "schema_version": "v1",
            "decision_id": next_decision["decision_id"],
            "action": "counter_trade",
            "args": {
                "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
            },
        }
        _, events, next_decision, _ = engine.apply_action(counter_action)
        if step < 4:
            assert next_decision is not None
            assert any(event["type"] == "TRADE_COUNTERED" for event in events)
            assert next_decision["player_id"] == expected_actor
            expected_actor = "p2" if expected_actor == "p1" else "p1"
        else:
            assert next_decision is None
            assert engine.state.trade is None
            assert any(event["type"] == "TRADE_EXPIRED" for event in events)


def test_trade_reject_clears_trade() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=79, players=players, run_id="run-trade-reject", max_turns=3, ts_step_ms=1)
    decision = _start_post_turn(engine, "p1")
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "propose_trade",
        "args": {
            "to_player_id": "p2",
            "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
            "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
        },
    }
    _, _, trade_decision, _ = engine.apply_action(action)
    assert trade_decision is not None

    reject_action = {
        "schema_version": "v1",
        "decision_id": trade_decision["decision_id"],
        "action": "reject_trade",
        "args": {},
    }
    _, events, _, _ = engine.apply_action(reject_action)
    assert engine.state.trade is None
    assert any(event["type"] == "TRADE_REJECTED" for event in events)


def test_trade_disallows_properties_with_buildings() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=80, players=players, run_id="run-trade-buildings", max_turns=3, ts_step_ms=1)
    engine.state.board[1].owner_id = "p1"
    engine.state.board[1].houses = 1
    decision = _start_post_turn(engine, "p1")
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "propose_trade",
        "args": {
            "to_player_id": "p2",
            "offer": {"cash": 0, "properties": ["MEDITERRANEAN_AVENUE"], "get_out_of_jail_cards": 0},
            "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
        },
    }
    with pytest.raises(ValueError):
        engine.apply_action(action)


def test_trade_accept_illegal_if_cannot_pay_mortgage_interest() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=81, players=players, run_id="run-trade-mortgage", max_turns=3, ts_step_ms=1)
    engine.state.board[1].owner_id = "p1"
    engine.state.board[1].mortgaged = True
    engine.state.players[1].cash = 0
    decision = _start_post_turn(engine, "p1")
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "propose_trade",
        "args": {
            "to_player_id": "p2",
            "offer": {"cash": 0, "properties": ["MEDITERRANEAN_AVENUE"], "get_out_of_jail_cards": 0},
            "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
        },
    }
    _, _, trade_decision, _ = engine.apply_action(action)
    assert trade_decision is not None
    legal_actions = {entry["action"] for entry in trade_decision.get("legal_actions", [])}
    assert "accept_trade" not in legal_actions
