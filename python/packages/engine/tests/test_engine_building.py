from __future__ import annotations

from typing import Any

import pytest

from monopoly_engine import Engine
from monopoly_engine.board import SPACE_KEY_BY_INDEX


def _make_engine(seed: int = 11) -> Engine:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    return Engine(seed=seed, players=players, run_id=f"run-build-{seed}", max_turns=5, ts_step_ms=1)


def _set_pending_decision(engine: Engine, decision: dict[str, Any]) -> None:
    engine._pending_decision = decision
    engine._pending_turn = {
        "player_id": decision["player_id"],
        "decision_type": decision["decision_type"],
        "rolled_double": False,
    }


def test_build_requires_monopoly() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = "p2"

    decision = engine._build_post_turn_action_decision(player)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "build_houses_or_hotel" not in legal_actions


def test_build_blocked_by_mortgaged_group() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = player.player_id
    engine.state.board[1].mortgaged = True

    decision = engine._build_post_turn_action_decision(player)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "build_houses_or_hotel" not in legal_actions


def test_mortgage_blocked_with_buildings() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = player.player_id
    engine.state.board[1].houses = 1

    decision = engine._build_post_turn_action_decision(player)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "mortgage_property" not in legal_actions


def test_even_building_enforced() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = player.player_id

    decision = engine._build_post_turn_action_decision(player)
    assert "build_houses_or_hotel" in {entry["action"] for entry in decision["legal_actions"]}
    _set_pending_decision(engine, decision)

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "build_houses_or_hotel",
        "args": {
            "build_plan": [
                {"space_key": SPACE_KEY_BY_INDEX[1], "kind": "HOUSE", "count": 2},
            ]
        },
    }

    with pytest.raises(ValueError):
        engine.apply_action(action)


def test_build_hotel_returns_houses_to_bank() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = player.player_id
    engine.state.board[1].houses = 4
    engine.state.board[3].houses = 4

    bank_houses_before = engine.state.bank.houses_remaining
    bank_hotels_before = engine.state.bank.hotels_remaining
    cash_before = player.cash

    decision = engine._build_post_turn_action_decision(player)
    _set_pending_decision(engine, decision)

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "build_houses_or_hotel",
        "args": {
            "build_plan": [
                {"space_key": SPACE_KEY_BY_INDEX[1], "kind": "HOTEL", "count": 1},
            ]
        },
    }
    engine.apply_action(action)

    space = engine.state.board[1]
    assert space.hotel is True
    assert space.houses == 0
    assert engine.state.bank.hotels_remaining == bank_hotels_before - 1
    assert engine.state.bank.houses_remaining == bank_houses_before + 4
    assert player.cash == cash_before - 50


def test_bank_houses_limit_blocks_build() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = player.player_id
    engine.state.bank.houses_remaining = 0

    decision = engine._build_post_turn_action_decision(player)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "build_houses_or_hotel" not in legal_actions


def test_sell_hotel_requires_bank_houses() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    engine.state.board[1].owner_id = player.player_id
    engine.state.board[3].owner_id = player.player_id
    engine.state.board[1].hotel = True
    engine.state.bank.houses_remaining = 3

    decision = engine._build_post_turn_action_decision(player)
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "sell_houses_or_hotel" not in legal_actions


def test_rent_uses_houses_and_hotels() -> None:
    engine = _make_engine()
    owner = engine.state.players[0]
    space = engine.state.board[1]
    space.owner_id = owner.player_id

    space.houses = 2
    assert engine._calculate_rent(space, owner, dice_total=0) == 30

    space.houses = 0
    space.hotel = True
    assert engine._calculate_rent(space, owner, dice_total=0) == 250


def test_mortgage_and_unmortgage_property() -> None:
    engine = _make_engine()
    player = engine.state.players[0]
    engine.state.active_player_id = player.player_id
    space = engine.state.board[1]
    space.owner_id = player.player_id

    decision = engine._build_post_turn_action_decision(player)
    _set_pending_decision(engine, decision)
    cash_before = player.cash

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "mortgage_property",
        "args": {"space_key": SPACE_KEY_BY_INDEX[1]},
    }
    _, events, _, _ = engine.apply_action(action)
    assert space.mortgaged is True
    assert player.cash == cash_before + 30
    assert any(event["type"] == "PROPERTY_MORTGAGED" for event in events)

    engine.state.active_player_id = player.player_id
    player.cash = 100
    decision = engine._build_post_turn_action_decision(player)
    _set_pending_decision(engine, decision)
    cash_before = player.cash

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "unmortgage_property",
        "args": {"space_key": SPACE_KEY_BY_INDEX[1]},
    }
    _, events, _, _ = engine.apply_action(action)
    assert space.mortgaged is False
    assert player.cash == cash_before - 33
    assert any(event["type"] == "PROPERTY_UNMORTGAGED" for event in events)


def test_mortgaged_property_yields_no_rent() -> None:
    engine = _make_engine()
    engine.state.active_player_id = "p1"
    engine.state.players[0].position = 10
    engine.state.board[14].owner_id = "p2"
    engine.state.board[14].mortgaged = True
    engine._rng.roll_dice = lambda: (2, 2)

    cash_before = engine.state.players[0].cash
    _, events, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert all(event["type"] != "RENT_PAID" for event in events)
    assert engine.state.players[0].cash == cash_before
