#!/usr/bin/env bash
# phase-lock gate: review — verifies .harness/last-turn-meta.json exists and
# contains a non-empty review_tier (file-derived; D5 precedent — no ledger query).
set -eu

META_FILE="${HARNESS_LAST_TURN_META_FILE:-.harness/last-turn-meta.json}"

if [ ! -f "$META_FILE" ]; then
  echo "review gate: $META_FILE missing" >&2
  exit 1
fi

python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        meta = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    print(f"review gate: {sys.argv[1]} unreadable: {e}", file=sys.stderr)
    sys.exit(1)
tier = meta.get("review_tier")
if not isinstance(tier, str) or not tier.strip():
    print("review gate: review_tier missing/empty in " + sys.argv[1], file=sys.stderr)
    sys.exit(1)
print(f"review gate: review_tier={tier!r}")
' "$META_FILE"
