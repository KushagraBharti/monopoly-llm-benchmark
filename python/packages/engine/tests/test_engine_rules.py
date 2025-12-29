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
    engine._rng.roll_dice = lambda: (1, 3)
    target_index = 14
    engine.state.board[target_index].owner_id = None

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert events
    assert decision is not None
    assert decision["decision_type"] == "BUY_OR_AUCTION_DECISION"
    assert engine.state.phase == "AWAITING_DECISION"
    assert any(event["type"] == "LLM_DECISION_REQUESTED" for event in events)
    assert all(event["type"] != "TURN_ENDED" for event in events)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "buy_property" in legal_actions

    cash_before = engine.state.players[0].cash
    price = engine.state.board[target_index].price or 0
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "buy_property",
        "args": {},
    }
    _, action_events, _, _ = engine.apply_action(action)

    assert engine.state.board[target_index].owner_id == "p1"
    assert engine.state.players[0].cash == cash_before - price
    assert any(event["type"] == "PROPERTY_PURCHASED" for event in action_events)
    assert any(
        event["type"] == "CASH_CHANGED" and event["payload"]["reason"] == "buy_property"
        for event in action_events
    )


def test_start_auction_starts_bid_round() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-auction", max_turns=5, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    engine._rng.roll_dice = lambda: (1, 3)
    target_index = 14
    engine.state.board[target_index].owner_id = None

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert any(event["type"] == "LLM_DECISION_REQUESTED" for event in events)

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "start_auction",
        "args": {},
    }
    _, action_events, new_decision, _ = engine.apply_action(action)

    assert engine.state.board[target_index].owner_id is None
    assert engine.state.auction is not None
    assert any(event["type"] == "AUCTION_STARTED" for event in action_events)
    assert any(event["type"] == "LLM_DECISION_RESPONSE" for event in action_events)
    assert any(event["type"] == "LLM_DECISION_REQUESTED" for event in action_events)
    assert new_decision is not None
    assert new_decision["decision_type"] == "AUCTION_BID_DECISION"
    assert all(event["type"] != "PROPERTY_PURCHASED" for event in action_events)


def test_illegal_action_rejected() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=123, players=players, run_id="run-illegal", max_turns=5, ts_step_ms=1)
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    engine._rng.roll_dice = lambda: (1, 3)

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
    engine._rng.roll_dice = lambda: (1, 3)
    rent_index = 14
    engine.state.board[rent_index].owner_id = "p2"

    cash_p1 = engine.state.players[0].cash
    cash_p2 = engine.state.players[1].cash

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "POST_TURN_ACTION_DECISION"
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
    engine._rng.roll_dice = lambda: (1, 3)
    engine.state.board[1].owner_id = "p2"
    engine.state.board[3].owner_id = "p2"

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "POST_TURN_ACTION_DECISION"
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
    engine._rng.roll_dice = lambda: (1, 3)
    engine.state.players[0].cash = 5
    engine.state.board[1].owner_id = "p1"
    engine.state.board[1].mortgaged = True
    rent_index = 14
    engine.state.board[rent_index].owner_id = "p2"
    cash_p2 = engine.state.players[1].cash

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "LIQUIDATION_DECISION"

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "declare_bankruptcy",
        "args": {},
    }
    _, action_events, _, _ = engine.apply_action(action)

    assert any(event["type"] == "CASH_CHANGED" for event in action_events)
    assert engine.state.players[0].bankrupt is True
    assert engine.state.players[0].bankrupt_to == "p2"
    assert engine.state.players[0].cash == 0
    assert engine.state.players[1].cash == cash_p2 + 5
    assert engine.state.board[1].owner_id == "p2"
    assert engine.state.active_player_id == "p2"


def test_go_to_jail_moves_player() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=42, players=players, run_id="run-go-jail", max_turns=3, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.position = 28
    engine._rng.roll_dice = lambda: (1, 1)

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)

    assert decision is None
    assert player.in_jail is True
    assert player.position == engine._jail_index
    assert player.doubles_count == 0
    assert any(
        event["type"] == "SENT_TO_JAIL" and event["payload"]["reason"] == "GO_TO_JAIL"
        for event in events
    )


def test_three_doubles_sends_player_to_jail() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=7, players=players, run_id="run-three-doubles", max_turns=3, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.position = 4
    player.doubles_count = 2
    engine._rng.roll_dice = lambda: (3, 3)

    _, events, decision, _ = engine.advance_until_decision(max_steps=1)

    assert decision is None
    assert player.in_jail is True
    assert player.position == engine._jail_index
    assert any(
        event["type"] == "SENT_TO_JAIL" and event["payload"]["reason"] == "THREE_DOUBLES"
        for event in events
    )


def test_jail_roll_fails_ends_turn() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=11, players=players, run_id="run-jail-fail", max_turns=4, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.in_jail = True
    player.position = engine._jail_index
    engine._rng.roll_dice = lambda: (1, 2)

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "JAIL_DECISION"

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "roll_for_doubles",
        "args": {},
    }
    _, action_events, new_decision, _ = engine.apply_action(action)

    assert new_decision is None
    assert player.in_jail is True
    assert player.position == engine._jail_index
    assert player.jail_turns == 1
    assert any(event["type"] == "TURN_ENDED" for event in action_events)
    assert all(event["type"] != "PLAYER_MOVED" for event in action_events)


def test_jail_roll_success_leaves_jail() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=13, players=players, run_id="run-jail-success", max_turns=4, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.in_jail = True
    player.position = engine._jail_index
    engine.state.board[14].owner_id = "p1"
    engine._rng.roll_dice = lambda: (2, 2)

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "JAIL_DECISION"

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "roll_for_doubles",
        "args": {},
    }
    _, action_events, new_decision, _ = engine.apply_action(action)

    assert new_decision is not None
    assert new_decision["decision_type"] == "POST_TURN_ACTION_DECISION"
    assert player.in_jail is False
    assert player.position == 14
    assert player.jail_turns == 0
    assert any(event["type"] == "PLAYER_MOVED" for event in action_events)


def test_pay_jail_fine_leaves_jail() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=17, players=players, run_id="run-jail-fine", max_turns=4, ts_step_ms=1)
    player = engine.state.players[0]
    engine.state.active_player_id = "p1"
    player.in_jail = True
    player.position = engine._jail_index
    engine.state.board[13].owner_id = "p1"
    engine._rng.roll_dice = lambda: (1, 2)
    cash_before = player.cash

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "JAIL_DECISION"

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "pay_jail_fine",
        "args": {},
    }
    _, action_events, new_decision, _ = engine.apply_action(action)

    assert new_decision is not None
    assert new_decision["decision_type"] == "POST_TURN_ACTION_DECISION"
    assert player.in_jail is False
    assert player.position == engine._jail_index + 3
    assert player.cash == cash_before - 50
    assert any(
        event["type"] == "CASH_CHANGED" and event["payload"]["reason"] == "JAIL_FINE"
        for event in action_events
    )


def test_third_failed_attempt_requires_fine() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=23, players=players, run_id="run-jail-third", max_turns=6, ts_step_ms=1)
    player = engine.state.players[0]
    player.in_jail = True
    player.jail_turns = 2
    player.position = engine._jail_index
    player.cash = 200
    engine.state.active_player_id = "p1"
    engine.state.players[1].position = 7
    rolls = iter([(1, 2), (1, 2)])
    engine._rng.roll_dice = lambda: next(rolls)

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "roll_for_doubles",
        "args": {},
    }
    engine.apply_action(action)
    assert player.jail_turns == 3

    _, _, decision_after, _ = engine.advance_until_decision(max_steps=1)
    assert decision_after is not None
    assert decision_after["decision_type"] == "JAIL_DECISION"
    legal_actions = {entry["action"] for entry in decision_after["legal_actions"]}
    assert legal_actions == {"pay_jail_fine"}
