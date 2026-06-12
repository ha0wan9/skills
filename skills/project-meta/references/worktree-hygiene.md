# Worktree Hygiene

Use this reference when a session starts in a repo that accumulates git
worktrees (e.g. agent runs that create `.claude/worktrees/*` or `isolation:'worktree'`
Workflow peers). It owns the **Worktree Trim Contract**: the session-start sweep
that keeps the worktree set honest — trim what is stale, merge what is useful,
and surface what is in progress.

## Worktree Trim Contract

A session-start companion to the Memory Contract's read leg
([`repo-memory-crud.md#memory-contract`](repo-memory-crud.md)). Run it once, near
the start of a session, **before** substantive work — alongside reading canonical
memory — so the workspace you operate in is clean and nothing in-progress is lost.

The contract has a deterministic **gather+classify** leg (a CLI) and a
judgment **act** leg (the agent, with user confirmation for destructive steps).
Never invert this: the CLI never removes, merges, or commits; the agent never
trims on a guess.

### 1. Gather + classify (read-only CLI)

```bash
python3 scripts/worktree_audit.py --target-root . --base main
```

`worktree_audit.py` enumerates every worktree and assigns one disposition each,
from facts only (merged-into-base?, uncommitted tracked changes?, untracked
files?, ahead/behind, last commit):

| Disposition | Meaning | Default action |
|---|---|---|
| `prune` | backing dir gone / git marks prunable | `git worktree prune` (lossless) |
| `stale` | branch fully merged into base **and** clean tree (no dirty, no untracked) | trim: remove worktree + delete merged branch |
| `in-progress` | has uncommitted **or** untracked files | **KEEP** — surface it, never trim |
| `mergeable` | clean, but branch has commits not in base | review then merge (do not auto-merge) |
| `primary` | the main worktree | never trimmed |

The `--json` form feeds an agent loop; the default text form is the report you
show the user.

### 2. Act (agent, with confirmation)

- **Stale + prune → trim.** These are lossless (commits are already in base; the
  branch is recreatable; prunable dirs are already gone). Trim them:
  ```bash
  git worktree remove <path>          # add --force only if git refuses on a clean tree
  git branch -d <branch>              # -d (not -D): refuses if somehow unmerged
  git worktree prune                  # clears prunable/missing entries
  ```
  Because the work is provably preserved, a brief "trimming N stale worktrees"
  note is enough; you do not need a blocking confirmation for each. If `git
  branch -d` refuses, the branch was **not** actually merged — stop and reclassify.
- **In-progress → surface, never touch.** This is the load-bearing rule: an
  `in-progress` worktree may hold the only copy of unsaved work (untracked new
  files are invisible to every other checkout). Report what it holds (path,
  branch, what is uncommitted/untracked) so the user can decide. Do **not**
  remove it, and do **not** silently commit its contents — mid-design work is
  not merge-ready by default.
- **Mergeable → review then merge.** A clean branch with unmerged commits is a
  candidate to land, not stale debris. Route it through the normal review+merge
  path (the repo's ship/delivery flow), not a blind merge. When the repo has the
  land-queue capability installed (`agents/land-queue.md`), the merge leg is
  `scripts/land.sh queue <branches…>` — sequential, deterministic, test-gated
  (see [`land-queue-integration.md`](land-queue-integration.md)). Only after it
  merges does it become `stale` and trimmable.
- **Stale local base branch.** While auditing, if the primary worktree's base
  branch is behind its remote (`git rev-parse main` ≠ `git rev-parse origin/main`)
  with no local divergence, fast-forward it (`git fetch && git merge --ff-only`)
  so "merged into base" comparisons are accurate. This is housekeeping, not a trim.

### Safety invariants

- **Untracked beats merged.** "Branch merged into base" never authorizes a trim
  on its own — a merged branch can still sit in a worktree full of untracked,
  unsaved files (this is the common agent-session case). Dirty/untracked always
  wins and forces `in-progress`.
- **`-d`, not `-D`.** Delete branches with `git branch -d` so git's own
  merged-check is a second gate; reach for `-D` only with explicit user approval.
- **Confirm the irreversible-at-scale case.** Trimming a handful of provably-safe
  worktrees is fine to do and report. If a sweep would remove many worktrees, or
  any classified anything other than `stale`/`prune`, confirm first.
