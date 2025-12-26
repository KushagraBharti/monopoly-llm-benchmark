MONOPOLY LLM BENCHMARK

What this is
A full Monopoly implementation where multiple LLMs compete against each other under strict official rules. The system is designed to be:
1) A polished, real-time visual showcase
2) A repeatable benchmark for model strategy and decision quality
3) A research-ready data collection system with detailed logs and metrics

Core ideas
1) The Monopoly engine is deterministic and authoritative.
2) LLMs do not change state; they only choose from legal moves at decision points.
3) Every state change emits an event, enabling replay, debugging, and analysis.
4) The UI is fully custom-coded (no board image dependency). It renders board, tokens, houses/hotels, ownership, mortgages, and an event feed plus inspector.

Tech stack
Frontend: React + Vite + TypeScript
Backend: Python + uv + FastAPI + WebSocket
Engine: Python (deterministic rules engine)
LLM: OpenRouter only
Storage: local runs folder (no database yet)

Quickstart (Windows)
Prerequisites
1) Node installed
2) Yarn enabled via Corepack
3) Python available via uv (pinned by .python-version)

Frontend
1) cd frontend
2) yarn
3) yarn dev
Expected: app served at http://localhost:5173

Backend
1) cd python
2) uv sync --all-packages
3) cd apps/api
4) uv run uvicorn main:app --reload
Expected: API served at http://127.0.0.1:8000

Health check
Open http://127.0.0.1:8000/health and confirm ok true.

WebSocket
Backend provides a WebSocket endpoint at /ws. Frontend connects to it for real-time events and state snapshots.

Configuration
Create a .env file in the repo root or in python/apps/api depending on your local setup.
Required
OPENROUTER_API_KEY
Optional
OPENROUTER_MODEL
RUNS_DIR

How gameplay works (high-level)
1) Engine advances automatically through deterministic steps (dice roll, movement resolution, rent, card effects).
2) When a decision is required, engine emits a decision point with legal_actions.
3) Arena asks the model to select a legal action via tool calling.
4) Output is validated strictly. One retry is allowed. If invalid again, a deterministic fallback is applied.
5) Engine applies the chosen action and emits events.
6) Backend streams events and periodic snapshots to the UI.
7) Telemetry writes everything locally for benchmarking and research.

Run outputs and dataset format
Each run creates a folder under runs/RUN_ID/
events.jsonl: canonical append-only event stream
decisions.jsonl: decision inputs, prompts, model outputs, tool calls, validation results, retries, latencies, token usage when available
state snapshots: periodic full snapshots for resync and replay support
summary.json: winner, turns, bankruptcies, cost estimates, key metrics

Benchmarking goals
1) Compare win rate across models and prompts under identical seeds and settings
2) Characterize strategy: property preferences, building behavior, trading frequency, risk, jail decisions
3) Build artifacts: landing heatmaps, rent extraction curves, trade graphs, bankruptcy causes

Repo layout
frontend: UI
python/apps/api: server + realtime
python/packages/monopoly_engine: rules engine
python/packages/monopoly_arena: OpenRouter orchestration + prompts
python/packages/monopoly_telemetry: logging + metrics

Development rules
See AGENTS.md. It defines how to work in this repo, how to keep determinism, how to evolve contracts, and how to enforce strict legal play.

Contributing
1) Keep changes focused and easy to review.
2) Add tests for engine behavior and edge cases.
3) Update protocol contracts when you change events/actions/snapshots.
4) Do not commit secrets.

License
This repository is open source. See LICENSE.
