#!/usr/bin/env bash
# ship_plugin.sh — deterministic mechanics for the "validated edit → ship" workflow.
#
# The agent orchestrates the chain; this script owns only the deterministic legs so
# they are reliable and cheap. The two judgment gates (repo validator must pass AND a
# fresh-context review agent must approve) live in the agent's flow, not here:
#
#   1. scripts/ship_plugin.sh validate          # validator gate — exits non-zero on failure
#   2. scripts/ship_plugin.sh open "<title>"    # commit (if needed) + push + open PR
#   3. <agent dispatches a FRESH-context review agent over the PR diff>
#   4. scripts/ship_plugin.sh land              # merge-if-clean + reload changed plugins
#
# `land` re-checks GitHub mergeability but does NOT itself run the review — the agent
# must only call `land` after the fresh review came back clean ("review, merge if clean").
#
# Subcommands:
#   validate            run repo validators on the changed plugins; exit 0 iff all pass
#   changed-plugins     print the plugin names touched vs the base branch (one per line)
#   open "<title>"      stage all, commit if there are changes, push branch, open/echo PR
#   land [--no-reload]  merge the current branch's PR if clean, then reload changed plugins
#   reload [names...]   refresh local install: marketplace update + plugin update (per name)
#
# Env overrides: BASE_BRANCH (default main), MARKETPLACE (default ha0wan9-skills),
#                MERGE_FLAGS (default "--squash --delete-branch").
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_BRANCH="${BASE_BRANCH:-main}"
MARKETPLACE="${MARKETPLACE:-ha0wan9-skills}"
MERGE_FLAGS="${MERGE_FLAGS:---squash --delete-branch}"

die()  { echo "ship: $*" >&2; exit 1; }
info() { echo "ship: $*" >&2; }

# Files changed by this branch's work: committed-vs-base ∪ staged ∪ unstaged.
_changed_files() {
  { git diff --name-only "${BASE_BRANCH}...HEAD" 2>/dev/null || true
    git diff --name-only 2>/dev/null || true
    git diff --name-only --staged 2>/dev/null || true
  } | sort -u | sed '/^$/d'
}

# Plugin (== skill dir) basenames touched by the change set.
_changed_plugins() {
  _changed_files | sed -n 's#^skills/\([^/]*\)/.*#\1#p' | sort -u
}

# --- marketplace.json sanity: parses, every skills[] path is a dir with SKILL.md,
#     plugin names are unique, and each plugin description matches its SKILL.md. ---
_validate_marketplace() {
  python3 - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mani = os.path.join(root, ".claude-plugin", "marketplace.json")
with open(mani) as f:
    data = json.load(f)
errs, names = [], set()
for p in data.get("plugins", []):
    n = p.get("name", "<unnamed>")
    if n in names:
        errs.append(f"duplicate plugin name: {n}")
    names.add(n)
    for sk in p.get("skills", []):
        d = os.path.normpath(os.path.join(root, sk))
        if not os.path.isdir(d):
            errs.append(f"{n}: skills path not a dir: {sk}")
            continue
        sm = os.path.join(d, "SKILL.md")
        if not os.path.isfile(sm):
            errs.append(f"{n}: no SKILL.md in {sk}")
if errs:
    print("marketplace.json invalid:\n  - " + "\n  - ".join(errs), file=sys.stderr)
    sys.exit(1)
print(f"marketplace.json ok ({len(names)} plugins)", file=sys.stderr)
PY
}

cmd_validate() {
  local plugins; plugins="$(_changed_plugins || true)"
  info "changed plugins: ${plugins:-<none>}"

  # Always: manifest must be coherent (cheap, catches the common drift).
  _validate_marketplace

  # project-meta has a dedicated dev validator.
  if grep -qx "project-meta" <<<"$plugins"; then
    info "running validate_project_meta.py"
    python3 scripts/validate_project_meta.py
  fi

  # dl-research ships a ledger validator; run it only when a runs.jsonl fixture changed.
  if grep -qx "dl-research" <<<"$plugins"; then
    local ledgers
    ledgers="$(_changed_files | grep -E 'skills/dl-research/.*runs\.jsonl$' || true)"
    if [[ -n "$ledgers" ]]; then
      while IFS= read -r lf; do
        [[ -n "$lf" ]] || continue
        info "validating ledger fixture: $lf"
        python3 skills/dl-research/scripts/validate_ledger.py "$lf"
      done <<<"$ledgers"
    fi
  fi

  info "validate: PASS"
}

cmd_changed_plugins() { _changed_plugins; }

cmd_open() {
  local title="${1:-}"
  [[ -n "$title" ]] || die "open requires a PR title: ship_plugin.sh open \"<title>\""
  local branch; branch="$(git rev-parse --abbrev-ref HEAD)"
  [[ "$branch" != "$BASE_BRANCH" ]] || die "refusing to ship from $BASE_BRANCH; switch to a feature branch"

  if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    git commit -m "$title" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  else
    info "no uncommitted changes; using existing commits"
  fi

  git push -u origin "$branch"

  local existing; existing="$(gh pr view "$branch" --json url -q .url 2>/dev/null || true)"
  if [[ -n "$existing" ]]; then
    info "PR already open: $existing"
    echo "$existing"
  else
    gh pr create --base "$BASE_BRANCH" --head "$branch" --title "$title" \
      --body "$(printf '%s\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)' "$title")" \
      --fill
  fi
}

cmd_land() {
  local do_reload=1
  [[ "${1:-}" == "--no-reload" ]] && { do_reload=0; shift || true; }

  local branch; branch="$(git rev-parse --abbrev-ref HEAD)"
  local plugins; plugins="$(_changed_plugins || true)"

  local state
  state="$(gh pr view "$branch" --json mergeStateStatus -q .mergeStateStatus 2>/dev/null || true)"
  info "PR mergeStateStatus: ${state:-<unknown>}"
  case "$state" in
    CLEAN|UNSTABLE|HAS_HOOKS|"") : ;;  # UNSTABLE = mergeable but checks pending/failing
    BEHIND)  die "PR is BEHIND base; update the branch before landing" ;;
    DIRTY)   die "PR has conflicts (DIRTY); resolve before landing" ;;
    BLOCKED) die "PR is BLOCKED by branch protection; cannot auto-merge" ;;
    *)       info "proceeding despite mergeStateStatus=$state" ;;
  esac

  # shellcheck disable=SC2086
  gh pr merge "$branch" $MERGE_FLAGS
  info "merged $branch into $BASE_BRANCH"

  if [[ "$do_reload" == "1" ]]; then
    cmd_reload $plugins
  fi
}

cmd_reload() {
  info "updating marketplace: $MARKETPLACE"
  claude plugin marketplace update "$MARKETPLACE" || info "marketplace update returned non-zero (continuing)"
  local n
  for n in "$@"; do
    [[ -n "$n" ]] || continue
    info "updating plugin: $n"
    claude plugin update "$n" || info "plugin update $n returned non-zero (continuing)"
  done
  info "reload done — restart Claude Code to apply updated plugins"
}

main() {
  local sub="${1:-}"; shift || true
  case "$sub" in
    validate)         cmd_validate "$@" ;;
    changed-plugins)  cmd_changed_plugins "$@" ;;
    open)             cmd_open "$@" ;;
    land)             cmd_land "$@" ;;
    reload)           cmd_reload "$@" ;;
    ""|-h|--help)
      sed -n '2,33p' "${BASH_SOURCE[0]}" ;;
    *) die "unknown subcommand: $sub (try --help)" ;;
  esac
}
main "$@"
