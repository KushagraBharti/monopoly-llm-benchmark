"""Smoke tests for monopoly_engine module."""
import monopoly_engine


def test_import_monopoly_engine() -> None:
    """Verify monopoly_engine can be imported."""
    assert monopoly_engine is not None


def test_hello_function() -> None:
    """Verify hello function returns correct string."""
    assert monopoly_engine.hello() == "Hello from monopoly_engine!"
