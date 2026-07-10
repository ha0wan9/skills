#!/usr/bin/env python3
"""Find MUST/Gotcha rules that name a backing script but no hook enforces (AP-VAL-1/2).

A rule worded "MUST run X.py after every mutation" is advisory until a hook
fires it deterministically. This critic scans each SKILL.md for invariant /
gotcha lines that reference a script, then checks whether any hook
configuration in the marketplace actually invokes that script. The gap list
is the finding: it tells you exactly which prose rules are candidates for
PostToolUse / Stop hooks.

Inline enforcement tags:

    A rule line (or the physical line immediately following it — bounded to
    +1, no further) may carry a tag documenting how it is actually enforced:

        (enforcement: manual|advisory|hook|stop-gate|ci)

    - `manual` / `advisory`  — deliberately not hook-enforced (an
      operator-run command, or a session-start/advisory leg). Reported as
      INFO instead of GAP.
    - `hook` / `stop-gate` / `ci`  — intended to be hook-enforced. Behaves
      like an untagged line: still checked against actual hook wiring and
      reported as GAP when no hook invokes the script. Tagging one of these
      levels documents intent only; it does not itself close the gap.
    - Untagged — default, unchanged: GAP when backed and unenforced.

    CONFLICT check: a rule line that contains a MUST-ASSERTION may not be
    tagged `manual` or `advisory` — that combination is reported as
    CONFLICT (and fails the run under --strict). A MUST-ASSERTION is a bold
    `**MUST**` or a line-initial/imperative `MUST` token; mentions like
    "MUST-rules", "MUST-rule", or "a new MUST" are not assertions and do not
    trigger the check.

Usage:

    python3 determinism_gap_scan.py <marketplace-root-or-skills-dir> [--strict]

Dependency-free. Gaps are EXPECTED until hooks are installed; default exit is
0 (advisory scan). Pass --strict to make any gap or conflict exit 1 (for a gate).

Exit: 0 = no gaps/conflicts (or advisory mode), 1 = gaps/conflicts found under
--strict, 2 = path not resolved.
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

ENFORCEMENT_TAG_RE = re.compile(r"\(enforcement:\s*(manual|advisory|hook|stop-gate|ci)\)", re.IGNORECASE)
MUST_TOKEN_RE = re.compile(r"\bMUST\b")
MENTION_SUFFIX_RE = re.compile(r"-rules?\b")


def body_after_frontmatter(text: str) -> str:
    """Return the markdown body with any leading frontmatter stripped."""
    return _split_fm(text)[1]


def has_must_assertion(line: str) -> bool:
    """True if `line` contains a MUST-ASSERTION (bold **MUST** or an imperative
    MUST token), as opposed to a mere MENTION like "MUST-rules" or "a new MUST"."""
    if "**MUST**" in line:
        return True
    for m in MUST_TOKEN_RE.finditer(line):
        start, end = m.start(), m.end()
        if MENTION_SUFFIX_RE.match(line, end):
            continue  # mention: MUST-rule / MUST-rules
        if line[:start].rstrip().lower().endswith("a new"):
            continue  # mention: "a new MUST"
        return True
    return False


def find_enforcement_tag(line: str, next_line: str | None) -> str | None:
    """Return the enforcement level tagged on `line` or the immediately
    following physical line (bounded +1), or None if untagged."""
    m = ENFORCEMENT_TAG_RE.search(line)
    if not m and next_line is not None:
        m = ENFORCEMENT_TAG_RE.search(next_line)
    return m.group(1).lower() if m else None


def rules_referencing_scripts(body: str) -> list[tuple[str, str, str | None, bool]]:
    """Return (script_name, rule_excerpt, enforcement_tag, has_must_assertion)
    for lines that look like rules and name a .py."""
    out: list[tuple[str, str, str | None, bool]] = []
    lines = body.splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        low = line.lower()
        if not any(h in low for h in RULE_HINT):
            continue
        matches = list(SCRIPT_RE.finditer(line))
        if not matches:
            continue
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else None
        tag = find_enforcement_tag(line, next_line)
        must = has_must_assertion(line)
        for m in matches:
            script = Path(m.group(1)).name
            excerpt = (line[:110] + "…") if len(line) > 110 else line
            out.append((script, excerpt, tag, must))
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
    parser.add_argument("--strict", action="store_true", help="exit 1 when any gap or conflict is found")
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
    infos = 0
    conflicts = 0
    for skill in skills:
        body = body_after_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        rows = rules_referencing_scripts(body)
        # de-dup on (script, excerpt)
        seen: set[tuple[str, str]] = set()
        printed_header = False

        def header() -> None:
            nonlocal printed_header
            if not printed_header:
                print(f"{skill.name}:")
                printed_header = True

        for script, excerpt, tag, must in rows:
            if (script, excerpt) in seen:
                continue
            seen.add((script, excerpt))
            backed = script in available
            if not backed:
                continue
            if tag in ("manual", "advisory"):
                if must:
                    conflicts += 1
                    header()
                    print(f"  CONFLICT  {script}  (MUST-assertion tagged '{tag}')")
                    print(f"       rule: {excerpt}")
                else:
                    infos += 1
                    header()
                    print(f"  INFO  {script}  (enforcement: {tag})")
                    print(f"       rule: {excerpt}")
                continue
            # tag in (None, "hook", "stop-gate", "ci") — behaves like untagged
            hooked = script in enforced
            if not hooked:
                gaps += 1
                header()
                print(f"  GAP  {script}  (no hook enforces it)")
                print(f"       rule: {excerpt}")
        if printed_header:
            print()

    print(f"summary: {gaps} rule(s) reference a backing script with no enforcing hook")
    print(f"summary: {infos} rule(s) tagged manual/advisory (INFO, not a gap)")
    print(f"summary: {conflicts} rule(s) tag a MUST-assertion as manual/advisory (CONFLICT)")
    if gaps and not args.strict:
        print("note: advisory scan — promote each to a PostToolUse/Stop hook to close the gap (AP-VAL-1/2)")
    return 1 if ((gaps or conflicts) and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
