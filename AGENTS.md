# AGENTS.md

Single source of truth for how humans and coding agents should work in this repository.

This project is simultaneously:
- a deterministic Monopoly implementation (authoritative rules engine),
- a strict LLM orchestration harness (OpenRouter-only, legal-actions-only),
- a real-time UI (render-only),
- and a research-grade logging system (replayable artifacts).

If you change behavior, you are changing a benchmark. Treat changes accordingly.

---

## Mission

1. Build a polished real-time Monopoly game UI where multiple LLMs compete.
2. Build a strict and reproducible benchmark harness (deterministic replay, rich telemetry).
3. Produce research-grade artifacts suitable for analysis and publication.

---

## Non-negotiable invariants

These are invariants. If you violate one, you are breaking the project’s purpose.

1. **Engine is authoritative**: only the engine mutates game state.
2. **Determinism is mandatory**: given the same seed and the same applied actions, a run must replay identically.
3. **UI is render-only**: UI renders from snapshots/events only; no rules or legality inference in the UI.
4. **LLMs are constrained**: LLMs may only act via explicit legal actions emitted by the engine.
5. **No silent mutations**: every state change must emit an event.
6. **OpenRouter is the only LLM gateway**: no direct vendor APIs.

---

## Key definitions (protocol objects)

These objects define the system boundary between engine, arena, API, telemetry, and UI. They must stay consistent.

### State snapshot
The authoritative current game state serialized as JSON.
- Produced by the engine.
- Streamed to UI for resync.
- Written to disk for replay/inspection.

In code:
- Engine snapshot production: `python/packages/engine/src/monopoly_engine/models.py`
- Contract: `contracts/schemas/state.schema.json` and `contracts/ts/state.ts`

### Event
An append-only, strictly ordered log entry representing a state transition (or a major marker like game start/end).
- Every event has a monotonically increasing `seq` and a `turn_index`.
- Events are the canonical replay surface.

In code:
- Engine event emission: `python/packages/engine/src/monopoly_engine/engine.py`
- Contract: `contracts/schemas/event.schema.json` and `contracts/ts/events.ts`

### Decision point (DecisionPoint)
An object produced whenever a player must choose.
- Includes `decision_id`, `decision_type`, `player_id`, full `state`, and `legal_actions`.
- `legal_actions` fully enumerates allowed actions and argument schemas.

In code:
- Engine decisions: `python/packages/engine/src/monopoly_engine/engine.py`
- Contract: `contracts/schemas/decision.schema.json` and `contracts/ts/decisions.ts`

### Action
A structured payload representing the chosen move for a specific decision.
- Must match the action schema.
- Must be one of the engine-provided `legal_actions` for that decision.

In code:
- Arena validation: `python/packages/arena/src/monopoly_arena/action_validation.py`
- Engine validation: `python/packages/engine/src/monopoly_engine/engine.py`
- Contract: `contracts/schemas/action.schema.json` and `contracts/ts/actions.ts`

---

## Directory map and ownership

Each directory has a clear responsibility. Keep boundaries clean.

### `contracts/`
**Owner**: protocol/contracts
- JSON Schemas (`contracts/schemas/`)
- TypeScript types used by the UI (`contracts/ts/`)
- Examples (`contracts/examples/`)
- Board data (`contracts/data/board.json`)

### `python/packages/engine/`
**Owner**: rules + determinism
- Deterministic rules engine, authoritative state, event emission, decision generation.
- Must not make network calls.
- Must not depend on wall-clock time for game progression.

### `python/packages/arena/`
**Owner**: LLM orchestration
- Prompt construction, tool schema building, tool call parsing/validation.
- Retry policy (exactly one corrective retry) and deterministic fallback policy.
- OpenRouter client implementation.

### `python/packages/telemetry/`
**Owner**: artifacts + metrics
- Run directory layout and writers (events/decisions/actions/snapshots/prompts/summary).
- Summary builder derived from logs.

### `python/apps/api/`
**Owner**: server + streaming
- FastAPI endpoints for run lifecycle.
- WebSocket streaming fanout for snapshots/events.
- Should stay “thin”: no rules, minimal logic beyond lifecycle and transport.

### `frontend/`
**Owner**: render-only UI
- Renders board and panels from server-provided snapshots/events.
- Must not implement Monopoly rules or legality.

---

## Determinism & replay policy

### What must be deterministic
Given:
- seed
- initial player identities (player_id + name)
- engine settings that affect progression (e.g., `max_turns`, `allow_extra_turns`, `ts_step_ms`)
- the exact sequence of applied actions (including args)

Then:
- `events.jsonl` must be identical on replay (after canonicalization).

### Allowed nondeterminism (explicitly permitted)
- Wall-clock timestamps used for observability in decision logs (do not gate determinism on these).
- Network timing, OpenRouter latency, UI rendering timing.

### Determinism enforcement rules
- Engine randomness must come only from deterministic RNG seeded at engine init.
- Engine event timestamps must be derived from deterministic counters (not wall clock).
- Replay should be validated by comparing canonicalized events, not by ad-hoc checks.

### Replay requirements
- All benchmark-worthy runs must have `actions.jsonl` sufficient to replay.
- If you add metadata that changes `events.jsonl` (e.g., fallback markers), ensure replay has enough data to reproduce it.

---

## LLM control policy (strict)

This policy exists to make LLM behavior measurable, comparable, and safe.

For each decision point, the arena provides:
1. A compact but authoritative view of game state (“full_state” as structured JSON).
2. A scenario-specific “decision_focus” with only relevant context.
3. The explicit `legal_actions` menu (as OpenRouter tool schema).
4. (Optionally) a short memory window of recent actions and public chat.

Constraints:
- The model must respond with **exactly one tool call**.
- The chosen tool must match a legal action name.
- Arguments must conform to schema.

Invalid output handling:
1. If output is invalid JSON/schema or not legal: send **exactly one** retry request that includes validation errors.
2. If still invalid: apply a deterministic fallback action (and record it clearly).

Optional model fields:
- `public_message`: visible to all players in UI feed.
- `private_thought`: stored in artifacts and viewable in inspector; never shown publicly unless UI explicitly enables it.

---

## Contracts-first workflow

This repo treats protocol shape changes as first-class, multi-layer changes.

### When you change any protocol shape
Examples: new event type, new action, new decision fields, new snapshot fields.

Required steps (do not skip):
1. Update JSON Schema(s) in `contracts/schemas/`.
2. Update TS types in `contracts/ts/` to match.
3. Update or add examples in `contracts/examples/`.
4. Run contract validation: `node contracts/validate-contracts.mjs`.
5. Update engine/arena/api/frontend/telemetry code accordingly.
6. Add/update tests (engine + api) and ensure replay still matches.

### Schema versioning policy
- Current schemas use `schema_version: "v1"`.
- If you introduce a breaking change (meaning changes, removed required fields), bump schema versions and update both producer and consumer.

---

## Run artifacts (what must be written)

Every run writes to `runs/<run_id>/` (or `RUNS_DIR`).

Required artifacts (must remain stable):
- `events.jsonl`: canonical append-only event stream.
- `actions.jsonl`: append-only log of applied actions for replay.
- `decisions.jsonl`: decision contexts, attempts, retries, fallbacks, timing.
- `state/turn_XXXX.json`: canonical per-turn snapshots (never overwritten).
- `prompts/decision_<id>_*.{json,txt}`: per-decision prompt/response artifacts.
- `summary.json`: end-of-run summary derived from logs.

Artifact invariants:
- Never overwrite canonical per-turn snapshots.
- Always include `decision_id` and attempt index in prompt artifact filenames.
- Log enough metadata to debug: validation errors, fallback reason, and emitted event ranges.

---

## Testing and quality bar

### Minimum bar for any behavioral change
- Add/adjust unit tests that cover the change.
- Ensure deterministic replay still holds (at least for representative scenarios).
- Run `scripts/verify.ps1` before merging.

### Focus areas (engine)
The engine must remain correct and deterministic across:
- jail rules and doubles behavior
- auctions
- mortgages and interest
- building rules and bank inventory (houses/hotels)
- bankruptcy handling and asset transfers
- chance/community chest card effects
- trade negotiation sequencing and limits

Tests live under:
- `python/packages/engine/tests/`
- `python/apps/api/tests/`
- `python/packages/arena/tests/`
- `python/packages/telemetry/tests/`

Add golden-seed or replay-based tests when possible (event stream comparisons are stronger than spot checks).

---

## Lint/typecheck

Preferred (from `python/`):
```bash
uv run ruff check .
uv run mypy .
```

Frontend:
- `yarn build` (runs TS build + Vite build)

---

## Developer commands

### Full verification (repo root)
```powershell
pwsh -File scripts/verify.ps1
```

### Frontend
```bash
cd frontend
yarn
yarn dev
```

### Backend
```bash
cd python
uv sync --all-packages
cd apps/api
uv run uvicorn monopoly_api.main:app --reload
```

### Headless runs
```bash
cd python/packages/arena
uv run python -m monopoly_arena.run --seed 123 --max-turns 20
```

### Batch runs
```bash
cd python/packages/arena
uv run python -m monopoly_arena.batch_run --config ../../../batches/batch.example.json
```

---

## Change playbooks

Use these when adding or modifying major capabilities.

### Add a new event type
1. Add the event to `contracts/schemas/event.schema.json` and `contracts/ts/events.ts`.
2. Add an example line to `contracts/examples/event.example.jsonl`.
3. Emit the event in engine (`python/packages/engine/src/monopoly_engine/engine.py`).
4. Update UI renderers/formatters for the event (`frontend/src/domain/monopoly/formatters.ts` and/or feed components).
5. Update telemetry summary if the event affects metrics (`python/packages/telemetry/src/monopoly_telemetry/summary.py`).
6. Add tests validating shape + ordering.

### Add a new action or decision type
1. Update `contracts/schemas/action.schema.json` and/or `contracts/schemas/decision.schema.json` + TS types.
2. Add contract examples for the new variant(s).
3. Engine:
   - include the action in `legal_actions` for the decision type
   - validate args in `_validate_action`
   - apply behavior and emit events
4. Arena:
   - ensure tool schema generation covers args
   - ensure fallback policy handles the new decision/action safely
5. UI:
   - render any new events or new snapshot fields (render-only)
6. Telemetry:
   - include metrics if relevant
7. Add replay test coverage if it can affect event stream determinism.

### Change prompt structure
Treat prompt schema as part of benchmark integrity.
- Keep prompt payload compact, stable, and structured.
- Do not leak hidden state (future deck order, internal RNG state).
- Add tests that assert prompt payload does not contain banned information.

---

## Debugging playbook

### When something “looks wrong”
Use this order:
1. `events.jsonl`: the canonical truth of what happened, in order.
2. `actions.jsonl`: what actions were applied to decisions.
3. `decisions.jsonl`: what the model attempted, validation errors, retry/fallback reason, timing.
4. `prompts/decision_<id>_*`: exact system/user/tools/response/parsed artifacts.
5. `state/turn_XXXX.json`: authoritative snapshots at key points.

### Common failure signatures
- Lots of `fallback_used=true`: OpenRouter errors, schema mismatch, or prompt drift.
- Replay mismatch: missing action metadata, nondeterministic state changes, or modified engine rules.
- UI confusion: missing event formatting or missing decision context rendering (UI should not infer).

---

## Boundaries and forbidden shortcuts

Do not do these, even “just for a demo”:
1. Do not implement rules in the UI.
2. Do not allow free-form actions from LLMs.
3. Do not introduce nondeterministic state changes (wall clock, unordered iteration affecting outcomes, random without seed).
4. Do not change event meaning without updating contracts and all consumers.
5. Do not add house rules unless explicitly documented and versioned.
6. Do not add direct vendor API calls (OpenRouter only).
7. Do not commit secrets (API keys, tokens). Use local `.env` files.
8. Do not switch frontend package managers (use Yarn; avoid npm lockfiles).

---

## Review expectations

- Prefer small, reviewable changes.
- Keep the project runnable at all times.
- Add tests for any behavior change, especially engine changes.
- Never commit secrets; rely on `.env` locally.
- If you touch protocol shapes, update schemas + TS types + examples together.

---

## If anything is ambiguous

Prefer the strictest interpretation that preserves:
1. determinism,
2. legality enforcement,
3. replay correctness,
4. and contract stability.

Document the decision (in the PR description and/or in updated docs/examples) and add a test to lock it in.
