from monopoly_api.action_validation import validate_action_payload


def test_action_validation_rejects_string_space_index() -> None:
    action = {
        "schema_version": "v1",
        "decision_id": "dec-1",
        "action": "buy_property",
        "args": {"space_index": "5"},
    }
    ok, errors = validate_action_payload(action)
    assert ok is False
    assert errors


def test_action_validation_rejects_null_public_message() -> None:
    action = {
        "schema_version": "v1",
        "decision_id": "dec-2",
        "action": "start_auction",
        "args": {},
        "public_message": None,
    }
    ok, errors = validate_action_payload(action)
    assert ok is False
    assert errors


def test_action_validation_rejects_additional_properties() -> None:
    action = {
        "schema_version": "v1",
        "decision_id": "dec-4",
        "action": "buy_property",
        "args": {},
        "extra": "nope",
    }
    ok, errors = validate_action_payload(action)
    assert ok is False
    assert errors


def test_action_validation_rejects_invalid_action_name() -> None:
    action = {
        "schema_version": "v1",
        "decision_id": "dec-5",
        "action": "HACK_ACTION",
        "args": {},
    }
    ok, errors = validate_action_payload(action)
    assert ok is False
    assert errors


def test_action_validation_accepts_valid_action() -> None:
    action = {
        "schema_version": "v1",
        "decision_id": "dec-3",
        "action": "start_auction",
        "args": {},
    }
    ok, errors = validate_action_payload(action)
    assert ok is True
    assert errors == []
