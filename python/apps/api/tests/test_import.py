"""Smoke tests for api module imports."""
import monopoly_engine
import monopoly_arena
import monopoly_telemetry


def test_import_all_packages() -> None:
    """Verify all monopoly_* packages can be imported from API context."""
    assert monopoly_engine is not None
    assert monopoly_arena is not None
    assert monopoly_telemetry is not None


def test_hello_functions() -> None:
    """Verify all hello functions work."""
    assert "monopoly_engine" in monopoly_engine.hello()
    assert "monopoly_arena" in monopoly_arena.hello()
    assert "monopoly_telemetry" in monopoly_telemetry.hello()
