#!/usr/bin/env python3
"""Worktree audit CLI — the deterministic gather+classify leg of the Worktree
Trim Contract (see references/worktree-hygiene.md).

This script ships inside the ``project-meta`` skill. It is **read-only**: it
enumerates the repo's git worktrees, computes the facts that decide each one's
fate (merged-into-base?, dirty?, untracked work?, ahead/behind, last commit),
and classifies each into a disposition. It NEVER removes a worktree, deletes a
branch, merges, or commits — those are agent actions taken per the contract,
with user confirmation for anything destructive. The agent owns judgment; this
script owns the facts.

Dispositions:

    prune        backing directory is gone / git marks it prunable → safe to
                 ``git worktree prune`` (lossless).
    stale        branch fully merged into base AND no uncommitted/untracked
                 work → safe to remove worktree (+ delete the merged branch).
    in-progress  has uncommitted tracked changes OR untracked files → KEEP.
                 Unsaved work lives only here; surface it, never trim.
    mergeable    clean, but the branch has commits not in base → propose a
                 review+merge (does not auto-merge).

The primary (main) worktree is reported but never classified for trimming.

Operates on a *target repo* (``--target-root``, default: cwd). Base branch via
``--base`` (default: main). Standard library only.

Exit: 0 audit ran | 2 bad invocation / not a git repo.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _git(root: Path, *args: str, cwd: Path | None = None) -> tuple[int, str]:
    """Run a git command; return (returncode, stripped stdout)."""
    proc = subprocess.run(
        ["git", "-C", str(cwd or root), *args],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout.strip()


def _parse_worktrees(root: Path) -> list[dict]:
    """Parse ``git worktree list --porcelain`` into records."""
    rc, out = _git(root, "worktree", "list", "--porcelain")
    if rc != 0:
        return []
    records, cur = [], {}
    for line in out.splitlines():
        if not line:
            if cur:
                records.append(cur)
                cur = {}
            continue
        if line == "bare":
            cur["bare"] = True
        elif line == "detached":
            cur["detached"] = True
        elif line == "prunable" or line.startswith("prunable "):
            cur["prunable"] = True
        elif " " in line:
            key, _, val = line.partition(" ")
            cur[key] = val
    if cur:
        records.append(cur)
    return records


def _classify(root: Path, base: str, wt: dict, is_primary: bool) -> dict:
    path = Path(wt.get("worktree", ""))
    branch = (wt.get("branch", "") or "").replace("refs/heads/", "")
    head = wt.get("HEAD", "")[:9]
    rec = {
        "path": str(path),
        "branch": branch or ("(detached)" if wt.get("detached") else ""),
        "head": head,
        "primary": is_primary,
    }

    if not path.exists() or wt.get("prunable"):
        rec["disposition"] = "prune"
        rec["reason"] = "backing directory missing / git marks it prunable"
        return rec

    # Dirty (tracked changes) vs untracked files — counted separately so we can
    # tell "modified tracked file" from "brand-new unsaved work".
    _, porc = _git(root, "status", "--porcelain", cwd=path)
    lines = [l for l in porc.splitlines() if l]
    dirty = [l for l in lines if not l.startswith("??")]
    untracked = [l for l in lines if l.startswith("??")]
    rec["dirty_files"] = len(dirty)
    rec["untracked_files"] = len(untracked)

    merged = False
    if branch:
        mc, _ = _git(root, "merge-base", "--is-ancestor", branch, base)
        merged = mc == 0
        _, lr = _git(root, "rev-list", "--left-right", "--count", f"{base}...{branch}")
        parts = lr.split()
        if len(parts) == 2:
            rec["base_ahead"], rec["branch_ahead"] = int(parts[0]), int(parts[1])
    rec["merged"] = merged
    _, last = _git(root, "log", "-1", "--format=%cr — %s", cwd=path)
    rec["last_commit"] = last

    if is_primary:
        rec["disposition"] = "primary"
        rec["reason"] = "primary worktree — never trimmed"
        return rec

    if dirty or untracked:
        rec["disposition"] = "in-progress"
        bits = []
        if dirty:
            bits.append(f"{len(dirty)} uncommitted")
        if untracked:
            bits.append(f"{len(untracked)} untracked")
        rec["reason"] = f"has {' + '.join(bits)} change(s) — unsaved work, KEEP"
        return rec

    if merged:
        rec["disposition"] = "stale"
        rec["reason"] = "branch fully merged into base, clean tree — safe to trim"
        return rec

    rec["disposition"] = "mergeable"
    rec["reason"] = f"clean but {rec.get('branch_ahead', '?')} commit(s) not in {base} — review+merge"
    return rec


ORDER = ["in-progress", "mergeable", "stale", "prune", "primary"]
LABEL = {
    "in-progress": "IN PROGRESS — keep, surface",
    "mergeable": "MERGEABLE — review then merge",
    "stale": "STALE — safe to trim",
    "prune": "PRUNE — gone, safe to clear",
    "primary": "PRIMARY",
}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Read-only git worktree audit for the Worktree Trim Contract.")
    ap.add_argument("--target-root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--base", default="main", help="base branch to compare against (default: main)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    args = ap.parse_args(argv)

    root = Path(args.target_root).resolve()
    rc, _ = _git(root, "rev-parse", "--git-dir")
    if rc != 0:
        print(f"worktree_audit: not a git repo: {root}", file=sys.stderr)
        return 2

    worktrees = _parse_worktrees(root)
    if not worktrees:
        print("worktree_audit: no worktrees found", file=sys.stderr)
        return 2

    # The first record from `git worktree list` is the primary (main) worktree.
    primary_path = worktrees[0].get("worktree", "")
    results = [
        _classify(root, args.base, wt, is_primary=(wt.get("worktree") == primary_path))
        for wt in worktrees
    ]

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    by_disp: dict[str, list[dict]] = {}
    for r in results:
        by_disp.setdefault(r["disposition"], []).append(r)

    print(f"Worktree audit (base = {args.base}) — {len(results)} worktree(s)\n")
    for disp in ORDER:
        group = by_disp.get(disp)
        if not group:
            continue
        print(f"## {LABEL[disp]}  ({len(group)})")
        for r in group:
            print(f"  • {r['branch'] or '(no branch)'}  [{r['head']}]")
            print(f"    {r['path']}")
            print(f"    {r['reason']}")
            if r.get("last_commit"):
                print(f"    last: {r['last_commit']}")
        print()

    actionable = [r for r in results if r["disposition"] in ("stale", "prune")]
    inprog = [r for r in results if r["disposition"] == "in-progress"]
    mergeable = [r for r in results if r["disposition"] == "mergeable"]
    print(f"Summary: {len(actionable)} trimmable, {len(mergeable)} mergeable, "
          f"{len(inprog)} in-progress (keep).")
    if actionable:
        print("Next: confirm, then `git worktree remove <path>` (+ `git branch -d <branch>` if merged).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
