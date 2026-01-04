# Monopoly LLM Benchmark

A deterministic Monopoly rules engine plus a benchmark harness and a real-time UI for running **multi-agent LLM Monopoly matches** under strict legality constraints.

This repo is built for three things at once:
1. **A polished live demo** (board + tokens + event feed + inspector).
2. **A reproducible benchmark** (same seed + same actions -> identical replay).
3. **Research-grade artifacts** (events, actions, decisions, prompts, snapshots, summary).

---

## Table of contents
- [What you can do](#what-you-can-do)
- [Core principles](#core-principles)
- [Architecture (one diagram)](#architecture-one-diagram)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [How runs work](#how-runs-work)
- [Run artifacts (dataset format)](#run-artifacts-dataset-format)
- [Replay and determinism](#replay-and-determinism)
- [Contracts (schemas and types)](#contracts-schemas-and-types)
- [Testing, linting, typecheck](#testing-linting-typecheck)
- [Troubleshooting](#troubleshooting)
- [Repo layout](#repo-layout)
- [Contributing](#contributing)
- [License](#license)

---

## What you can do

- Start a 4-player game where each player is an LLM (via OpenRouter).
- Watch the game live in a custom React UI fed by a FastAPI WebSocket.
- Inspect each LLM decision (attempts, retries, validation errors, fallbacks, timing).
- Persist every run to disk in a replayable, analysis-friendly format.
- Run headless single games or batches for benchmarking.

---

## Core principles

These are enforced in code and should stay true as the project evolves:

1. **Engine is authoritative**: only the rules engine mutates game state.
2. **Determinism is mandatory**: given the same seed and action selections, the event stream must replay identically.
3. **LLMs can only select legal actions**: each decision point includes an explicit `legal_actions` menu; no free-form actions.
4. **Every state change emits an event**: there are no silent mutations.
5. **UI is render-only**: it renders from snapshots/events; it does not implement rules.
6. **OpenRouter only**: no direct vendor APIs.

For development and change-management rules, see `AGENTS.md`.

---

## Architecture

```
Frontend (React) <---- WS: HELLO / SNAPSHOT / EVENT --------> API (FastAPI)
     |                                                          | owns RunManager
     v                                                          v
Inspector UI <----- reads decisions + prompt artifacts -----> Arena (LlmRunner)
                                                                |
                                                                v
                                              OpenRouter (chat.completions + tools)
                                                                |
                                                                v
                                                      Engine (deterministic)
                                                                |
                                                                v
                                                Telemetry writer (runs/<run_id>/)
```

---

## Repo layout

- `contracts/`: schemas + TS types + examples + board spec
- `frontend/`: render-only UI (React/Vite)
- `python/packages/engine`: deterministic Monopoly rules engine
- `python/packages/arena`: OpenRouter orchestration + prompting + strict validation + retries/fallbacks
- `python/packages/telemetry`: run folder management + writers + summary builder
- `python/apps/api`: FastAPI + WebSocket server
- `scripts/`: verification scripts
- `runs/`: output artifacts (generated)

---

## Quickstart

### Prerequisites
- Node.js (for the frontend)
- Yarn via Corepack (recommended): `corepack enable`
- Python via `uv` (workspace is under `python/`)
- OpenRouter API key

### 1) Configure environment
Env files are loaded in this priority order (later overrides earlier; OS env wins):
1. repo root `.env`
2. `python/.env`
3. `python/apps/api/.env`

Minimal `.env` (repo root):
```bash
OPENROUTER_API_KEY=...
```

### 2) Install dependencies

I recommend using `uv` for Python and `yarn` for the frontend.
I also recommend using a Python virtual environment.

Frontend:
```bash
cd frontend
yarn
```

Notes:
- This repo uses Yarn for the frontend. Avoid npm; `package-lock.json` is intentionally not tracked.

Python (from repo root):
```bash
cd python
uv sync --all-packages
```

### 3) Run verification (recommended before pushing)
From repo root:
```powershell
pwsh -File scripts/verify.ps1
```
On macOS/Linux:
```bash
./scripts/verify.sh
```

Verification includes:
- contract example validation
- Python tests (engine + api + arena)
- frontend build

### 4) Run the backend
```bash
cd python/apps/api
uv run uvicorn monopoly_api.main:app --reload
```

Health check: open `http://127.0.0.1:8000/health` and expect `{"ok": true}`.

### 5) Run the frontend
```bash
cd frontend
yarn dev
```

Open `http://localhost:5173`.

---

## Configuration

### Required
- `OPENROUTER_API_KEY`

### Player configuration
Default player configuration lives at:
- `python/apps/api/src/monopoly_api/config/players.json`

Rules:
- Exactly **4** players are required for LLM runs.
- `/run/start` may provide overrides, but overrides must match `player_id`s from the file.
- Per-player `reasoning.effort` (one of `low|medium|high`) is supported and passed through to OpenRouter.

---

## How runs work

At runtime, the system loops like this:

1. The engine advances deterministically (dice -> movement -> forced payments -> cards).
2. When a decision is needed, the engine emits a **DecisionPoint** containing:
   - `decision_id`, `decision_type`, `player_id`
   - a full **StateSnapshot**
   - an explicit `legal_actions` list with argument schemas
3. The arena builds an OpenRouter tool schema from `legal_actions` and asks the model to choose.
4. The model output is validated strictly:
   - invalid tool call / invalid schema / illegal action -> **one retry**
   - still invalid -> deterministic fallback action (recorded)
5. The engine applies the action and emits events (including LLM meta events).
6. The API streams events + snapshots to the UI over WebSocket.
7. Telemetry writes artifacts to `runs/<run_id>/` for later inspection and replay.

---

## Repo layout

- `contracts/`: schemas + TS types + examples + board spec
- `frontend/`: render-only UI (React/Vite)
- `python/packages/engine`: deterministic Monopoly rules engine
- `python/packages/arena`: OpenRouter orchestration + prompting + strict validation + retries/fallbacks
- `python/packages/telemetry`: run folder management + writers + summary builder
- `python/apps/api`: FastAPI + WebSocket server
- `scripts/`: verification scripts
- `runs/`: output artifacts (generated)

## Contracts (schemas and types)

The repo maintains a shared contract boundary:
- JSON Schemas: `contracts/schemas/*.schema.json`
- TypeScript types: `contracts/ts/*.ts`
- Example payloads: `contracts/examples/*`
- Board spec: `contracts/data/board.json`

Validation entrypoint:
```bash
node contracts/validate-contracts.mjs
```

If you change any protocol shape, update:
1. JSON schema(s)
2. TS types
3. examples
4. validation + tests

---

## Testing, linting, typecheck

Canonical repo-wide check:
- `pwsh -File scripts/verify.ps1`

Per-package tests:
```bash
cd python/packages/engine && uv run pytest
cd python/packages/arena && uv run pytest
cd python/apps/api && uv run pytest
cd python/packages/telemetry && uv run pytest
```

Lint / typecheck (preferred):
```bash
cd python
uv run ruff check .
uv run mypy .
```

## License

This project is licensed under the Apache License 2.0. See Details at [LICENSE](LICENSE)

## Citation

If you use MonopolyBench in academic work, please cite:

Kushagra Bharti. *MonopolyBench: A Multi-Agent LLM Benchmark for Monopoly.*  
GitHub repository, 2026.

A BibTeX entry is available via [CITATION.cff](CITATION.cff)