# AGENTS

Single source of truth for how coding agents and humans should work in this repo. Optimized for long autonomous coding sessions and for producing benchmark-quality, reproducible results.

## Table of contents
1. [Purpose](#purpose)
2. [High-level mission](#high-level-mission)
3. [Non-negotiable invariants](#non-negotiable-invariants)
4. [Directory map and responsibilities](#directory-map-and-responsibilities)
5. [Core protocol objects (must stay consistent)](#core-protocol-objects-must-stay-consistent)
6. [LLM control policy (strict enforcement)](#llm-control-policy-strict-enforcement)
7. [Reasoning and thinking models](#reasoning-and-thinking-models)
8. [Performance and token discipline](#performance-and-token-discipline)
9. [How to run (developer commands)](#how-to-run-developer-commands)
10. [Testing](#testing)
11. [Lint and typecheck (preferred)](#lint-and-typecheck-preferred)
12. [Run logging and dataset output](#run-logging-and-dataset-output)
13. [Feature development workflow (mandatory)](#feature-development-workflow-mandatory)
14. [Testing requirements (minimum bar)](#testing-requirements-minimum-bar)
15. [Git and review expectations](#git-and-review-expectations)
16. [Boundaries and forbidden shortcuts](#boundaries-and-forbidden-shortcuts)
17. [If anything is ambiguous](#if-anything-is-ambiguous)

## Purpose
This file defines the single source of truth for how coding agents and humans should work in this repo. It is optimized for long autonomous coding sessions and for producing benchmark-quality, reproducible results.

## High-level mission
1. Build a polished, real-time Monopoly game UI where multiple LLMs compete.
2. Build a strict Monopoly benchmark harness that measures how well models play, with reproducibility and rich telemetry.
3. Produce research-grade logs and artifacts that can support analysis and a paper.

## Non-negotiable invariants
1. The game engine is authoritative. Only the engine mutates game state.
2. Determinism is mandatory. Given the same seed and the same action selections, the game must replay identically.
3. UI must not infer game outcomes. UI renders from state snapshots and event stream only.
4. LLMs may only act via explicit legal actions provided by the engine.
5. All state changes must produce an event. There are no silent mutations.
6. OpenRouter is the only LLM gateway. No direct vendor APIs.

## Directory map and responsibilities
1. `frontend`
   - Custom-built React UI. Renders board, tokens, houses/hotels, ownership, mortgages, jail status, and an event feed + inspector.
2. `python/packages/monopoly_engine`
   - Pure rules engine, deterministic RNG, legality generation, and event emission. No OpenRouter, no web server code.
3. `python/packages/monopoly_arena`
   - LLM orchestration: OpenRouter client, prompt builder (holistic context), tool call parsing, retry policy, fallback policy, and decision logging.
4. `python/packages/monopoly_telemetry`
   - Local run folder management, jsonl writers, snapshot writers, metrics computation, exporters.
5. `python/apps/api`
   - FastAPI + WebSocket. Runs games, streams events/snapshots to UI, manages run lifecycle.

## Core protocol objects (must stay consistent)
1. State snapshot
   - A full, holistic view of the entire game: all players, all properties, bank inventory, decks state (as allowed), open trades, active auctions, and derived metrics if needed. Sent periodically to clients for resync.
2. Event
   - Append-only, strictly ordered. Every event has sequence number, turn index, actor, type, and payload. Events drive the UI feed and animations and support replay.
3. Decision point
   - Produced by the engine whenever an LLM must choose. Includes `legal_actions` list that fully enumerates the only allowed tools and argument shapes.
4. Action (tool call)
   - Structured object chosen by an LLM that must match schema and must be one of `legal_actions` exactly.

## LLM control policy (strict enforcement)
1. For each decision point, the LLM receives:
   1. Full state snapshot (holistic game view).
   2. Short textual summary of relevant situational factors.
   3. Explicit `legal_actions` menu (the only allowed tool calls).
   4. Rules snippet relevant to the decision type (only what is necessary).
2. The LLM must respond via tool call selection only.
3. If the LLM output is invalid JSON, invalid schema, or not a legal action:
   1. Send exactly one corrective retry request with the validation error and the `legal_actions` menu repeated.
   2. If still invalid, apply a deterministic fallback action and record a strike.
4. LLM may include optional fields:
   - `public_message`: shown to everyone in UI feed.
   - `private_thought`: stored and visible only in inspector; never shown publicly unless explicitly enabled.

## Reasoning and thinking models
1. When the model provides reasoning or thinking traces, store them and make them inspectable in the UI.
2. Reasoning should be treated as optional; absence is normal for some models.
3. Reasoning must never be required for correctness; tool call selection must be sufficient.

## Performance and token discipline
1. Always send full state snapshot as structured JSON, but keep it compact and stable.
2. Prefer stable IDs instead of repeated long strings.
3. For long histories, provide:
   1. last N events (small)
   2. rolling summary maintained by server (short)
4. Never paste an entire rulebook. Include only decision-relevant rules.

## How to run (developer commands)
### Frontend
```
cd frontend
yarn
yarn dev
```

### Backend
```
cd python
uv sync --all-packages
cd apps/api
uv run uvicorn monopoly_api.main:app --reload
```

## Testing
### Engine
```
cd python/packages/engine
uv run pytest
```

### Arena
```
cd python/packages/arena
uv run pytest
```

### Telemetry
```
cd python/packages/telemetry
uv run pytest
```

## Lint and typecheck (preferred)
```
uv run ruff check .
uv run mypy .
```

## Run logging and dataset output
1. Every run writes to `runs/RUN_ID/`.
2. Required artifacts:
   - `events.jsonl`: canonical event log.
   - `decisions.jsonl`: decision contexts + tool calls + validation + retries + timing.
   - state snapshots: periodic full snapshots for replay resync.
   - `summary.json`: winner, turn count, bankruptcies, costs, key stats.

## Feature development workflow (mandatory)
1. Start by updating contracts first whenever a protocol changes:
   - schemas for events, actions, decision points, and state snapshots.
2. Implement engine support with unit tests.
3. Implement backend streaming changes.
4. Implement frontend rendering for new event types and state fields.
5. Add or update telemetry for the new data.
6. Confirm replay still works deterministically.

## Testing requirements (minimum bar)
1. Engine must have unit tests for all edge cases:
   - jail, doubles, auctions, mortgages, building rules, bankruptcy, chance/community cards.
2. Add deterministic golden-seed tests:
   - the same seed must produce identical event streams.
3. Add invariants checks:
   - cash never becomes NaN.
   - bank inventory never negative.
   - houses/hotels respect limits.
   - ownership is consistent.
   - bankruptcy transitions are valid.

## Git and review expectations
1. Prefer small changesets with clear commit messages.
2. Every commit must keep the project runnable locally.
3. Never commit secrets. Use `.env` and `.env.example`.

## Boundaries and forbidden shortcuts
1. Do not implement rules in the UI.
2. Do not allow free-form actions from LLMs.
3. Do not add house rules unless explicitly specified and documented.
4. Do not change event meanings without bumping schema and updating both frontend and backend.

## If anything is ambiguous
Prefer the strictest interpretation that preserves determinism, legality, and replay correctness. Document the choice.
