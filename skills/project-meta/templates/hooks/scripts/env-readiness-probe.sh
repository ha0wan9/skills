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
#       * aws_secret_access_key assignments with a secret-shaped value (20+ chars)
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

    # Single python3 invocation: receives the capped file list via stdin,
    # sniffs binaries, scans with compiled regexes, prints one warning line
    # per hit (file path only — matched value is NEVER printed).
    #
    # Patterns (same set as the original per-file grep):
    #   aws_secret_access_key\s*[=:]\s*[quote?][A-Za-z0-9/+=]{20,}  (value must be secret-shaped, not a bare keyword mention)
    #   AKIA[0-9A-Z]{16}
    #   -----BEGIN (RSA |EC )?PRIVATE KEY-----
    #   ghp_[A-Za-z0-9]{36}
    #   (api[_-]?key|secret|token)\s*[:=]\s*['"'"'"][A-Za-z0-9+/]{20,}  (quote = \x27 or \x22 in embedded python)
    local scan_output
    scan_output="$(git -C "$TARGET_ROOT" ls-files 2>/dev/null \
        | python3 -c '
import sys, re, os

TARGET_ROOT = os.environ.get("HARNESS_TARGET_ROOT", ".")
FILE_CAP = 2000
PER_FILE_BYTE_CAP = 1 * 1024 * 1024  # 1 MiB per file

PATTERNS = re.compile(
    r"aws_secret_access_key\s*[=:]\s*[\x27\x22]?[A-Za-z0-9/+=]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"
    r"|ghp_[A-Za-z0-9]{36}"
    r"|(?:api[_\-]?key|secret|token)\s*[:=]\s*[\x27\x22][A-Za-z0-9+/]{20,}",
    re.IGNORECASE,
)

warned = []
count = 0
for line in sys.stdin:
    rel_path = line.rstrip("\n")
    count += 1
    if count > FILE_CAP:
        break
    abs_path = os.path.join(TARGET_ROOT, rel_path)
    if not os.path.isfile(abs_path):
        continue
    try:
        file_size = os.path.getsize(abs_path)
        if file_size > PER_FILE_BYTE_CAP:
            continue
        with open(abs_path, "rb") as fh:
            header = fh.read(8192)
        # Sniff binary: presence of NUL byte → skip.
        if b"\x00" in header:
            continue
        # Read full file as text for scanning.
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(PER_FILE_BYTE_CAP)
    except OSError:
        continue
    if PATTERNS.search(text):
        warned.append(rel_path)

for p in warned:
    print("[env-probe] WARNING: credential-shaped string found in tracked file: " + p + " (value not shown)")
if warned:
    print("[env-probe] WARNING: " + str(len(warned)) + " file(s) with potential secrets found — review and rotate credentials if committed accidentally.")
' 2>/dev/null)"

    if [ -n "$scan_output" ]; then
        printf '%s\n' "$scan_output"
    fi
}

_probe_secrets

exit 0
