#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

last_step=""

step() {
  last_step="$1"
  echo ""
  echo "==> $1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

on_error() {
  if [[ -n "$last_step" ]]; then
    echo "" >&2
    echo "Step failed: $last_step" >&2
  fi
}
trap on_error ERR

step "Tooling: verify prerequisites"
require_cmd node
require_cmd uv
require_cmd yarn

step "Contracts: validate examples"
node contracts/validate-contracts.mjs

step "Python: lint (ruff)"
(cd python && uv run ruff check .)

step "Python: typecheck (mypy)"
(cd python && uv run mypy .)

step "Python: engine tests"
(cd python/packages/engine && uv run pytest)

step "Python: API tests"
(cd python/apps/api && uv run pytest)

step "Python: arena tests"
(cd python/packages/arena && uv run pytest)

step "Python: telemetry tests"
(cd python/packages/telemetry && uv run pytest)

step "Frontend: lint"
(cd frontend && yarn lint)

step "Frontend: build"
(cd frontend && yarn build)

echo ""
echo "All checks passed."
