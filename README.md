# MONOPOLY LLM BENCHMARK

A full Monopoly implementation where multiple LLMs compete against each other under strict official rules. The system is designed to be:
1. A polished, real-time visual showcase
2. A repeatable benchmark for model strategy and decision quality
3. A research-ready data collection system with detailed logs and metrics

## Table of contents
1. [Core ideas](#core-ideas)
2. [Tech stack](#tech-stack)
3. [Quickstart (Windows)](#quickstart-windows)
4. [Health check](#health-check)
5. [Verification](#verification)
6. [WebSocket](#websocket)
7. [Configuration](#configuration)
8. [How gameplay works (high-level)](#how-gameplay-works-high-level)
9. [Run outputs and dataset format](#run-outputs-and-dataset-format)
10. [Benchmarking goals](#benchmarking-goals)
11. [Repo layout](#repo-layout)
12. [Development rules](#development-rules)
13. [Contributing](#contributing)
14. [License](#license)

## Core ideas
1. The Monopoly engine is deterministic and authoritative.
2. LLMs do not change state; they only choose from legal moves at decision points.
3. Every state change emits an event, enabling replay, debugging, and analysis.
4. The UI is fully custom-coded (no board image dependency). It renders board, tokens, houses/hotels, ownership, mortgages, and an event feed plus inspector.

## Tech stack
- Frontend: React + Vite + TypeScript
- Backend: Python + uv + FastAPI + WebSocket
- Engine: Python (deterministic rules engine)
- LLM: OpenRouter only
- Storage: local runs folder (no database yet)

## Quickstart (Windows)
### Prerequisites
1. Node installed
2. Yarn enabled via Corepack
3. Python available via uv (pinned by `.python-version`)

### Frontend
```
cd frontend
yarn
yarn dev
```
Expected: app served at `http://localhost:5173`.

### Backend
```
cd python
uv sync --all-packages
cd apps/api
uv run uvicorn monopoly_api.main:app --reload
```
Expected: API served at `http://127.0.0.1:8000`.

### Headless (no UI)
```bash
python -m monopoly_arena.run --seed 123 --max-turns 20
```

## Health check
Open `http://127.0.0.1:8000/health` and confirm `ok true`.

## Verification
Run the full repo verification suite (contracts + Python tests + frontend build) from repo root:
```
pwsh -File scripts/verify.ps1
```
On macOS/Linux:
```
./scripts/verify.sh
```

## WebSocket
Backend provides a WebSocket endpoint at `/ws`. Frontend connects to it for real-time events and state snapshots.

## Configuration
Env files are loaded in this priority order (later overrides earlier, but OS env always wins):
1) repo root `.env`
2) `python/.env`
3) `python/apps/api/.env`

### Required
- `OPENROUTER_API_KEY`

### Optional
- `OPENROUTER_MODEL`
- `OPENROUTER_SYSTEM_PROMPT`
- `PLAYERS_CONFIG_PATH` (defaults to `python/apps/api/src/monopoly_api/config/players.json`)
- `RUNS_DIR`

## How gameplay works (high-level)
1. Engine advances automatically through deterministic steps (dice roll, movement resolution, rent, card effects).
2. When a decision is required, engine emits a decision point with `legal_actions`.
3. Arena asks the model to select a legal action via tool calling.
4. Output is validated strictly. One retry is allowed. If invalid again, a deterministic fallback is applied.
5. Engine applies the chosen action and emits events.
6. Backend streams events and periodic snapshots to the UI.
7. Telemetry writes everything locally for benchmarking and research.

## Run outputs and dataset format
Each run creates a folder under `runs/RUN_ID/`.
- `events.jsonl`: canonical append-only event stream
- `decisions.jsonl`: append-only log with `phase` entries (`decision_started`, `decision_resolved`) per decision, including epoch-ms timing fields (`request_start_ms`, `response_end_ms`, `latency_ms`), prompts, model outputs, tool calls, validation results, and retries
- `prompts/`: per-decision prompt/response artifacts for inspection (`decision_<id>_*.{json,txt}`)
- state snapshots: full snapshots under `state/` (`turn_XXXX.json` is never overwritten; decision-time snapshots also write `turn_XXXX_decision_*.json`)
- `summary.json`: winner, turns, bankruptcies, cost estimates, key metrics

## Player model configuration
Default player models live in `python/apps/api/src/monopoly_api/config/players.json`. Exactly 4 players are required for LLM runs; `/run/start` requests must include 4 players if provided, and overrides only apply by `player_id` from that file. Each entry can include `openrouter_model_id` and `system_prompt`.

## Benchmarking goals
1. Compare win rate across models and prompts under identical seeds and settings
2. Characterize strategy: property preferences, building behavior, trading frequency, risk, jail decisions
3. Build artifacts: landing heatmaps, rent extraction curves, trade graphs, bankruptcy causes

## Repo layout
- `frontend`: UI
- `python/apps/api`: server + realtime
- `python/packages/monopoly_engine`: rules engine
- `python/packages/monopoly_arena`: OpenRouter orchestration + prompts
- `python/packages/monopoly_telemetry`: logging + metrics

## Development rules
See `AGENTS.md`. It defines how to work in this repo, how to keep determinism, how to evolve contracts, and how to enforce strict legal play.

## Contributing
1. Keep changes focused and easy to review.
2. Add tests for engine behavior and edge cases.
3. Update protocol contracts when you change events/actions/snapshots.
4. Do not commit secrets.

## License
This repository is open source. See `LICENSE`.
