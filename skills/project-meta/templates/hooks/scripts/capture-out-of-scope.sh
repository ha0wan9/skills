#!/usr/bin/env bash
# capture-out-of-scope.sh — DASH-02 autonomous out-of-scope capture (DRY-RUN FIRST).
#
# A `SessionEnd` command hook that records a *candidate* when a session likely surfaced a
# feature/bug outside the session's scope. It is deliberately conservative:
#
#   BOARD_CAPTURE_MODE=dryrun  (DEFAULT) — append a candidate marker to a dry-run log ONLY.
#                              Never calls a model, never writes items.jsonl / roadmap.json /
#                              inbox.jsonl. This is the only shipped mode.
#   BOARD_CAPTURE_MODE=append  (OPT-IN, not yet implemented) — would classify the session via
#                              `claude -p --model sonnet` and atomically append a fuzzy row to
#                              inbox.jsonl (never the canonical store). Gated behind observed
#                              false-positive rate + an approval story (see references).
#
# Safety invariants (DASH-02 / DASH-24):
#   - Profile-gated: HARNESS_PROFILE=minimal disables it entirely.
#   - Never touches items.jsonl / roadmap.json. At most it appends to inbox.jsonl (append mode).
#   - Always exits 0 — a capture hook must never fail a session.
set -uo pipefail

profile="${HARNESS_PROFILE:-standard}"
[ "$profile" = "minimal" ] && exit 0

mode="${BOARD_CAPTURE_MODE:-dryrun}"
root="${BOARD_ROOT:-.}"
log="${root}/docs/backlog/.capture-dryrun.log"
mkdir -p "$(dirname "$log")" 2>/dev/null || exit 0

# Drain hook stdin if present (Claude Code passes hook JSON on stdin); we do not parse it in
# dry-run mode — classification is the append-mode model step, intentionally not shipped yet.
input="$(cat 2>/dev/null || true)"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"

case "$mode" in
  dryrun)
    printf '%s\tdryrun\tcandidate-capture (no model call; store untouched); chars=%s\n' \
      "$ts" "${#input}" >> "$log"
    exit 0
    ;;
  append)
    if ! command -v claude >/dev/null 2>&1; then
      printf '%s\tappend\tskipped: claude CLI not found\n' "$ts" >> "$log"
      exit 0
    fi
    # OPT-IN, NOT IMPLEMENTED: classify via `claude -p --model sonnet`, then
    #   board.py inbox-add --source capture --title "<classified>" ...
    # Left as a documented scaffold until the approval/false-positive story is settled
    # (docs/backlog/project-board-system.md Open questions). Logs intent, writes nothing.
    printf '%s\tappend\tNOT-IMPLEMENTED: would classify + board.py inbox-add (no write performed)\n' \
      "$ts" >> "$log"
    exit 0
    ;;
  *)
    printf '%s\tunknown-mode\t%s (treated as dryrun)\n' "$ts" "$mode" >> "$log"
    exit 0
    ;;
esac
