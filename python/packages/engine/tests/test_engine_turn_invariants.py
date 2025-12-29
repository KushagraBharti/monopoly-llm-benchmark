from __future__ import annotations

import itertools

import pytest

from monopoly_engine import Engine

from .utils import choose_action, collect_events


def _make_players() -> list[dict[str, str]]:
    return [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
        {"player_id": "p4", "name": "P4"},
    ]


def test_turn_started_rotates_without_doubles() -> None:
    engine = Engine(seed=7, players=_make_players(), run_id="run-turn-rot", max_turns=12, ts_step_ms=1)
    roll_cycle = itertools.cycle([(1, 2), (3, 4), (1, 3), (2, 3)])
    engine._rng.roll_dice = lambda: next(roll_cycle)

    started_players: list[str] = []
    while len(started_players) < 6 and not engine.is_game_over():
        _, events, decision, _ = engine.advance_until_decision(max_steps=1)
        if any(event["type"] == "TURN_STARTED" for event in events):
            started_players.append(engine.state.active_player_id)
        if decision is None:
            break
        snapshot = engine.get_snapshot()
        assert snapshot["active_player_id"] == decision["player_id"]
        assert snapshot["turn_index"] == decision["turn_index"]
        action = choose_action(decision)
        engine.apply_action(action)

    assert started_players[:6] == ["p1", "p2", "p3", "p4", "p1", "p2"]


def test_turn_started_has_turn_ended_between() -> None:
    engine = Engine(seed=19, players=_make_players(), run_id="run-turn-ended", max_turns=10, ts_step_ms=1)
    events = collect_events(engine, limit=200)

    open_turn = False
    for event in events:
        if event["type"] == "TURN_STARTED":
            assert open_turn is False
            open_turn = True
        elif event["type"] == "TURN_ENDED":
            open_turn = False


def test_turn_started_rotates_even_with_doubles() -> None:
    engine = Engine(
        seed=31,
        players=_make_players(),
        run_id="run-turn-double",
        max_turns=12,
        ts_step_ms=1,
        allow_extra_turns=False,
    )
    engine._rng.roll_dice = lambda: (2, 2)

    started_players: list[str] = []
    while len(started_players) < 6 and not engine.is_game_over():
        _, events, decision, _ = engine.advance_until_decision(max_steps=1)
        if any(event["type"] == "TURN_STARTED" for event in events):
            started_players.append(engine.state.active_player_id)
        if decision is None:
            break
        action = choose_action(decision)
        engine.apply_action(action)

    assert started_players[:6] == ["p1", "p2", "p3", "p4", "p1", "p2"]


def test_decision_id_applies_once() -> None:
    engine = Engine(seed=23, players=_make_players(), run_id="run-decision-id", max_turns=6, ts_step_ms=1)
    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    action = choose_action(decision)
    engine.apply_action(action)
    snapshot = engine.get_snapshot()

    with pytest.raises(ValueError, match="Decision id already applied"):
        engine.apply_action(action)

    assert engine.get_snapshot() == snapshot
