from monopoly_api.mock_runner import MockRunner, create_initial_state


def test_snapshot_shape() -> None:
    snapshot = create_initial_state("run-test", [{"player_id": "p1", "name": "P1"}])
    assert snapshot["schema_version"] == "v1"
    assert snapshot["run_id"] == "run-test"
    assert snapshot["turn_index"] == 0
    assert snapshot["phase"] in {
        "START_TURN",
        "RESOLVING_MOVE",
        "AWAITING_DECISION",
        "END_TURN",
        "GAME_OVER",
    }
    assert snapshot["active_player_id"] == "p1"
    assert len(snapshot["board"]) == 40
    for space in snapshot["board"]:
        assert 0 <= space["index"] <= 39
        assert space["kind"] is not None
        assert space["name"]


def test_event_shape_and_seq() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    runner = MockRunner(seed=321, players=players, run_id="run-test", event_delay_s=0)
    events = runner.generate_events(limit=12)

    assert events
    assert [event["seq"] for event in events] == list(range(len(events)))
    assert all(event["schema_version"] == "v1" for event in events)
    assert all(event["run_id"] == "run-test" for event in events)
    assert all(event["event_id"] for event in events)

    moved = next(event for event in events if event["type"] == "PLAYER_MOVED")
    assert 0 <= moved["payload"]["from"] <= 39
    assert 0 <= moved["payload"]["to"] <= 39
