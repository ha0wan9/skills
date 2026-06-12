#!/usr/bin/env bash
# SessionStart hook: surface AGENTS.md routing so the agent has it without
# being prompted. Output goes to the agent's context as a system reminder.
#
# Profile-aware via $HARNESS_PROFILE (minimal | standard | strict):
#   minimal  — only print the canonical entrypoint name
#   standard — print canonical + topical-routing summary
#   strict   — print canonical + routing + invariants list
#
# Output kept short (≤30 lines) so it doesn't burn context budget.

set -euo pipefail

PROFILE="${HARNESS_PROFILE:-standard}"

# Locate the canonical entrypoint. Prefer CLAUDE.md when running under
# Claude Code (this hook fires there), AGENTS.md otherwise. Fall back
# gracefully if both exist.
canonical=""
if [[ -f CLAUDE.md ]]; then
  canonical="CLAUDE.md"
elif [[ -f AGENTS.md ]]; then
  canonical="AGENTS.md"
fi

if [[ -z "$canonical" ]]; then
  # No canonical memory file. Suggest /project-meta init quietly.
  cat <<'EOF'
[harness] no canonical project-memory file found (CLAUDE.md / AGENTS.md).
[harness] run `/project-meta init` to bootstrap.
EOF
  exit 0
fi

case "$PROFILE" in
  minimal)
    echo "[harness] canonical project memory: $canonical"
    ;;
  strict|standard)
    echo "[harness] read $canonical before substantive work."
    if [[ "$PROFILE" == "strict" ]]; then
      echo "[harness] MUST cite the AGENTS.md rule that justifies any non-trivial harness edit."
    fi
    # Surface topical routing keys if AGENTS.md uses the project-meta loader pattern.
    if grep -q '^## Topic Routing' "$canonical" 2>/dev/null; then
      echo "[harness] topical routing available; load only the relevant agents/*.md per task."
    fi
    # Inject prior-session receipt when available (self-gates on profile + existence).
    # Resolve project-meta's install dir using the same probe logic as verify-before-stop.sh.
    _rcpt_dir=""
    for _c in \
      "${PROJECT_META_DIR:-}" \
      "$HOME/.codex/skills/project-meta" \
      "$HOME/.claude/skills/project-meta" \
      "$HOME"/.codex/plugins/marketplaces/*/skills/project-meta \
      "$HOME"/.claude/plugins/marketplaces/*/skills/project-meta \
      "$HOME"/.codex/plugins/cache/*/*/*/skills/project-meta \
      "$HOME"/.claude/plugins/cache/*/*/*/skills/project-meta \
      "$HOME"/.codex/plugins/cache/*/project-meta/* \
      "$HOME"/.claude/plugins/cache/*/project-meta/* ; do
      if [[ -n "$_c" && -f "$_c/scripts/session_receipt.py" ]]; then
        _rcpt_dir="$_c"; break
      fi
    done
    if [[ -n "$_rcpt_dir" ]] && command -v python3 >/dev/null 2>&1; then
      python3 "$_rcpt_dir/scripts/session_receipt.py" --target-root . inject 2>/dev/null || true
    fi
    ;;
  *)
    echo "[harness] WARN: unknown HARNESS_PROFILE=$PROFILE; falling back to standard."
    echo "[harness] read $canonical before substantive work."
    ;;
esac
