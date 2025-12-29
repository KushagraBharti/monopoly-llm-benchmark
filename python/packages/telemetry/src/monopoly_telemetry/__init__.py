from .run_files import RunFiles, init_run_files
from .summary import build_summary
from .writer_jsonl import append_jsonl


def hello() -> str:
    return "Hello from monopoly_telemetry!"


__all__ = ["RunFiles", "append_jsonl", "hello", "init_run_files", "build_summary"]
