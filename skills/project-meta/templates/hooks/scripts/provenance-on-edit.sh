#!/usr/bin/env bash
# PostToolUse hook: advisory provenance pass on a freshly-edited agents/*.md
# topical file (the artifacts that carry provenance frontmatter).
#
# Reads $CLAUDE_TOOL_USE_PATH (or $TOOL_USE_PATH / $EDITED_PATH). Acts only on
# agents/*.md; everything else is a no-op.
#
#   new (untracked) file → provenance.py auto-stamp — ADVISORY, never blocks:
#       a first draft legitimately lacks provenance, so the hard gate for new
#       files moves to deliver/validate. auto-stamp refreshes last_reviewed
#       when lineage is present and warns (without failing) when it is not.
#   pre-existing (tracked) file → provenance.py check — a tracked artifact must
#       keep its provenance; advisory at standard, blocking at strict.
#
# Profile-aware via $HARNESS_PROFILE: minimal disables; standard warns; strict
# blocks (only on the pre-existing-file check). Resolve-don't-vendor: it locates
# project-meta's provenance.py the same way the Stop hook resolves its scripts.

set -euo pipefail

PROFILE="${HARNESS_PROFILE:-standard}"
[[ "$PROFILE" == "minimal" ]] && exit 0

TARGET="${CLAUDE_TOOL_USE_PATH:-${TOOL_USE_PATH:-${EDITED_PATH:-}}}"
[[ -z "$TARGET" || ! -f "$TARGET" ]] && exit 0

# Only the provenance-carrying topical files.
case "$TARGET" in
  agents/*.md|*/agents/*.md) : ;;
  *) exit 0 ;;
esac

command -v python3 >/dev/null 2>&1 || exit 0

# Resolve project-meta's provenance.py (first existing match wins).
prov=""
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
  if [[ -n "$c" && -f "$c/scripts/provenance.py" ]]; then prov="$c/scripts/provenance.py"; break; fi
done
[[ -z "$prov" ]] && exit 0

if command -v git >/dev/null 2>&1 && git ls-files --error-unmatch "$TARGET" >/dev/null 2>&1; then
  # Tracked → hard check (advisory at standard, blocking at strict).
  if ! python3 "$prov" check "$TARGET" >/dev/null 2>&1; then
    echo "[harness] provenance: $TARGET is tracked but missing provenance keys (instantiated_from / source_reference / last_reviewed)." >&2
    [[ "$PROFILE" == "strict" ]] && exit 1
  fi
else
  # New/untracked → advisory auto-stamp (never blocks a first draft).
  python3 "$prov" auto-stamp "$TARGET" || true
fi
exit 0
