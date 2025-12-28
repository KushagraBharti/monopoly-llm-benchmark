# Python Workspace

This folder is a `uv` workspace containing:
- `packages/engine`: deterministic Monopoly rules engine (authoritative state + events)
- `packages/arena`: LLM orchestration (OpenRouter client, prompting, tool parsing/validation, retry/fallback policy)
- `packages/telemetry`: local run folder + JSONL writers (events/decisions/snapshots/summary)
- `apps/api`: FastAPI + WebSocket server that wires engine + arena + telemetry

## Setup
From `python/`:
```bash
uv sync --all-packages
```

## Tests
From repo root, the canonical verification entrypoint is:
```bash
pwsh -File scripts/verify.ps1
```

Or run per-package:
```bash
cd python/packages/engine && uv run pytest
cd python/packages/arena && uv run pytest
cd python/packages/telemetry && uv run pytest
cd python/apps/api && uv run pytest
```

## Lint / typecheck (preferred)
From `python/`:
```bash
uv run ruff check .
uv run mypy .
```
