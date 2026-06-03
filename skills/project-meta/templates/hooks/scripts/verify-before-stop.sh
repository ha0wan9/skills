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

# 1) Phase-lock check, if installed.
if [[ -f .harness/phase-state.json ]]; then
  # Resolve the project-meta install path from $PROJECT_META_DIR or fall back
  # to the conventional Claude Code skill install location.
  pm_dir="${PROJECT_META_DIR:-$HOME/.claude/skills/project-meta}"
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
pm_dir="${PROJECT_META_DIR:-$HOME/.claude/skills/project-meta}"
pm_mem="$pm_dir/scripts/repo_memory.py"
if [[ -f "$pm_mem" ]]; then
  if ! python3 "$pm_mem" --target-root . writeback 2>/tmp/_wb.out; then
    cat /tmp/_wb.out >&2
    rm -f /tmp/_wb.out
    advisory_exit "memory write-back decision pending; see above."
  fi
  rm -f /tmp/_wb.out
fi

exit 0
