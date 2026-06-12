#!/usr/bin/env bash
# pre-tool-guard.sh — PreToolUse destructive-command guard (Bash tool, matcher Bash).
#
# Intercepts shell commands before execution and blocks/warns on patterns that can
# irreversibly destroy repo or system data. Closed pattern list v1 (word-boundary,
# precise) — see "Guard patterns" in docs/plans/agentic-infra-v0.6-build-plan.md §8.
#
# Guarded patterns:
#   rm -rf (or -fr / -r -f) on: /, ~, ., or an unquoted shell variable ($var)
#   git reset --hard
#   git clean with -f/-d/-x flags combined
#   DROP TABLE / DROP DATABASE / TRUNCATE TABLE (case-insensitive, in non-doc commands)
#
# False-positive policy:
#   rm file.txt                → allowed (no -r flag)
#   rm -rf /tmp/something      → allowed (concrete subpath under /tmp)
#   git reset --soft HEAD~1    → allowed (not --hard)
#   grep DROP docs/x.md        → allowed (doc-read command excluded)
#
# Profile-aware via $HARNESS_PROFILE:
#   minimal  — silent pass-through; exit 0 always
#   standard — emit warning to stderr; exit 0 (advisory, never blocks)
#   strict   — emit message to stderr; exit 2 (blocks the tool call)
#
# Block mechanism: exit 2 (PreToolUse deny convention).
# Fails open — any payload that cannot be parsed → exit 0 (never wedge the session).
#
# Independent of board-guard.sh — that guard protects board store files via
# Edit/Write/MultiEdit events; this guard intercepts Bash commands.
set -uo pipefail

profile="${HARNESS_PROFILE:-standard}"
[ "$profile" = "minimal" ] && exit 0

input="$(cat 2>/dev/null || true)"
[ -z "$input" ] && exit 0

# Extract .tool_input.command from the PreToolUse JSON payload via python3.
# python3 is a harness prerequisite; if unavailable we fail open.
cmd="$(printf '%s' "$input" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
ti = d.get("tool_input") or {}
print(ti.get("command") or "")
' 2>/dev/null || true)"

[ -z "$cmd" ] && exit 0

# ─── Detection helpers ────────────────────────────────────────────────────────
# Each returns 0 on match and sets GUARD_REASON.
GUARD_REASON=""

_check_rm_rf() {
    # Requires both a recursive flag (-r/-R) and force flag (-f) in the rm command,
    # targeting a dangerous location (/, ~, ., or an unquoted $variable).
    # /tmp/... and other concrete absolute subpaths are explicitly allowed.

    if ! printf '%s' "$cmd" | grep -qE '(^|[[:space:]])rm[[:space:]]'; then
        return 1
    fi

    # Check for both -r/-R and -f flags in any combined or separate form.
    local has_r=0 has_f=0
    if printf '%s' "$cmd" | grep -qE -- '-[a-zA-Z]*[rR][a-zA-Z]*'; then has_r=1; fi
    if printf '%s' "$cmd" | grep -qE -- '-[a-zA-Z]*f[a-zA-Z]*'; then has_f=1; fi
    [ "$has_r" -eq 0 ] || [ "$has_f" -eq 0 ] && return 1

    # Use python3 -c to tokenise the rm segment and inspect targets.
    local target_check
    target_check="$(printf '%s' "$cmd" | python3 -c '
import sys, re, shlex
cmd = sys.stdin.read()
# Split into segments on shell operators; find the rm segment.
segments = re.split(r"[;|&]", cmd)
rm_seg = ""
for seg in segments:
    seg = seg.strip()
    if re.search(r"(^|\s)rm\s", " " + seg):
        rm_seg = seg
        break
if not rm_seg:
    print("safe"); sys.exit(0)
try:
    tokens = shlex.split(rm_seg)
except ValueError:
    # Cannot tokenise (complex expansion) — conservative: treat as potentially dangerous
    print("unsafe"); sys.exit(0)
# Find rm index, collect non-flag tokens as targets.
rm_idx = None
for i, t in enumerate(tokens):
    if t == "rm" or t.endswith("/rm"):
        rm_idx = i
        break
if rm_idx is None:
    print("safe"); sys.exit(0)
targets = [t for t in tokens[rm_idx+1:] if not t.startswith("-") and t != "--"]
if not targets:
    print("safe"); sys.exit(0)
# Dangerous: bare /, ~, . or unquoted variable ($word / ${word}).
# /tmp/... and other concrete absolute subpaths are safe.
import re as _re
def is_dangerous(t):
    if t in ("/", "~", "."):
        return True
    if _re.match(r"^\$[{]?[A-Za-z_][A-Za-z0-9_]*", t):
        return True
    return False
dangerous = any(is_dangerous(t) for t in targets)
print("unsafe" if dangerous else "safe")
' 2>/dev/null || echo "safe")"

    if [ "$target_check" = "unsafe" ]; then
        GUARD_REASON="rm -rf on a dangerous target (/, ~, ., or unquoted variable). This is irreversible."
        return 0
    fi
    return 1
}

_check_git_reset_hard() {
    if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])git[[:space:]][^;|&]*reset[[:space:]][^;|&]*--hard'; then
        GUARD_REASON="git reset --hard discards all uncommitted changes and cannot be undone."
        return 0
    fi
    return 1
}

_check_git_clean() {
    # git clean is dangerous when it carries -f (force) AND at least one of -d or -x.
    if ! printf '%s' "$cmd" | grep -qE '(^|[[:space:]])git[[:space:]][^;|&]*clean[[:space:]]'; then
        return 1
    fi
    local has_f=0 has_d_or_x=0
    if printf '%s' "$cmd" | grep -qE -- 'git[[:space:]][^;|&]*clean[^;|&]*-[a-zA-Z]*f'; then has_f=1; fi
    if printf '%s' "$cmd" | grep -qE -- 'git[[:space:]][^;|&]*clean[^;|&]*-[a-zA-Z]*[dx]'; then has_d_or_x=1; fi
    if [ "$has_f" -eq 1 ] && [ "$has_d_or_x" -eq 1 ]; then
        GUARD_REASON="git clean with -f and -d/-x flags removes untracked files/dirs permanently."
        return 0
    fi
    return 1
}

_check_sql_destructive() {
    # Match DROP TABLE, DROP DATABASE, TRUNCATE TABLE (case-insensitive) in non-doc commands.
    if ! printf '%s' "$cmd" | grep -iqE '(DROP[[:space:]]+(TABLE|DATABASE)|TRUNCATE[[:space:]]+TABLE)'; then
        return 1
    fi
    # Exclude: grep, cat, less, more, head, tail, echo, printf — doc-read / output commands.
    if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])(grep|egrep|fgrep|cat|less|more|head|tail|echo|printf)[[:space:]]'; then
        return 1
    fi
    GUARD_REASON="Destructive SQL statement (DROP TABLE/DATABASE or TRUNCATE TABLE) detected."
    return 0
}

# ─── Run checks ───────────────────────────────────────────────────────────────

matched=0
if _check_rm_rf; then
    matched=1
elif _check_git_reset_hard; then
    matched=1
elif _check_git_clean; then
    matched=1
elif _check_sql_destructive; then
    matched=1
fi

[ "$matched" -eq 0 ] && exit 0

# ─── Enforce per profile ──────────────────────────────────────────────────────

case "$profile" in
  strict)
    echo "[pre-tool-guard] BLOCKED (strict): $GUARD_REASON" >&2
    echo "[pre-tool-guard] Command: $cmd" >&2
    exit 2
    ;;
  standard)
    echo "[pre-tool-guard] WARNING: $GUARD_REASON" >&2
    echo "[pre-tool-guard] Command: $cmd" >&2
    exit 0
    ;;
  *)
    # Unknown profile — fail open (advisory only)
    echo "[pre-tool-guard] WARNING (unknown profile '$profile'): $GUARD_REASON" >&2
    exit 0
    ;;
esac
