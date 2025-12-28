# `monopoly_engine`

Deterministic, authoritative Monopoly rules engine.

## Responsibilities
- Owns and mutates all game state.
- Produces a strictly ordered event stream (no silent mutations).
- Produces decision points with an explicit `legal_actions` menu and args schema.
- Must remain deterministic: same seed + same action choices => identical replay.

## Public API
- `monopoly_engine.Engine`: main engine class (`advance_until_decision`, `apply_action`, `get_snapshot`)
- `monopoly_engine.create_initial_state`: builds a `GameState` (used by tests/mocks)

## Invariants
- No network calls.
- No wall-clock time for game progression (timestamps are derived from deterministic counters).
- Randomness comes only from `DeterministicRng`.

## Tests
```bash
cd python/packages/engine
uv run pytest
```
