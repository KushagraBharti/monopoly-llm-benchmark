from __future__ import annotations

from monopoly_engine import Engine
from monopoly_engine.board import SPACE_KEY_BY_INDEX


def test_liquidation_mortgage_then_pay_rent() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=31, players=players, run_id="run-liquidation", max_turns=3, ts_step_ms=1)
    payer = engine.state.players[0]
    owner = engine.state.players[1]

    engine.state.active_player_id = payer.player_id
    payer.position = 10
    payer.cash = 5
    engine.state.board[1].owner_id = payer.player_id
    engine.state.board[14].owner_id = owner.player_id
    engine._rng.roll_dice = lambda: (2, 2)

    cash_owner_before = owner.cash

    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    assert decision["decision_type"] == "LIQUIDATION_DECISION"
    legal_actions = {entry["action"] for entry in decision["legal_actions"]}
    assert "mortgage_property" in legal_actions

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "mortgage_property",
        "args": {"space_key": SPACE_KEY_BY_INDEX[1]},
    }
    _, action_events, next_decision, _ = engine.apply_action(action)

    assert engine.state.board[1].mortgaged is True
    assert payer.cash == 23
    assert owner.cash == cash_owner_before + 12
    assert any(event["type"] == "RENT_PAID" for event in action_events)
    assert next_decision is not None
    assert next_decision["decision_type"] == "POST_TURN_ACTION_DECISION"
