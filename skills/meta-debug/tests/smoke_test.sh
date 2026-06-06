#!/usr/bin/env bash
# smoke_test.sh — non-interactive smoke test for debug_session.py
# Runs `show` and `list` against the example state in examples/null-deref-cache/
# using --state-dir so it never touches project-scoped state.
# Exits 0 on success, non-zero on any failure.

set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DBG="$SKILL_ROOT/scripts/debug_session.py"
STATE_DIR="$SKILL_ROOT/examples/null-deref-cache/state"
SESSION_ID="dbg-20260603T165614Z"

echo "[smoke] testing debug_session.py show ..."
python3 "$DBG" show "$SESSION_ID" --state-dir "$STATE_DIR"

echo "[smoke] testing debug_session.py list ..."
python3 "$DBG" list --state-dir "$STATE_DIR"

echo "[smoke] all checks passed."
