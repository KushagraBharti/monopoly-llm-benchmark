# `monopoly_arena`

LLM orchestration for Monopoly runs (OpenRouter-only).

## Responsibilities
- OpenRouter client and retry/backoff policy.
- Prompt construction from engine decision points + state snapshots.
- Tool schema building, tool-call parsing, and strict action validation.
- Deterministic fallback policy when the model output is invalid.

## Public API
- `monopoly_arena.OpenRouterClient`
- `monopoly_arena.OpenRouterResult`
- `monopoly_arena.LlmRunner`

## Headless run
```bash
python -m monopoly_arena.run --seed 123 --max-turns 20
```

## Tests
```bash
cd python/packages/arena
uv run pytest
```
