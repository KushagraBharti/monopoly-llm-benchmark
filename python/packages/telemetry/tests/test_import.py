"""Smoke tests for monopoly_telemetry module."""
import monopoly_telemetry


def test_import_monopoly_telemetry() -> None:
    """Verify monopoly_telemetry can be imported."""
    assert monopoly_telemetry is not None


def test_hello_function() -> None:
    """Verify hello function returns correct string."""
    assert monopoly_telemetry.hello() == "Hello from monopoly_telemetry!"
