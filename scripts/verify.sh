#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

step() {
  echo ""
  echo "==> $1"
}

step "Contracts: validate examples"
node contracts/validate-contracts.mjs

step "Python: engine tests"
(cd python/packages/engine && uv run pytest)

step "Python: API tests"
(cd python/apps/api && uv run pytest)

step "Python: arena tests"
(cd python/packages/arena && uv run pytest)

step "Frontend: build"
(cd frontend && yarn build)

echo ""
echo "All checks passed."

