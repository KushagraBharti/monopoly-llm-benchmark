from __future__ import annotations

import time
from typing import Any


def make_hello(run_id: str | None) -> dict[str, Any]:
    return {
        "type": "HELLO",
        "payload": {
            "schema_version": "v1",
            "server_time_ms": int(time.time() * 1000),
            "run_id": run_id,
        },
    }


def make_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"type": "SNAPSHOT", "payload": snapshot}


def make_event(event: dict[str, Any]) -> dict[str, Any]:
    return {"type": "EVENT", "payload": event}


def make_error(message: str, details: Any | None = None) -> dict[str, Any]:
    return {
        "type": "ERROR",
        "payload": {
            "schema_version": "v1",
            "message": message,
            "details": details,
        },
    }
