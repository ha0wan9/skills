#!/usr/bin/env bash
# phase-lock gate: implement — passes iff `scripts/ship_plugin.sh validate` exits 0.
# validate runs: marketplace.json coherence, version-bump gate (check-version),
# and any plugin-specific dev validators for plugins touched on this branch.
set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! OUTPUT="$(scripts/ship_plugin.sh validate 2>&1)"; then
  echo "implement gate: ship_plugin.sh validate failed:" >&2
  echo "$OUTPUT" | tail -5 >&2
  exit 1
fi

echo "implement gate: ship_plugin.sh validate passed"
exit 0
