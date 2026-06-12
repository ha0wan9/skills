#!/usr/bin/env bash
# env-readiness-probe.sh — SessionStart environment readiness probe.
#
# Two legs (both advisory — always exits 0; a SessionStart hook must never block):
#
# (a) Command-resolvability leg: when .harness/verify.sh or a Makefile / package.json
#     exists in the repo root, the implied canonical toolchain entrypoints are checked
#     for resolvability (command -v / file existence). Unresolvable tools are reported.
#     Heuristics are simple and conservative to avoid false positives.
#
# (b) Secret leg: scans TRACKED files only (git ls-files, capped at 2000 files; binary
#     files skipped) for credential-shaped strings:
#       * aws_secret_access_key
#       * AKIA[0-9A-Z]{16}  (AWS access key ID)
#       * -----BEGIN (RSA |EC )?PRIVATE KEY-----
#       * ghp_[A-Za-z0-9]{36}  (GitHub personal access token)
#       * (api[_-]?key|secret|token)\s*[:=]\s*['"][A-Za-z0-9+/]{20,}
#     Warns with the file path. The secret value itself is NEVER printed.
#
# Profile-aware via $HARNESS_PROFILE:
#   minimal  — silent exit 0; no checks run
#   standard — warnings emitted for both legs
#   strict   — same as standard (exit 0 is fixed; SessionStart must not block)
#
# Always exits 0.
set -uo pipefail

profile="${HARNESS_PROFILE:-standard}"
[ "$profile" = "minimal" ] && exit 0

TARGET_ROOT="${HARNESS_TARGET_ROOT:-.}"

warn() { echo "[env-probe] WARNING: $*"; }

# ─── (a) Command-resolvability leg ───────────────────────────────────────────

_check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

_probe_commands() {
    # .harness/verify.sh — just check bash is present (models the pattern; always true).
    if [ -f "$TARGET_ROOT/.harness/verify.sh" ]; then
        _check_cmd bash || warn "command 'bash' not found on PATH — canonical toolchain entrypoint may be broken."
    fi

    # Makefile implies make.
    if [ -f "$TARGET_ROOT/Makefile" ] || [ -f "$TARGET_ROOT/makefile" ]; then
        _check_cmd make || warn "command 'make' not found on PATH — canonical toolchain entrypoint may be broken."
    fi

    # package.json implies node; lockfiles imply yarn/pnpm.
    if [ -f "$TARGET_ROOT/package.json" ]; then
        _check_cmd node || warn "command 'node' not found on PATH — canonical toolchain entrypoint may be broken."
        if [ -f "$TARGET_ROOT/yarn.lock" ]; then
            _check_cmd yarn || warn "command 'yarn' not found on PATH — canonical toolchain entrypoint may be broken."
        fi
        if [ -f "$TARGET_ROOT/pnpm-lock.yaml" ]; then
            _check_cmd pnpm || warn "command 'pnpm' not found on PATH — canonical toolchain entrypoint may be broken."
        fi
    fi

    # pyproject.toml / setup.py implies python3.
    if [ -f "$TARGET_ROOT/pyproject.toml" ] || [ -f "$TARGET_ROOT/setup.py" ] || [ -f "$TARGET_ROOT/setup.cfg" ]; then
        _check_cmd python3 || warn "command 'python3' not found on PATH — canonical toolchain entrypoint may be broken."
    fi

    # Cargo.toml implies cargo.
    if [ -f "$TARGET_ROOT/Cargo.toml" ]; then
        _check_cmd cargo || warn "command 'cargo' not found on PATH — canonical toolchain entrypoint may be broken."
    fi

    # go.mod implies go.
    if [ -f "$TARGET_ROOT/go.mod" ]; then
        _check_cmd go || warn "command 'go' not found on PATH — canonical toolchain entrypoint may be broken."
    fi
}

_probe_commands

# ─── (b) Secret leg ──────────────────────────────────────────────────────────

_probe_secrets() {
    # Only meaningful inside a git repo.
    if ! git -C "$TARGET_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        return 0
    fi

    # Combined regex pattern covering all credential shapes.
    # Intentionally uses -E (POSIX extended) for broad portability; -P (PCRE) tried first.
    local pat='aws_secret_access_key[[:space:]]*[=:][[:space:]]*[^[:space:]]|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|(api.?key|secret|token)[[:space:]]*[:=][[:space:]]*['"'"'"][A-Za-z0-9+/]{20,}'

    local warned_count=0
    local file_count=0

    # Iterate tracked files; bash 3.2-compatible (no mapfile).
    while IFS= read -r rel_path; do
        file_count=$((file_count + 1))
        [ "$file_count" -gt 2000 ] && break

        local abs_path="$TARGET_ROOT/$rel_path"
        [ -f "$abs_path" ] || continue

        # Skip binary files: check for null byte in first 8 KB via python3 (portable).
        local is_binary=0
        if python3 -c '
import sys
try:
    with open(sys.argv[1], "rb") as f:
        chunk = f.read(8192)
    sys.exit(0 if b"\x00" not in chunk else 1)
except Exception:
    sys.exit(0)
' "$abs_path" 2>/dev/null; then
            : # not binary — continue
        else
            is_binary=1
        fi
        [ "$is_binary" -eq 1 ] && continue

        # Scan for credential patterns. Never print the matched value.
        local hit=0
        if LC_ALL=C grep -qiP "$pat" "$abs_path" 2>/dev/null; then
            hit=1
        elif LC_ALL=C grep -qiE "$pat" "$abs_path" 2>/dev/null; then
            hit=1
        fi

        if [ "$hit" -eq 1 ]; then
            warn "credential-shaped string found in tracked file: $rel_path (value not shown)"
            warned_count=$((warned_count + 1))
        fi
    done < <(git -C "$TARGET_ROOT" ls-files 2>/dev/null)

    if [ "$warned_count" -gt 0 ]; then
        warn "$warned_count file(s) with potential secrets found — review and rotate credentials if committed accidentally."
    fi
}

_probe_secrets

exit 0
