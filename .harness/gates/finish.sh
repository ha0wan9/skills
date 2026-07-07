#!/usr/bin/env bash
# phase-lock gate: finish — passes iff `scripts/ship_plugin.sh check-version` exits 0
# (a version bump exists for every changed plugin, or the marketplace version bumped
# for root-only changes, vs BASE_BRANCH).
set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! OUTPUT="$(scripts/ship_plugin.sh check-version 2>&1)"; then
  echo "finish gate: ship_plugin.sh check-version failed:" >&2
  echo "$OUTPUT" | tail -5 >&2
  exit 1
fi

echo "finish gate: ship_plugin.sh check-version passed"
exit 0
