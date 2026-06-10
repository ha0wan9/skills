#!/usr/bin/env bash
# Stop hook: run repo-defined verification before the agent ends a turn.
#
# Two responsibilities:
#   1. Phase-lock check (when phase-lock contract installed) — verify the
#      current phase's gate has passed at least once since started_utc.
#   2. Project verifier — run the project's own verification command if
#      .harness/verify.sh exists.
#
# Profile-aware via $HARNESS_PROFILE:
#   minimal   — disabled; never run
#   standard  — run checks; warn on failure but exit 0 (advisory)
#   strict    — run checks; exit non-zero on failure (blocks the turn)
#
# Phase-lock check is skipped when no .harness/phase-state.json exists,
# letting repos opt out without uninstalling the hook.

set -euo pipefail

PROFILE="${HARNESS_PROFILE:-standard}"
[[ "$PROFILE" == "minimal" ]] && exit 0

advisory_exit() {
  # Standard profile: warn on stderr, exit 0 so the agent can still close
  # the turn. Strict profile: exit non-zero to block.
  local msg=$1
  echo "[harness] $msg" >&2
  if [[ "$PROFILE" == "strict" ]]; then
    exit 1
  fi
  exit 0
}

# Resolve project-meta's install dir containing the sentinel script $1. Probes:
# explicit override, personal-skill location, and the two plugin-install layouts
# (marketplace checkout + version cache). Existence-checked on the sentinel, so
# an older installed copy that lacks it is skipped. Echoes the dir, or returns 1.
resolve_project_meta() {
  local sentinel=$1 c
  for c in \
    "${PROJECT_META_DIR:-}" \
    "$HOME/.codex/skills/project-meta" \
    "$HOME/.claude/skills/project-meta" \
    "$HOME"/.codex/plugins/marketplaces/*/skills/project-meta \
    "$HOME"/.codex/plugins/cache/*/*/*/skills/project-meta \
    "$HOME"/.claude/plugins/marketplaces/*/skills/project-meta \
    "$HOME"/.claude/plugins/cache/*/*/*/skills/project-meta ; do
    if [[ -n "$c" && -f "$c/$sentinel" ]]; then printf '%s\n' "$c"; return 0; fi
  done
  return 1
}

# 1) Phase-lock check, if installed.
if [[ -f .harness/phase-state.json ]]; then
  pm_dir="$(resolve_project_meta scripts/phase_lock_check.py)" || pm_dir=""
  pm_check="$pm_dir/scripts/phase_lock_check.py"
  if [[ -x "$pm_check" ]] || [[ -f "$pm_check" ]]; then
    if ! python3 "$pm_check" --harness-dir .harness >/tmp/_pl.out 2>&1; then
      cat /tmp/_pl.out >&2
      rm -f /tmp/_pl.out
      advisory_exit "phase-lock gate failed; see above."
    fi
    rm -f /tmp/_pl.out
  fi
fi

# 2) Project verifier.
if [[ -x .harness/verify.sh ]]; then
  if ! .harness/verify.sh >/tmp/_v.out 2>&1; then
    cat /tmp/_v.out >&2
    rm -f /tmp/_v.out
    advisory_exit "project verification failed; see above."
  fi
  rm -f /tmp/_v.out
fi

# 3) Memory write-back gate. Flags a pending write-back decision when the turn
#    changed substantive files but no memory file was updated. Self-skips when
#    not a git repo, when nothing changed, or when .harness/writeback-ack
#    exists. Delegates to project-meta's repo_memory.py (resolve-don't-vendor).
pm_dir="$(resolve_project_meta scripts/repo_memory.py)" || pm_dir=""
pm_mem="$pm_dir/scripts/repo_memory.py"
if [[ -f "$pm_mem" ]]; then
  if ! python3 "$pm_mem" --target-root . writeback 2>/tmp/_wb.out; then
    cat /tmp/_wb.out >&2
    rm -f /tmp/_wb.out
    advisory_exit "memory write-back decision pending; see above."
  fi
  rm -f /tmp/_wb.out
fi

# 4) Mandatory-dispatch gate. Flags the AP-COORD-1 pattern: the turn edited >=2
#    harness files without an acknowledged dispatch. Self-skips when not a git
#    repo, when <2 harness files changed, or when .harness/dispatch-ack exists.
#    Delegates to project-meta's dispatch_ledger.py (resolve-don't-vendor).
pm_disp="$pm_dir/scripts/dispatch_ledger.py"
if [[ -f "$pm_disp" ]]; then
  if ! python3 "$pm_disp" --target-root . gate 2>/tmp/_dg.out; then
    cat /tmp/_dg.out >&2
    rm -f /tmp/_dg.out
    advisory_exit "mandatory-dispatch gate: see above."
  fi
  rm -f /tmp/_dg.out
fi

# 5) Project Board store integrity. When a board store exists, validate it (board.py tx:
#    item schema + duplicate ids + roadmap references + items_sha256 freshness) so a
#    hand-edited or stale store is caught before the turn ends. Resolve-don't-vendor;
#    pm_dir was resolved above for repo_memory.py, re-resolve on the board sentinel if needed.
if [[ -f docs/backlog/items.jsonl ]]; then
  pm_board="$pm_dir/scripts/board.py"
  if [[ ! -f "$pm_board" ]]; then
    pm_bdir="$(resolve_project_meta scripts/board.py)" || pm_bdir=""
    pm_board="$pm_bdir/scripts/board.py"
  fi
  if [[ -f "$pm_board" ]]; then
    if ! python3 "$pm_board" tx --root . >/tmp/_bt.out 2>&1; then
      cat /tmp/_bt.out >&2
      rm -f /tmp/_bt.out
      advisory_exit "project board store check (board.py tx) failed; see above."
    fi
    rm -f /tmp/_bt.out
  fi
fi

exit 0
