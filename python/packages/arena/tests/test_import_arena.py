"""Smoke tests for monopoly_arena module."""
import monopoly_arena


def test_import_monopoly_arena() -> None:
    """Verify monopoly_arena can be imported."""
    assert monopoly_arena is not None


def test_hello_function() -> None:
    """Verify hello function returns correct string."""
    assert monopoly_arena.hello() == "Hello from monopoly_arena!"
