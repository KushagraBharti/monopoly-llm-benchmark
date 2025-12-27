"""Smoke tests for monopoly_engine module."""
from monopoly_engine import Engine


def test_import_monopoly_engine() -> None:
    """Verify monopoly_engine can be imported."""
    players = [{"player_id": "p1", "name": "P1"}]
    engine = Engine(seed=1, players=players, run_id="run-test", max_turns=1)
    assert engine.get_snapshot()["run_id"] == "run-test"
