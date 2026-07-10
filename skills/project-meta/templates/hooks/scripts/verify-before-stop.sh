#!/usr/bin/env bash
# Stop hook: run repo-defined verification before the agent ends a turn.
#
# Responsibilities (each self-skips when its artifact is absent):
#   1. Phase-lock check (when phase-lock contract installed) — verify the
#      current phase's gate has passed at least once since started_utc.
#   2. Project verifier — run the project's own verification command if
#      .harness/verify.sh exists.
#   3. Memory write-back gate — repo_memory.py writeback.
#   4. Mandatory-dispatch gate — dispatch_ledger.py gate (AP-COORD-1).
#   5. Project Board store integrity — board.py tx.
#   6. Audit convergence gate — audit_ledger.py gate (final audits are
#      multi-round; an open+red audit transaction must converge before ship).
#   8. Last-turn-meta gate — last_turn_meta.py check (an editing recipe must
#      leave a valid .harness/last-turn-meta.json; fires only on harness change).
#   (elastic leg) 7. Lesson registry — lesson_registry.py validate/watermark.
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
EFFECTIVE_PROFILE="$PROFILE"
if [[ -f .harness/effective-profile ]]; then
  _effective="$(tr -d '\r\n' < .harness/effective-profile 2>/dev/null || true)"
  case "$_effective" in
    minimal|standard|strict) EFFECTIVE_PROFILE="$_effective" ;;
  esac
fi
[[ "$PROFILE" == "minimal" && "$EFFECTIVE_PROFILE" == "minimal" ]] && exit 0

# Per-invocation temp dir: fixed /tmp names collide across concurrent sessions
# (routine in multi-worktree fleet runs) and corrupt the diagnostics the agent
# sees. Fail-open if mktemp is unavailable — diagnostics matter less than turns.
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/vbs.XXXXXX" 2>/dev/null)" || exit 0
trap 'rm -rf "$TMPD"' EXIT

# Every gate below shells out to python3; a missing interpreter must fail open
# (exit 127 under set -e would otherwise hard-fail the hook in BOTH profiles).
command -v python3 >/dev/null 2>&1 || exit 0

# E1/DASH-073: gate-failure event artifact. advisory_exit terminates the whole
# hook, so a later step can never see an earlier gate's failure in-process; this
# one-line durable record is what makes "a gate failed this turn" observable at
# all (consumed read-then-truncate by `lesson_registry.py observe` on the next
# invocation). Git-ignored; size-capped; every write is fail-open.
GATE_EVENTS=".harness/stop-gate-events.jsonl"

record_gate_event() {
  local gate=$1
  {
    mkdir -p .harness 2>/dev/null
    if [[ -f "$GATE_EVENTS" ]] && [[ "$(wc -l < "$GATE_EVENTS" 2>/dev/null || echo 0)" -gt 400 ]]; then
      tail -n 200 "$GATE_EVENTS" > "$GATE_EVENTS.tmp" && mv "$GATE_EVENTS.tmp" "$GATE_EVENTS"
    fi
    printf '{"gate":"%s","profile":"%s","utc":"%s"}\n' \
      "$gate" "$PROFILE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$GATE_EVENTS"
  } 2>/dev/null || true
}

advisory_exit() {
  # Standard profile: warn on stderr, exit 0 so the agent can still close
  # the turn. Strict profile: exit non-zero to block. Either way, record the
  # failing gate id first so the evidence survives the process exit.
  local msg=$1
  local gate=${2:-unknown}
  record_gate_event "$gate"
  echo "[harness] $msg" >&2
  if [[ "$PROFILE" == "strict" ]]; then
    exit 1
  fi
  exit 0
}

pm_dir=""

# Resolve project-meta's install dir containing the sentinel script $1. Probes
# in priority order (first match wins):
#   1. explicit $PROJECT_META_DIR override (baked at init — most robust)
#   2. personal-skill locations (~/.codex/skills, ~/.claude/skills)
#   3. marketplace checkout (full-repo clone, all versions)
#   4. old-layout version cache: cache/<mkt>/<plugin>/<ver>/skills/project-meta/
#      (pre-3.0 installs; <plugin> is the installing plugin, e.g. global-meta)
#   5. new-layout (scoped) version cache: cache/<mkt>/project-meta/<ver>/
#      (marketplace >=3.0; source="./skills/project-meta" → cache root IS skill root)
# Existence-checked on the sentinel, so an older installed copy that lacks it
# is skipped safely. Echoes the dir, or returns 1.
resolve_project_meta() {
  local sentinel=$1 c
  for c in \
    "${PROJECT_META_DIR:-}" \
    "$HOME/.codex/skills/project-meta" \
    "$HOME/.claude/skills/project-meta" \
    "$HOME"/.codex/plugins/marketplaces/*/skills/project-meta \
    "$HOME"/.claude/plugins/marketplaces/*/skills/project-meta \
    "$HOME"/.codex/plugins/cache/*/*/*/skills/project-meta \
    "$HOME"/.claude/plugins/cache/*/*/*/skills/project-meta \
    "$HOME"/.codex/plugins/cache/*/project-meta/* \
    "$HOME"/.claude/plugins/cache/*/project-meta/* ; do
    if [[ -n "$c" && -f "$c/$sentinel" ]]; then printf '%s\n' "$c"; return 0; fi
  done
  return 1
}

# Invariant/core gates read raw HARNESS_PROFILE only. A derived effective profile
# can scale elastic advisory legs below, but it must not enable or disable the
# core verification path.
if [[ "$PROFILE" != "minimal" ]]; then

# 1) Phase-lock check, if installed.
if [[ -f .harness/phase-state.json ]]; then
  pm_dir="$(resolve_project_meta scripts/phase_lock_check.py)" || pm_dir=""
  pm_check="$pm_dir/scripts/phase_lock_check.py"
  if [[ -x "$pm_check" ]] || [[ -f "$pm_check" ]]; then
    if ! python3 "$pm_check" --harness-dir .harness >"$TMPD/pl.out" 2>&1; then
      cat "$TMPD/pl.out" >&2
      advisory_exit "phase-lock gate failed; see above." phase-lock
    fi
  fi
fi

# 2) Project verifier.
if [[ -x .harness/verify.sh ]]; then
  if ! .harness/verify.sh >"$TMPD/v.out" 2>&1; then
    cat "$TMPD/v.out" >&2
    advisory_exit "project verification failed; see above." project-verify
  fi
fi

# 3) Memory write-back gate. Flags a pending write-back decision when the turn
#    changed substantive files but no memory file was updated. Self-skips when
#    not a git repo, when nothing changed, or when .harness/writeback-ack
#    exists. Delegates to project-meta's repo_memory.py (resolve-don't-vendor).
pm_dir="$(resolve_project_meta scripts/repo_memory.py)" || pm_dir=""
pm_mem="$pm_dir/scripts/repo_memory.py"
if [[ -f "$pm_mem" ]]; then
  if ! python3 "$pm_mem" --target-root . writeback 2>"$TMPD/wb.out"; then
    cat "$TMPD/wb.out" >&2
    advisory_exit "memory write-back decision pending; see above." writeback
  fi
fi

# 4) Mandatory-dispatch gate. Flags the AP-COORD-1 pattern: the turn edited >=2
#    harness files without an acknowledged dispatch. Self-skips when not a git
#    repo, when <2 harness files changed, or when .harness/dispatch-ack exists.
#    Delegates to project-meta's dispatch_ledger.py (resolve-don't-vendor).
pm_disp="$pm_dir/scripts/dispatch_ledger.py"
if [[ -f "$pm_disp" ]]; then
  if ! python3 "$pm_disp" --target-root . gate 2>"$TMPD/dg.out"; then
    cat "$TMPD/dg.out" >&2
    advisory_exit "mandatory-dispatch gate: see above." dispatch
  fi
fi

# 5) Project Board store integrity. When a board store exists, validate it (board.py tx:
#    item schema + duplicate ids + roadmap references + items_sha256 freshness) so a
#    hand-edited or stale store is caught before the turn ends. Resolve-don't-vendor;
#    pm_dir was resolved above for repo_memory.py, re-resolve on the board sentinel if needed.
if [[ -f docs/backlog/items.jsonl ]]; then
  # Guard against an empty resolve result: "$pm_dir/scripts/board.py" with pm_dir=""
  # would yield the filesystem-rooted path /scripts/board.py.
  pm_board=""
  if [[ -n "$pm_dir" ]]; then pm_board="$pm_dir/scripts/board.py"; fi
  if [[ -z "$pm_board" || ! -f "$pm_board" ]]; then
    pm_bdir="$(resolve_project_meta scripts/board.py)" || pm_bdir=""
    pm_board=""
    if [[ -n "$pm_bdir" ]]; then pm_board="$pm_bdir/scripts/board.py"; fi
  fi
  if [[ -n "$pm_board" && -f "$pm_board" ]]; then
    if ! python3 "$pm_board" tx --root . >"$TMPD/bt.out" 2>&1; then
      cat "$TMPD/bt.out" >&2
      advisory_exit "project board store check (board.py tx) failed; see above." board-tx
    fi
  fi
fi

# 5.5) Session receipt — write a minimal auto receipt so the next SessionStart
#      can surface what this session did. Resolve-don't-vendor (reuses $pm_dir
#      resolved above). Thin floor: skip silently if unresolvable or if python3
#      is absent (already guarded above). A richer receipt written earlier in
#      the turn by the agent is NOT clobbered (--auto self-gates on age+richness).
pm_rcpt=""
if [[ -n "$pm_dir" ]]; then pm_rcpt="$pm_dir/scripts/session_receipt.py"; fi
if [[ -z "$pm_rcpt" || ! -f "$pm_rcpt" ]]; then
  pm_rdir="$(resolve_project_meta scripts/session_receipt.py)" || pm_rdir=""
  pm_rcpt=""
  if [[ -n "$pm_rdir" ]]; then pm_rcpt="$pm_rdir/scripts/session_receipt.py"; fi
fi
if [[ -n "$pm_rcpt" && -f "$pm_rcpt" ]]; then
  python3 "$pm_rcpt" --target-root . write --auto 2>/dev/null || true
fi

# 6) Audit convergence gate. Final audits are multi-round (recipes/audit.md,
#    Convergence loop): an open release-gated audit transaction whose last round
#    is still red (BLOCKER/MAJOR > 0, or the Round-4 cap) must not slip past a
#    turn end. Self-skips when no ledger exists — the gate enforces that a
#    CLAIMED audit converges; it never forces audits to happen.
if [[ -f .harness/audit-ledger.jsonl ]]; then
  pm_audit=""
  if [[ -n "$pm_dir" ]]; then pm_audit="$pm_dir/scripts/audit_ledger.py"; fi
  if [[ -z "$pm_audit" || ! -f "$pm_audit" ]]; then
    pm_audir="$(resolve_project_meta scripts/audit_ledger.py)" || pm_audir=""
    if [[ -n "$pm_audir" ]]; then pm_audit="$pm_audir/scripts/audit_ledger.py"; fi
  fi
  if [[ -n "$pm_audit" && -f "$pm_audit" ]]; then
    if ! python3 "$pm_audit" --target-root . gate >"$TMPD/ag.out" 2>&1; then
      cat "$TMPD/ag.out" >&2
      advisory_exit "audit convergence gate: see above." audit-convergence
    fi
  fi
fi

# 8) Last-turn metadata gate (D5). The machine counterpart to the prose Output
#    Footer: an editing recipe must leave a valid .harness/last-turn-meta.json.
#    last_turn_meta.py fires only when this turn changed >=1 harness file (it
#    reuses dispatch_ledger's harness-file definition), so read-only turns are a
#    no-op. File-derived — never greps the transcript.
pm_ltm=""
if [[ -n "$pm_dir" ]]; then pm_ltm="$pm_dir/scripts/last_turn_meta.py"; fi
if [[ -z "$pm_ltm" || ! -f "$pm_ltm" ]]; then
  pm_ltmdir="$(resolve_project_meta scripts/last_turn_meta.py)" || pm_ltmdir=""
  if [[ -n "$pm_ltmdir" ]]; then pm_ltm="$pm_ltmdir/scripts/last_turn_meta.py"; fi
fi
if [[ -n "$pm_ltm" && -f "$pm_ltm" ]]; then
  if ! python3 "$pm_ltm" --target-root . check >"$TMPD/ltm.out" 2>&1; then
    cat "$TMPD/ltm.out" >&2
    advisory_exit "last-turn-meta gate: see above." last-turn-meta
  fi
fi

fi # end raw HARNESS_PROFILE-gated invariant/core checks

# --- D6: lesson registry (begin) ---
# 7) Lesson registry gate (D6). Runs validate (hard gate) + watermark (advisory)
#    when .harness/lessons.jsonl exists. Self-skips when the store is absent.
#    Delegates to project-meta's lesson_registry.py (resolve-don't-vendor).
if [[ "$EFFECTIVE_PROFILE" != "minimal" && -f .harness/lessons.jsonl ]]; then
  pm_les=""
  if [[ -n "$pm_dir" ]]; then pm_les="$pm_dir/scripts/lesson_registry.py"; fi
  if [[ -z "$pm_les" || ! -f "$pm_les" ]]; then
    pm_ldir="$(resolve_project_meta scripts/lesson_registry.py)" || pm_ldir=""
    pm_les=""
    if [[ -n "$pm_ldir" ]]; then pm_les="$pm_ldir/scripts/lesson_registry.py"; fi
  fi
  if [[ -n "$pm_les" && -f "$pm_les" ]]; then
    # observe (E1/DASH-073): heuristic evidence leg. Runs FIRST so it consumes
    # gate-failure events recorded by earlier invocations this turn before the
    # validate leg below can add a fresh one. Advisory, fail-open, exits 0.
    python3 "$pm_les" --target-root . observe 2>&1 | sed 's/^/[harness] /' >&2 || true
    # validate: hard gate for the elastic lesson leg. Invariant core gates above
    # intentionally keep reading HARNESS_PROFILE directly.
    if ! python3 "$pm_les" --target-root . validate >"$TMPD/lr.out" 2>&1; then
      cat "$TMPD/lr.out" >&2
      echo "[harness] lesson registry validate failed; see above." >&2
      record_gate_event lesson-validate
      if [[ "$EFFECTIVE_PROFILE" == "strict" ]]; then
        exit 1
      fi
    fi
    # watermark: advisory only — always runs, output goes to stderr
    python3 "$pm_les" --target-root . watermark 2>&1 | sed 's/^/[harness] /' >&2 || true
  fi
fi
# --- D6: lesson registry (end) ---

exit 0
