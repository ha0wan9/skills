#!/usr/bin/env python3
"""Suggest a review FLOOR (L0-L3) from mechanical diff signals.

This is a heuristic pre-filter, NOT a deterministic classifier (DASH-20). It keys
off signals computable from a diff — lines changed, file count, harness-path hit,
new-skill, MUST-rule — and suggests a *floor*. The judgment inputs that actually
drive stakes (behavior-change, blast radius, reversibility, semantic_scope) are
NOT computable from a diff, so the conductor must ESCALATE on judgment, never
silently de-escalate for high stakes, and MUST state the chosen level + why.

HARNESS_PROFILE (or --profile) shifts the floor: `minimal` lowers it (but never
below the new-skill / MUST-rule L3 floor), `strict` adds one.

Usage:

    python3 review_tier.py --diff main...HEAD [--profile strict]
    python3 review_tier.py --files 1 --lines 8        # explicit signals (no git)
    python3 review_tier.py --harness-hit
    python3 review_tier.py --new-skill --profile strict

Dependency-free. Advisory: always exits 0; the conductor owns the final call.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

LEVELS = ("L0", "L1", "L2", "L3")
PROFILES = ("minimal", "standard", "strict")

# Paths whose change implies the harness floor (L2): agent-facing canon + contracts.
HARNESS_PREFIXES = ("references/", "templates/", "agents/", "recipes/")
HARNESS_FILES = ("SKILL.md", "AGENTS.md", "USER.md", ".claude-plugin/marketplace.json")


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def signals_from_diff(diff_range: str, cwd: Path) -> dict:
    """Derive (lines, files, harness_hit, new_skill) from a git diff range.

    must_rule is not reliably detectable from a diff and stays flag-only."""
    numstat = _git(["diff", "--numstat", diff_range], cwd)
    names = _git(["diff", "--name-only", diff_range], cwd)
    status = _git(["diff", "--name-status", diff_range], cwd)
    if numstat is None or names is None:
        raise SystemExit(f"could not read git diff for range {diff_range!r} (not a repo / bad range)")
    lines = 0
    files = 0
    for row in numstat.splitlines():
        if not row.strip():
            continue
        added, deleted, *_ = row.split("\t")
        files += 1
        for n in (added, deleted):
            if n.isdigit():
                lines += int(n)
    name_list = [n for n in names.splitlines() if n.strip()]
    harness_hit = any(
        n.startswith(HARNESS_PREFIXES) or Path(n).name in HARNESS_FILES or n in HARNESS_FILES
        for n in name_list
    )
    new_skill = any(
        line.startswith("A") and line.rstrip().endswith("SKILL.md")
        for line in (status or "").splitlines()
    )
    return {"lines": lines, "files": files, "harness_hit": harness_hit, "new_skill": new_skill}


def suggest_level(lines: int, files: int, harness_hit: bool, new_skill: bool, must_rule: bool, profile: str) -> int:
    """Return a level index 0-3. The new-skill / MUST-rule floor is never
    de-escalated by a profile shift (DASH-20 high-stakes rule)."""
    stakes_floor = 3 if (must_rule or new_skill) else 0
    if harness_hit or files >= 6 or lines >= 150:
        size = 2
    elif files > 1 or lines > 15:
        size = 1
    else:
        size = 0
    if profile == "strict":
        size = min(size + 1, 3)
    elif profile == "minimal":
        size = max(size - 1, 0)
    return max(size, stakes_floor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--diff", help="git diff range, e.g. main...HEAD (derives signals)")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repo root for --diff")
    parser.add_argument("--files", type=int, default=0, help="explicit changed-file count")
    parser.add_argument("--lines", type=int, default=0, help="explicit changed-line count")
    parser.add_argument("--harness-hit", action="store_true", help="diff touches references/templates/recipes/agents/SKILL.md/AGENTS.md/marketplace")
    parser.add_argument("--new-skill", action="store_true", help="adds a new SKILL.md (L3 floor)")
    parser.add_argument("--must-rule", action="store_true", help="changes a MUST-rule / public contract (L3 floor)")
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=os.environ.get("HARNESS_PROFILE", "standard"),
        help="HARNESS_PROFILE floor shift (default: $HARNESS_PROFILE or standard)",
    )
    args = parser.parse_args(argv)

    sig = {"lines": args.lines, "files": args.files, "harness_hit": args.harness_hit, "new_skill": args.new_skill}
    if args.diff:
        derived = signals_from_diff(args.diff, args.root.resolve())
        # explicit flags supplement derived signals (OR for booleans, max for counts)
        sig = {
            "lines": max(derived["lines"], args.lines),
            "files": max(derived["files"], args.files),
            "harness_hit": derived["harness_hit"] or args.harness_hit,
            "new_skill": derived["new_skill"] or args.new_skill,
        }

    level = suggest_level(sig["lines"], sig["files"], sig["harness_hit"], sig["new_skill"], args.must_rule, args.profile)

    print(f"suggested floor: {LEVELS[level]}  (profile: {args.profile})")
    print(
        f"signals: files={sig['files']} lines={sig['lines']} "
        f"harness_hit={sig['harness_hit']} new_skill={sig['new_skill']} must_rule={args.must_rule}"
    )
    print(
        "NOTE: this is a FLOOR from mechanical signals only. Behavior-change, blast radius, "
        "reversibility, and semantic_scope are not computable from a diff — ESCALATE on judgment "
        "(never silently de-escalate for high stakes) and STATE the chosen level + why."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
