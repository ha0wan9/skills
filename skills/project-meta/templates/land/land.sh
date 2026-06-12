#!/usr/bin/env bash
# land.sh — deterministic landing pipeline (land-queue capability).
#
# Integrates parallel agent branches into the base branch as a command, not
# a conversation: rebase onto base (git rerere + the registered syntax-aware
# merge driver auto-resolve what they can), run the repo's test command,
# fast-forward base. No model runs inside this script; exit codes route the
# escalation ladder defined in agents/land-queue.md.
#
#   scripts/land.sh setup [--base <branch>] [--test-cmd '<cmd>']
#   scripts/land.sh status
#   scripts/land.sh land <branch>
#   scripts/land.sh queue <branch> [<branch>...]
#
# Exit codes:
#   0 landed / ok        2 residual conflicts (bounded agent session needed)
#   1 usage / preflight  3 tests failed on the rebased branch
#   4 config missing     5 base not fast-forwardable or blocked by a dirty
#                          sibling worktree
#
# Config (repo-local git config, written by `setup`):
#   land.base     base branch (default: main)
#   land.testcmd  verification command run from the landed branch's worktree
#
# Protocol: project-meta/references/land-queue-integration.md
set -euo pipefail

MERGIRAF_DRIVER='mergiraf merge --git %O %A %B -s %S -x %X -y %Y -p %P -l %L'

die()  { printf 'land.sh: %s\n' "$*" >&2; exit 1; }
info() { printf 'land.sh: %s\n' "$*"; }

git rev-parse --git-dir >/dev/null 2>&1 || die "not inside a git repository"
TOPLEVEL="$(git rev-parse --show-toplevel)"

base_branch() { git config --get land.base 2>/dev/null || echo main; }

in_rebase() { git -C "$1" rev-parse -q --verify REBASE_HEAD >/dev/null 2>&1; }
unmerged()  { git -C "$1" diff --name-only --diff-filter=U; }

# Worktree path that has <branch> checked out, empty if none.
worktree_of() {
  git worktree list --porcelain | awk -v want="refs/heads/$1" '
    $1 == "worktree" { wt = substr($0, 10) }
    $1 == "branch" && $2 == want { print wt; exit }'
}

# Tracked changes block; untracked files only warn.
require_clean() {
  local dir="$1" label="$2"
  local tracked
  tracked="$(git -C "$dir" status --porcelain | grep -v '^??' || true)"
  [ -z "$tracked" ] || die "$label has uncommitted tracked changes — commit or stash first"
  if [ -n "$(git -C "$dir" status --porcelain)" ]; then
    info "warning: untracked files present in $label"
  fi
}

cmd_setup() {
  local base="" testcmd=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --base)     base="$2"; shift 2 ;;
      --test-cmd) testcmd="$2"; shift 2 ;;
      *) die "setup: unknown argument: $1" ;;
    esac
  done

  git config rerere.enabled true
  git config rerere.autoupdate true
  info "rerere enabled (repo-local)"

  if command -v mergiraf >/dev/null 2>&1; then
    git config merge.mergiraf.name mergiraf
    git config merge.mergiraf.driver "$MERGIRAF_DRIVER"
    info "mergiraf driver registered ($(mergiraf --version 2>/dev/null || echo 'version unknown'))"
    if ! grep -qs 'merge=mergiraf' "$TOPLEVEL/.gitattributes"; then
      info "warning: no merge=mergiraf lines in .gitattributes — driver is registered but no path opts in"
      info "  menu: mergiraf languages --gitattributes  (commit the extensions this repo uses)"
    fi
  else
    info "warning: mergiraf not on PATH — degraded to rerere only (layer 2 skipped)"
  fi

  [ -n "$base" ] && git config land.base "$base"
  [ -n "$testcmd" ] && git config land.testcmd "$testcmd"
  info "base=$(base_branch) testcmd=$(git config --get land.testcmd 2>/dev/null || echo '<unset>')"
}

cmd_status() {
  local base; base="$(base_branch)"
  printf 'base branch : %s\n' "$base"
  printf 'test command: %s\n' "$(git config --get land.testcmd 2>/dev/null || echo '<unset> — land will exit 4')"
  printf 'rerere      : %s\n' "$(git config --get rerere.enabled 2>/dev/null || echo off)"
  if command -v mergiraf >/dev/null 2>&1; then
    local registered="not registered — run setup"
    [ -n "$(git config --get merge.mergiraf.driver 2>/dev/null)" ] && registered="registered"
    printf 'mergiraf    : %s, %s\n' "$(mergiraf --version 2>/dev/null || echo present)" "$registered"
  else
    printf 'mergiraf    : absent — degraded to rerere only\n'
  fi
  local attr_count=0
  [ -f "$TOPLEVEL/.gitattributes" ] && attr_count="$(grep -c 'merge=mergiraf' "$TOPLEVEL/.gitattributes" || true)"
  printf 'attributes  : %s line(s) with merge=mergiraf\n' "$attr_count"
  if [ -d "$(git rev-parse --git-path rebase-merge)" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]; then
    printf 'WARNING     : rebase in progress in this worktree\n'
  fi
  printf 'awaiting landing (not merged into %s):\n' "$base"
  git branch --no-merged "$base" 2>/dev/null | sed 's/^/  /' || true
}

cmd_land() {
  [ $# -eq 1 ] || die "usage: land.sh land <branch>"
  local branch="$1" base; base="$(base_branch)"

  git show-ref --verify --quiet "refs/heads/$branch" || die "no such branch: $branch"
  git show-ref --verify --quiet "refs/heads/$base"   || die "no such base branch: $base"
  [ "$branch" != "$base" ] || die "refusing to land base onto itself"
  local testcmd
  testcmd="$(git config --get land.testcmd 2>/dev/null)" || {
    printf 'land.sh: land.testcmd not configured — run: scripts/land.sh setup --test-cmd '\''<cmd>'\''\n' >&2
    exit 4
  }

  # Run the rebase in the worktree that has the branch checked out (the
  # usual parallel-agent layout); fall back to checking it out here.
  local run_dir; run_dir="$(worktree_of "$branch")"
  [ -n "$run_dir" ] || run_dir="$TOPLEVEL"
  require_clean "$run_dir" "worktree $run_dir"

  info "rebasing $branch onto $base (rerere + merge driver active)"
  local rebase_ok=true
  if ! git -C "$run_dir" rebase "$base" "$branch"; then
    rebase_ok=false
    # rerere (autoupdate) replays recorded resolutions and stages them, but
    # git still stops the rebase — auto-continue while nothing is unmerged.
    local guard=0
    while in_rebase "$run_dir" && [ -z "$(unmerged "$run_dir")" ] && [ "$guard" -lt 100 ]; do
      guard=$((guard + 1))
      if GIT_EDITOR=true git -C "$run_dir" rebase --continue; then
        rebase_ok=true
        break
      fi
    done
  fi
  if ! $rebase_ok; then
    printf 'land.sh: RESIDUAL CONFLICTS — auto-resolution exhausted. Files:\n' >&2
    unmerged "$run_dir" | sed 's/^/  /' >&2
    git -C "$run_dir" rebase --abort
    printf 'land.sh: rebase aborted (clean). Escalate per agents/land-queue.md exit-2 row.\n' >&2
    exit 2
  fi

  info "running tests: $testcmd"
  if ! (cd "$run_dir" && bash -c "$testcmd"); then
    printf 'land.sh: TESTS FAILED on rebased %s — base untouched. Investigate in %s\n' "$branch" "$run_dir" >&2
    exit 3
  fi

  # Fast-forward base: in whichever worktree has it checked out, or by ref.
  git merge-base --is-ancestor "$base" "$branch" || {
    printf 'land.sh: base %s is not an ancestor of rebased %s — base moved mid-land; re-run\n' "$base" "$branch" >&2
    exit 5
  }
  local base_wt; base_wt="$(worktree_of "$base")"
  if [ -n "$base_wt" ]; then
    if [ -n "$(git -C "$base_wt" status --porcelain | grep -v '^??' || true)" ]; then
      printf 'land.sh: base %s is checked out dirty in %s — clean it, then re-run\n' "$base" "$base_wt" >&2
      exit 5
    fi
    git -C "$base_wt" merge --ff-only "$branch" >/dev/null
  else
    git fetch . "$branch:$base" 2>/dev/null || {
      printf 'land.sh: could not fast-forward %s — re-run\n' "$base" >&2
      exit 5
    }
  fi
  info "landed: $base is now $(git rev-parse --short "$base") ($branch). Branch/worktree cleanup per worktree hygiene; push per repo policy."
}

cmd_queue() {
  [ $# -ge 1 ] || die "usage: land.sh queue <branch> [<branch>...]"
  local total=$# i=0 landed=() b rc
  for b in "$@"; do
    i=$((i + 1))
    info "queue: landing $b ($i/$total)"
    rc=0
    cmd_land "$b" || rc=$?
    if [ "$rc" -ne 0 ]; then
      printf 'land.sh: queue stopped at %s (exit %s). Landed: %s. Not landed: %s\n' \
        "$b" "$rc" "${landed[*]:-none}" "${*:$i}" >&2
      exit "$rc"
    fi
    landed+=("$b")
  done
  info "queue complete: landed ${landed[*]}"
}

case "${1:-}" in
  setup)  shift; cmd_setup "$@" ;;
  status) shift; cmd_status ;;
  land)   shift; cmd_land "$@" ;;
  queue)  shift; cmd_queue "$@" ;;
  *) die "usage: land.sh {setup|status|land <branch>|queue <branch>...}" ;;
esac
