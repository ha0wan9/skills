#!/usr/bin/env bash
# phase-lock gate: plan — verifies .harness/phase-state.json names a build_plan
# path (optional field, written at plan entry) and that the named file exists.
set -eu

STATE_FILE="${HARNESS_STATE_FILE:-.harness/phase-state.json}"

if [ ! -f "$STATE_FILE" ]; then
  echo "plan gate: state file missing at $STATE_FILE" >&2
  exit 1
fi

BUILD_PLAN="$(python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        state = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    print(f"plan gate: state file unreadable: {e}", file=sys.stderr)
    sys.exit(1)
bp = state.get("build_plan")
if not bp:
    sys.exit(1)
print(bp)
' "$STATE_FILE" 2>/dev/null)" || {
  echo "plan gate: build_plan field unset/missing in $STATE_FILE" >&2
  exit 1
}

if [ -z "$BUILD_PLAN" ]; then
  echo "plan gate: build_plan field unset/missing in $STATE_FILE" >&2
  exit 1
fi

if [ ! -f "$BUILD_PLAN" ]; then
  echo "plan gate: build_plan path '$BUILD_PLAN' does not exist" >&2
  exit 1
fi

echo "plan gate: build_plan '$BUILD_PLAN' present"
exit 0
