CONTRACTS QUICK COMMANDS

Run validation (from repo root)
1) node contracts/validate-contracts.mjs

If validation dependencies are missing, install them with one of:
- yarn
- cd frontend && yarn

Update workflow (schemas + types stay in sync)
1) Edit JSON Schemas in contracts/schemas (versioned; update schema_version when you introduce a breaking change).
2) Update TypeScript types in contracts/ts to mirror the schema changes.
3) Update or add examples in contracts/examples to cover the new fields or variants.
4) Re-run validation: node contracts/validate-contracts.mjs

How contracts relate to the system
- Engine emits state snapshots, decision points, and core game events that must conform to contracts/schemas.
- Arena reads decision points, selects legal actions, and emits LLM meta events that must also conform.
- Backend streams events and snapshots to the UI and writes logs; it must not mutate schema fields.
- Frontend consumes the event and state streams using contracts/ts types for rendering and UI logic.
