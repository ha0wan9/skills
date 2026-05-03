#!/usr/bin/env bash
# PostToolUse hook: format files the agent just edited.
#
# Reads $CLAUDE_TOOL_USE_PATH (or $TOOL_USE_PATH) — the path the Edit /
# Write / MultiEdit tool just touched — and dispatches to the formatter
# matching the file extension. Silent on success; non-blocking on failure.
#
# Profile-aware via $HARNESS_PROFILE:
#   minimal   — disabled; never run
#   standard  — run formatter, ignore exit code
#   strict    — run formatter, exit non-zero on formatting changes (forces
#               the agent to re-stage)
#
# Add or remove formatters per project. Missing tools are skipped silently.

set -euo pipefail

PROFILE="${HARNESS_PROFILE:-standard}"
[[ "$PROFILE" == "minimal" ]] && exit 0

# Resolve the edited path from any of the conventional env vars Claude Code
# may export. Fall through to a no-op if none is set.
TARGET="${CLAUDE_TOOL_USE_PATH:-${TOOL_USE_PATH:-${EDITED_PATH:-}}}"
[[ -z "$TARGET" || ! -f "$TARGET" ]] && exit 0

ext="${TARGET##*.}"

run_format() {
  local cmd=$1
  shift
  command -v "$cmd" >/dev/null 2>&1 || return 0
  "$cmd" "$@" "$TARGET" >/dev/null 2>&1 || true
}

case "$ext" in
  py)
    run_format ruff format
    run_format black --quiet
    ;;
  ts|tsx|js|jsx)
    run_format prettier --write --log-level silent
    ;;
  json)
    run_format prettier --write --log-level silent
    ;;
  md)
    # Markdown formatters are opinionated; off by default.
    :
    ;;
  rs)
    run_format rustfmt --quiet
    ;;
  go)
    run_format gofmt -w
    ;;
  sh|bash)
    run_format shfmt -w
    ;;
  *)
    : # no-op for unknown extensions
    ;;
esac

if [[ "$PROFILE" == "strict" ]]; then
  # In strict mode, refuse to pass if the file was modified by the formatter.
  # The agent must re-stage the formatted version.
  if ! git diff --quiet --no-color -- "$TARGET" 2>/dev/null; then
    echo "[harness] strict: $TARGET was reformatted; re-stage before continuing." >&2
    exit 1
  fi
fi

exit 0
