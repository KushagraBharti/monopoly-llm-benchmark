import json

from monopoly_telemetry import init_run_files


def test_write_snapshot_does_not_overwrite_turn_file(tmp_path) -> None:
    run_files = init_run_files(tmp_path, "run-snapshots")

    start_turn = {"schema_version": "v1", "run_id": "run-snapshots", "turn_index": 1, "phase": "START_TURN"}
    decision = {"schema_version": "v1", "run_id": "run-snapshots", "turn_index": 1, "phase": "AWAITING_DECISION"}

    canonical_path = run_files.write_snapshot(start_turn)
    assert canonical_path.name == "turn_0001.json"
    assert json.loads(canonical_path.read_text(encoding="utf-8"))["phase"] == "START_TURN"

    variant_path = run_files.write_snapshot(decision)
    assert variant_path.name.startswith("turn_0001_decision_")
    assert variant_path.name.endswith(".json")
    assert json.loads(canonical_path.read_text(encoding="utf-8"))["phase"] == "START_TURN"
    assert json.loads(variant_path.read_text(encoding="utf-8"))["phase"] == "AWAITING_DECISION"

