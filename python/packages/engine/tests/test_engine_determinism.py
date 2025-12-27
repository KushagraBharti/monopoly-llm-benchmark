from monopoly_engine import Engine

from .utils import collect_events


def test_seed_reproducibility() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine_a = Engine(seed=42, players=players, run_id="run-test", max_turns=3, ts_step_ms=1)
    engine_b = Engine(seed=42, players=players, run_id="run-test", max_turns=3, ts_step_ms=1)

    events_a = collect_events(engine_a)
    events_b = collect_events(engine_b)

    assert events_a == events_b
    assert engine_a.get_snapshot() == engine_b.get_snapshot()


def test_event_ordering_invariants() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=7, players=players, run_id="run-test", max_turns=2, ts_step_ms=1)
    events = collect_events(engine)

    assert events[0]["type"] == "GAME_STARTED"

    turn_event_types: dict[int, list[str]] = {}
    for event in events:
        if event["type"] in {"TURN_STARTED", "DICE_ROLLED", "PLAYER_MOVED", "TURN_ENDED"}:
            turn_event_types.setdefault(event["turn_index"], []).append(event["type"])

    for types in turn_event_types.values():
        start_idx = types.index("TURN_STARTED")
        dice_idx = types.index("DICE_ROLLED")
        end_idx = types.index("TURN_ENDED")
        assert start_idx < dice_idx < end_idx
        if "PLAYER_MOVED" in types:
            move_idx = types.index("PLAYER_MOVED")
            assert dice_idx < move_idx < end_idx
