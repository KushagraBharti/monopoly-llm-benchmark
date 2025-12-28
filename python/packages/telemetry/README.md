# `monopoly_telemetry`

Run artifact writer utilities.

## Responsibilities
- Creates a run folder under `runs/<run_id>/`.
- Writes:
  - `events.jsonl`: canonical event log
  - `decisions.jsonl`: decision log (started/resolved phases, retries/fallbacks, timing)
  - `state/turn_XXXX.json`: periodic full state snapshots
  - `prompts/decision_<id>_*.{json,txt}`: per-decision prompt/response artifacts
  - `summary.json`: end-of-run summary

## Public API
- `monopoly_telemetry.RunFiles`
- `monopoly_telemetry.init_run_files`
- `monopoly_telemetry.append_jsonl`

## Tests
```bash
cd python/packages/telemetry
uv run pytest
```
