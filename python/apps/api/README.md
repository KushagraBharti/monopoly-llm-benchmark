# `monopoly_api`

FastAPI + WebSocket server that runs games and streams events/snapshots to the UI.

## Responsibilities
- Starts/stops runs and reports status (`/run/start`, `/run/stop`, `/run/status`).
- WebSocket fanout (`/ws`) for:
  - `HELLO`
  - `SNAPSHOT`
  - `EVENT`
  - `ERROR`
- Wires together engine + arena + telemetry; the API should stay thin.

## Dev
```bash
cd python
uv sync --all-packages
cd apps/api
uv run uvicorn monopoly_api.main:app --reload
```

## Tests
```bash
cd python/apps/api
uv run pytest
```
