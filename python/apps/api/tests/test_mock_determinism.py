from monopoly_api.mock_runner import MockRunner


def test_mock_determinism() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    runner_a = MockRunner(seed=123, players=players, run_id="test-run", event_delay_s=0)
    runner_b = MockRunner(seed=123, players=players, run_id="test-run", event_delay_s=0)

    events_a = runner_a.generate_events(limit=14)
    events_b = runner_b.generate_events(limit=14)

    assert events_a == events_b

    stripped = []
    for event in events_a:
        payload = event["payload"]
        if event["type"] in {"LLM_DECISION_REQUESTED", "LLM_DECISION_RESPONSE"}:
            payload = {key: value for key, value in payload.items() if key != "decision_id"}
        stripped.append({"type": event["type"], "payload": payload})
    expected = [
        {"type": "GAME_STARTED", "payload": {}},
        {"type": "TURN_STARTED", "payload": {}},
        {"type": "DICE_ROLLED", "payload": {"d1": 3, "d2": 6, "is_double": False}},
        {"type": "PLAYER_MOVED", "payload": {"from": 0, "to": 9, "passed_go": False}},
        {
            "type": "LLM_DECISION_REQUESTED",
            "payload": {"player_id": "p1", "decision_type": "BUY_OR_AUCTION_DECISION"},
        },
        {
            "type": "LLM_DECISION_RESPONSE",
            "payload": {"player_id": "p1", "action_name": "buy_property", "valid": True, "error": None},
        },
        {"type": "PROPERTY_PURCHASED", "payload": {"player_id": "p1", "space_index": 9, "price": 120}},
        {"type": "CASH_CHANGED", "payload": {"player_id": "p1", "delta": -120, "reason": "buy_property"}},
        {
            "type": "LLM_DECISION_REQUESTED",
            "payload": {"player_id": "p1", "decision_type": "POST_TURN_ACTION_DECISION"},
        },
        {
            "type": "LLM_DECISION_RESPONSE",
            "payload": {"player_id": "p1", "action_name": "end_turn", "valid": True, "error": None},
        },
        {"type": "TURN_ENDED", "payload": {}},
        {"type": "TURN_STARTED", "payload": {}},
        {"type": "DICE_ROLLED", "payload": {"d1": 4, "d2": 1, "is_double": False}},
        {"type": "PLAYER_MOVED", "payload": {"from": 0, "to": 5, "passed_go": False}},
    ]
    assert stripped == expected
