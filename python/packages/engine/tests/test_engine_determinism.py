from monopoly_engine import Engine


def _collect_events(engine: Engine, limit: int | None = None) -> list[dict]:
    events: list[dict] = []
    while not engine.is_game_over():
        _, new_events, _, _ = engine.advance_until_decision(max_steps=1)
        if not new_events:
            break
        events.extend(new_events)
        if limit is not None and len(events) >= limit:
            return events[:limit]
    return events


def test_seed_reproducibility() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine_a = Engine(seed=42, players=players, run_id="run-test", max_turns=3, ts_step_ms=1)
    engine_b = Engine(seed=42, players=players, run_id="run-test", max_turns=3, ts_step_ms=1)

    events_a = _collect_events(engine_a)
    events_b = _collect_events(engine_b)

    assert events_a == events_b
    assert engine_a.get_snapshot() == engine_b.get_snapshot()


def test_event_ordering_invariants() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=7, players=players, run_id="run-test", max_turns=2, ts_step_ms=1)
    events = _collect_events(engine)

    assert events[0]["type"] == "GAME_STARTED"

    turn_event_types: dict[int, list[str]] = {}
    for event in events:
        if event["type"] in {"TURN_STARTED", "DICE_ROLLED", "PLAYER_MOVED", "CASH_CHANGED", "TURN_ENDED"}:
            turn_event_types.setdefault(event["turn_index"], []).append(event["type"])

    for types in turn_event_types.values():
        start_idx = types.index("TURN_STARTED")
        dice_idx = types.index("DICE_ROLLED")
        move_idx = types.index("PLAYER_MOVED")
        end_idx = types.index("TURN_ENDED")
        assert start_idx < dice_idx < move_idx < end_idx
