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
        {"type": "DICE_ROLLED", "payload": {"d1": 1, "d2": 3, "is_double": False}},
        {"type": "PLAYER_MOVED", "payload": {"from": 0, "to": 4, "passed_go": False}},
        {"type": "CASH_CHANGED", "payload": {"player_id": "p1", "delta": -200, "reason": "TAX_INCOME"}},
        {"type": "TURN_ENDED", "payload": {}},
        {"type": "TURN_STARTED", "payload": {}},
        {"type": "DICE_ROLLED", "payload": {"d1": 1, "d2": 4, "is_double": False}},
        {"type": "PLAYER_MOVED", "payload": {"from": 0, "to": 5, "passed_go": False}},
        {
            "type": "LLM_DECISION_REQUESTED",
            "payload": {"player_id": "p2", "decision_type": "BUY_OR_AUCTION_DECISION"},
        },
        {
            "type": "LLM_DECISION_RESPONSE",
            "payload": {"player_id": "p2", "action_name": "buy_property", "valid": True, "error": None},
        },
        {"type": "PROPERTY_PURCHASED", "payload": {"player_id": "p2", "space_index": 5, "price": 200}},
        {"type": "CASH_CHANGED", "payload": {"player_id": "p2", "delta": -200, "reason": "buy_property"}},
        {"type": "TURN_ENDED", "payload": {}},
    ]
    assert stripped == expected
