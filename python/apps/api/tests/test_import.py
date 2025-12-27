"""Smoke tests for api module imports."""
import monopoly_engine
import monopoly_arena
import monopoly_telemetry


def test_import_all_packages() -> None:
    """Verify all monopoly_* packages can be imported from API context."""
    assert monopoly_engine is not None
    assert monopoly_arena is not None
    assert monopoly_telemetry is not None


def test_engine_constructor_available() -> None:
    """Verify engine entry points are available."""
    engine = monopoly_engine.Engine(seed=1, players=[{"player_id": "p1", "name": "P1"}], run_id="run")
    snapshot = engine.get_snapshot()
    assert snapshot["run_id"] == "run"
