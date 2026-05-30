#!/usr/bin/env python3
"""Find near-duplicate reference content across skills (one-source-of-truth).

A fact that lives in two reference files drifts; one copy goes silently wrong
(writing-skills.md: "One source of truth per fact"). This critic compares
every references/*.md across the marketplace's skills, reporting cross-skill
pairs that share headings or whose bodies are highly similar — candidates for
extraction into a shared component.

Usage:

    python3 cross_skill_redundancy.py <marketplace-root-or-skills-dir> \
        [--ratio 0.5] [--min-shared-headings 2] [--strict]

Dependency-free (uses difflib from the standard library).

Exit: 0 = no redundancy over threshold (or advisory), 1 = found under
--strict, 2 = path not resolved.
"""

from __future__ import annotations

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


# Structural boilerplate every reference carries; sharing these is not redundancy.
GENERIC_HEADINGS = {
    "contents", "overview", "summary", "examples", "gotchas", "requirements",
    "workflow", "output", "output contract", "schema", "why", "common pitfalls",
    "cadence", "roles", "anti-patterns", "anti-pattern", "notes", "scope",
}


def _is_heading(line: str) -> bool:
    # ATX heading: leading hashes followed by a space (excludes #region, shebangs).
    s = line.lstrip()
    return s.startswith("#") and s.lstrip("#").startswith(" ") and len(s.lstrip("#").strip()) > 2


def headings(text: str, drop_generic: bool = False) -> set[str]:
    hs = {ln.lstrip("#").strip().lower() for ln in text.splitlines() if _is_heading(ln)}
    return {h for h in hs if h not in GENERIC_HEADINGS} if drop_generic else hs


def normalize(text: str) -> str:
    # Drop heading markers and collapse whitespace so prose dominates the ratio.
    body = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", body).strip().lower()


def collect_refs(skills_root: Path) -> list[tuple[str, str, str]]:
    """Return (skill, relpath, text) for every references/*.md."""
    out: list[tuple[str, str, str]] = []
    for skill in sorted(d for d in skills_root.iterdir() if d.is_dir()):
        refs = skill / "references"
        if not refs.is_dir():
            continue
        for f in sorted(refs.glob("*.md")):
            out.append((skill.name, f"references/{f.name}", f.read_text(encoding="utf-8", errors="replace")))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="Marketplace root (with skills/) or a directory of skill dirs")
    parser.add_argument("--ratio", type=float, default=0.5, help="difflib similarity to flag (default 0.5)")
    parser.add_argument("--min-shared-headings", type=int, default=2, help="shared headings to flag (default 2)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when redundancy is found")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    skills_root = root / "skills" if (root / "skills").is_dir() else root
    refs = collect_refs(skills_root)
    if len(refs) < 2:
        print(f"need >=2 reference files; found {len(refs)} under {skills_root}", file=sys.stderr)
        return 2

    hits = 0
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            (sa, pa, ta), (sb, pb, tb) = refs[i], refs[j]
            if sa == sb:
                continue  # cross-skill redundancy only
            shared = headings(ta, drop_generic=True) & headings(tb, drop_generic=True)
            ratio = SequenceMatcher(None, normalize(ta), normalize(tb)).ratio()
            # A heading match only counts as redundancy if the bodies also overlap;
            # otherwise two files just happen to share a distinctive section title.
            heading_hit = len(shared) >= args.min_shared_headings and ratio >= 0.2
            if heading_hit or ratio >= args.ratio:
                hits += 1
                print(f"REDUNDANT {sa}/{pa}  <->  {sb}/{pb}")
                print(f"    body similarity: {ratio:.2f}   shared headings: {len(shared)}")
                if shared:
                    print(f"    headings: {', '.join(sorted(shared)[:6])}")
                print("    fix: extract the shared content into one owner; have the other reference it")

    print()
    print(f"summary: {hits} cross-skill redundancy candidate(s)")
    return 1 if (hits and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
