#!/usr/bin/env bash
# board-guard.sh — PreToolUse guard for the Project Board store + derived dashboard.
#
# Keeps board work fixed and stable by steering all writes through scripts/board.py
# (the only sanctioned writer; see references/project-board-crud.md). Fires on the
# Edit|Write|MultiEdit tools (scope it with that matcher in settings.json).
#
# Profile-aware via $HARNESS_PROFILE:
#   minimal   — disabled; never blocks.
#   standard  — block hand-edits to the DERIVED docs/dashboard.html (always regenerate).
#   strict    — also block hand-edits to the canonical store
#               (docs/backlog/items.jsonl | roadmap.json | inbox.jsonl).
#
# Block mechanism: exit 2 (PreToolUse → tool call denied, stderr returned to the agent).
# Anything it cannot parse → exit 0 (fail open; a guard must never wedge the session).
set -uo pipefail

profile="${HARNESS_PROFILE:-standard}"
[ "$profile" = "minimal" ] && exit 0

input="$(cat 2>/dev/null || true)"
[ -z "$input" ] && exit 0

# Extract the target path from the PreToolUse payload (tool_input.file_path). python3 is a
# harness prerequisite; if it is somehow missing the parse yields "" and we fail open.
path="$(printf '%s' "$input" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
ti = d.get("tool_input") or {}
print(ti.get("file_path") or ti.get("path") or "")
' 2>/dev/null || true)"
[ -z "$path" ] && exit 0

deny() { echo "[board-guard] $1" >&2; exit 2; }

case "$path" in
  */docs/dashboard.html|docs/dashboard.html)
    deny "docs/dashboard.html is DERIVED — never hand-edit it. Change the store via scripts/board.py (add/move/edit/refine/defer/trim/wontfix), then re-render: python3 <project-meta>/scripts/board.py render --root . (see references/project-board-crud.md)."
    ;;
esac

if [ "$profile" = "strict" ]; then
  case "$path" in
    */docs/backlog/items.jsonl|docs/backlog/items.jsonl| \
    */docs/backlog/roadmap.json|docs/backlog/roadmap.json| \
    */docs/backlog/inbox.jsonl|docs/backlog/inbox.jsonl)
      deny "$path is the CLI-managed board store — hand-edits break the lock / items_sha256 / atomic-write invariants. Use scripts/board.py verbs; for unavoidable surgery, edit then run 'board.py tx' to re-hash and validate."
      ;;
  esac
fi

exit 0
