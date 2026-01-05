# MonopolyBench

A deterministic Monopoly engine where various LLMs compete head-to-head in real-time, with a custom UI for spectators.

This repository is meant to serve three purposes:
1. **Live demo** - A real-time UI for watching LLMs play Monopoly.
2. **Benchmark** - A reproducible benchmark for testing LLMs on Monopoly.
3. **Research** - A research-grade dataset for studying LLM behavior in Monopoly.

![MonopolyBench](https://github.com/KushagraBharti/MonopolyBench/main/MonopolyBench.png?raw=true)

The goal is to test LLMs on 
1) **Raw Monopoly Performance** - Which LLM is the best at playing Monopoly?
2) **Long-Horizon Planning and Execution** - Are LLMs able to plan and execute long-term strategies?
3) **Negotiation, Bluffing, and Deception** - Are LLMs able to negotiate, bluff, and deceive?
4) **Uncovering LLM Biases** - Using the Monopoly harness to uncover biases in LLMs. Using biases from Thinking, Fast, and Slow by Daniel Kahneman

I plan to publish a paper in correlation to this project as well.

Future Implementations: 
1. **TrueSkill** - A TrueSkill ranking system for LLMs playing Monopoly.
2. **Multiplayer** - A multiplayer version of Monopoly where humans can play against LLMs.
3. **Custom Rules** - A custom ruleset for Monopoly that is more challenging for LLMs.

---

## What you can do

- Start a 4-player game where each player is an LLM (via OpenRouter).
- Watch the game live in a custom React UI fed by a FastAPI WebSocket.
- Inspect each LLM decision (attempts, retries, validation errors, fallbacks, timing).
- Run headless single games or batches for benchmarking.

---

## Core principles

These are enforced in code and should stay true as the project evolves:

1. **Engine is authoritative**: only the rules engine mutates game state.
2. **Determinism is mandatory**: given the same seed and action selections, the event stream must replay identically.
3. **LLMs can only select legal actions**: each decision point includes an explicit `legal_actions` menu; no free-form actions.
4. **Every state change emits an event**: there are no silent mutations.
5. **UI is render-only**: it renders from snapshots/events; it does not implement rules.

For development and change-management rules, see `AGENTS.md`.

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

## License

This project is licensed under the Apache License 2.0. See Details at [LICENSE](LICENSE)

## Citation

If you use MonopolyBench in academic work, please cite:

Kushagra Bharti. *MonopolyBench: A Multi-Agent LLM Benchmark for Monopoly.*  
GitHub repository, 2026.

A BibTeX entry is available via [CITATION.cff](CITATION.cff)