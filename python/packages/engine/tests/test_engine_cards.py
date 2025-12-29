from __future__ import annotations

from typing import Any

from monopoly_engine import Engine


def _make_engine(seed: int = 7) -> Engine:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    return Engine(seed=seed, players=players, run_id=f"run-cards-{seed}", max_turns=5, ts_step_ms=1)


def test_deck_shuffle_deterministic() -> None:
    engine_a = _make_engine(seed=42)
    engine_b = _make_engine(seed=42)

    assert engine_a._chance_deck == engine_b._chance_deck
    assert engine_a._community_chest_deck == engine_b._community_chest_deck


def test_get_out_of_jail_card_removed_and_returned() -> None:
    engine = _make_engine(seed=1)
    player = engine.state.players[0]
    engine._chance_deck = ["GET_OUT_OF_JAIL_FREE", "ADVANCE_TO_GO"]

    events: list[dict[str, Any]] = []
    engine._draw_card("CHANCE", player, events, turn_index=0, rolled_double=False)

    assert player.get_out_of_jail_cards == 1
    assert engine._chance_deck == ["ADVANCE_TO_GO"]

    engine.state.active_player_id = player.player_id
    player.in_jail = True
    player.position = engine._jail_index
    engine._rng.roll_dice = lambda: (1, 2)

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "use_get_out_of_jail_card" in legal_actions

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "use_get_out_of_jail_card",
        "args": {},
    }
    engine.apply_action(action)

    assert player.get_out_of_jail_cards == 0
    assert engine._chance_deck[-1] == "GET_OUT_OF_JAIL_FREE"


def test_card_go_to_jail() -> None:
    engine = _make_engine(seed=2)
    player = engine.state.players[0]
    engine._chance_deck = ["GO_TO_JAIL"]
    player.position = 7

    events: list[dict[str, Any]] = []
    engine._draw_card("CHANCE", player, events, turn_index=0, rolled_double=False)

    assert player.in_jail is True
    assert player.position == engine._jail_index
    assert any(
        event["type"] == "SENT_TO_JAIL" and event["payload"]["reason"] == "CHANCE_CARD"
        for event in events
    )
    assert engine._chance_deck == ["GO_TO_JAIL"]


def test_go_back_three_spaces_resolves_tax() -> None:
    engine = _make_engine(seed=3)
    player = engine.state.players[0]
    engine._chance_deck = ["GO_BACK_3_SPACES"]
    player.position = 7
    cash_before = player.cash

    events: list[dict[str, Any]] = []
    engine._draw_card("CHANCE", player, events, turn_index=0, rolled_double=False)

    assert player.position == 4
    assert any(
        event["type"] == "CASH_CHANGED" and event["payload"]["reason"] == "TAX_INCOME"
        for event in events
    )
    assert player.cash == cash_before - 200


def test_card_nearest_utility_rolls_and_pays() -> None:
    engine = _make_engine(seed=4)
    player = engine.state.players[0]
    owner = engine.state.players[1]
    engine._chance_deck = ["GO_TO_NEAREST_UTILITY"]
    player.position = 7
    engine.state.board[12].owner_id = owner.player_id
    engine._rng.roll_dice = lambda: (3, 4)

    cash_p1 = player.cash
    cash_p2 = owner.cash
    events: list[dict[str, Any]] = []
    engine._draw_card("CHANCE", player, events, turn_index=0, rolled_double=False)

    assert player.position == 12
    assert any(
        event["type"] == "DICE_ROLLED"
        and event["payload"].get("reason") == "CARD_UTILITY_RENT"
        for event in events
    )
    rent_event = next(event for event in events if event["type"] == "RENT_PAID")
    assert rent_event["payload"]["amount"] == 70
    assert player.cash == cash_p1 - 70
    assert owner.cash == cash_p2 + 70


def test_repairs_card_costs_houses_and_hotels() -> None:
    engine = _make_engine(seed=5)
    player = engine.state.players[0]
    engine._chance_deck = ["GENERAL_REPAIRS"]

    engine.state.board[1].owner_id = player.player_id
    engine.state.board[1].houses = 2
    engine.state.board[3].owner_id = player.player_id
    engine.state.board[3].hotel = True

    cash_before = player.cash
    events: list[dict[str, Any]] = []
    engine._draw_card("CHANCE", player, events, turn_index=0, rolled_double=False)

    assert player.cash == cash_before - 150
    assert any(
        event["type"] == "CASH_CHANGED" and event["payload"]["reason"] == "GENERAL_REPAIRS"
        for event in events
    )
