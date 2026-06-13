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

# --- D7: derive-profile (begin) ---
# Elastic profile resolution is opt-in. If floor/ceiling are configured, derive a
# bounded effective profile for elastic SessionStart legs and persist it for
# sibling hooks. If not configured, delete stale derived state.
if [[ -n "${HARNESS_PROFILE_FLOOR:-}" || -n "${HARNESS_PROFILE_CEILING:-}" ]]; then
  _prof_dir=""
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
    if [[ -n "$_c" && -f "$_c/scripts/derive_profile.py" ]]; then
      _prof_dir="$_c"; break
    fi
  done
  if [[ -n "$_prof_dir" ]] && command -v python3 >/dev/null 2>&1; then
    mkdir -p .harness 2>/dev/null || true
    _profile_tmp="$(mktemp "${TMPDIR:-/tmp}/effective-profile.XXXXXX" 2>/dev/null)" || _profile_tmp=""
    if [[ -n "$_profile_tmp" ]]; then
      if python3 "$_prof_dir/scripts/derive_profile.py" --root . >"$_profile_tmp" 2>/dev/null; then
        _derived="$(tr -d '\r\n' <"$_profile_tmp")"
        case "$_derived" in
          minimal|standard|strict)
            printf '%s\n' "$_derived" > .harness/effective-profile
            PROFILE="$_derived"
            ;;
          *)
            echo "[harness] WARN: derive_profile returned invalid profile; using HARNESS_PROFILE=$PROFILE." >&2
            ;;
        esac
      else
        echo "[harness] WARN: derive_profile failed; using HARNESS_PROFILE=$PROFILE." >&2
      fi
      rm -f "$_profile_tmp"
    fi
  fi
else
  rm -f .harness/effective-profile 2>/dev/null || true
fi
# --- D7: derive-profile (end) ---

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
      HARNESS_PROFILE="$PROFILE" python3 "$_rcpt_dir/scripts/session_receipt.py" --target-root . inject 2>/dev/null || true
    fi
    # --- D6: lesson inject (begin) ---
    # Inject lesson registry reminder: unprocessed candidates + stale targets.
    # Self-gates: prints nothing when store absent or HARNESS_PROFILE=minimal.
    # Resolve project-meta the same way as the receipt probe above.
    _les_dir=""
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
      if [[ -n "$_c" && -f "$_c/scripts/lesson_registry.py" ]]; then
        _les_dir="$_c"; break
      fi
    done
    if [[ -n "$_les_dir" ]] && command -v python3 >/dev/null 2>&1; then
      # Pass model tier when discoverable from environment
      _les_tier=""
      if [[ -n "${CLAUDE_MODEL:-}" ]]; then
        # Map model string to tier: haiku/sonnet/opus/fable (best-effort substring match)
        _les_model_lc="$(printf '%s' "$CLAUDE_MODEL" | tr '[:upper:]' '[:lower:]')"
        case "$_les_model_lc" in
          *haiku*)  _les_tier="haiku"  ;;
          *sonnet*) _les_tier="sonnet" ;;
          *opus*)   _les_tier="opus"   ;;
          *fable*)  _les_tier="fable"  ;;
        esac
      fi
      if [[ -n "$_les_tier" ]]; then
        HARNESS_PROFILE="$PROFILE" python3 "$_les_dir/scripts/lesson_registry.py" --target-root . inject --model-tier "$_les_tier" 2>/dev/null || true
      else
        HARNESS_PROFILE="$PROFILE" python3 "$_les_dir/scripts/lesson_registry.py" --target-root . inject 2>/dev/null || true
      fi
    fi
    # --- D6: lesson inject (end) ---
    ;;
  *)
    echo "[harness] WARN: unknown HARNESS_PROFILE=$PROFILE; falling back to standard."
    echo "[harness] read $canonical before substantive work."
    ;;
esac
