# Monopoly Arena Frontend

Render-only React UI for the Monopoly LLM benchmark.

## Responsibilities
- Renders the board, tokens, ownership, mortgages, and an event feed + inspector from server-provided snapshots/events.
- Connects to the backend WebSocket at `/ws` and polls `/run/status` for run metadata.
- Must not implement Monopoly rules or infer legality; engine is authoritative.

## Dev
From repo root:

```bash
cd frontend
yarn
yarn dev
```

## Build
```bash
cd frontend
yarn build
```

## Package manager
This repo uses Yarn (Corepack) for the frontend. Do not use npm (`package-lock.json` is intentionally not tracked).
