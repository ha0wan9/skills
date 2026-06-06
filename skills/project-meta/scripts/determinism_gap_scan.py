#!/usr/bin/env python3
"""Find MUST/Gotcha rules that name a backing script but no hook enforces (AP-VAL-1/2).

A rule worded "MUST run X.py after every mutation" is advisory until a hook
fires it deterministically. This critic scans each SKILL.md for invariant /
gotcha lines that reference a script, then checks whether any hook
configuration in the marketplace actually invokes that script. The gap list
is the finding: it tells you exactly which prose rules are candidates for
PostToolUse / Stop hooks.

Usage:

    python3 determinism_gap_scan.py <marketplace-root-or-skills-dir> [--strict]

Dependency-free. Gaps are EXPECTED until hooks are installed; default exit is
0 (advisory scan). Pass --strict to make any gap exit 1 (for a gate).

Exit: 0 = no gaps (or advisory mode), 1 = gaps found under --strict,
2 = path not resolved.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import split_frontmatter as _split_fm  # noqa: E402

SCRIPT_RE = re.compile(r"\b([A-Za-z0-9_./-]*?[A-Za-z0-9_]+\.py)\b")
RULE_HINT = ("must", "gotcha", "after every", "before", "validate", "run ")


def body_after_frontmatter(text: str) -> str:
    """Return the markdown body with any leading frontmatter stripped."""
    return _split_fm(text)[1]


def rules_referencing_scripts(body: str) -> list[tuple[str, str]]:
    """Return (script_name, rule_excerpt) for lines that look like rules and name a .py."""
    out: list[tuple[str, str]] = []
    for raw in body.splitlines():
        line = raw.strip()
        low = line.lower()
        if not any(h in low for h in RULE_HINT):
            continue
        for m in SCRIPT_RE.finditer(line):
            script = Path(m.group(1)).name
            excerpt = (line[:110] + "…") if len(line) > 110 else line
            out.append((script, excerpt))
    return out


def hooked_scripts(skills_root: Path) -> set[str]:
    """Collect script basenames referenced by any hook config under the marketplace."""
    found: set[str] = set()
    patterns = ["**/settings*.json*", "**/hooks*.json", "**/hooks/*.sh", "**/hooks/scripts/*.sh", "**/*.fragment"]
    for pat in patterns:
        for f in skills_root.rglob(pat):
            if f.is_file():
                for m in SCRIPT_RE.finditer(f.read_text(encoding="utf-8", errors="replace")):
                    found.add(Path(m.group(1)).name)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="Marketplace root (with skills/) or a directory of skill dirs")
    parser.add_argument("--strict", action="store_true", help="exit 1 when any gap is found")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    skills_root = root / "skills" if (root / "skills").is_dir() else root
    skills = sorted(d for d in skills_root.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())
    if not skills:
        print(f"no skills found under {skills_root}", file=sys.stderr)
        return 2

    enforced = hooked_scripts(root)
    # glob on a missing scripts/ dir yields nothing, so no is_dir guard is needed.
    available = {s.name for skill in skills for s in (skill / "scripts").glob("*.py")}

    gaps = 0
    for skill in skills:
        body = body_after_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        rows = rules_referencing_scripts(body)
        # de-dup on (script, excerpt)
        seen: set[tuple[str, str]] = set()
        printed_header = False
        for script, excerpt in rows:
            if (script, excerpt) in seen:
                continue
            seen.add((script, excerpt))
            backed = script in available
            hooked = script in enforced
            if backed and not hooked:
                if not printed_header:
                    print(f"{skill.name}:")
                    printed_header = True
                gaps += 1
                print(f"  GAP  {script}  (no hook enforces it)")
                print(f"       rule: {excerpt}")
        if printed_header:
            print()

    print(f"summary: {gaps} rule(s) reference a backing script with no enforcing hook")
    if gaps and not args.strict:
        print("note: advisory scan — promote each to a PostToolUse/Stop hook to close the gap (AP-VAL-1/2)")
    return 1 if (gaps and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
