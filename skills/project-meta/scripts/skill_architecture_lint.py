#!/usr/bin/env python3
"""Lint a skill against the mechanical subset of the writing-skills.md checklist.

This is the *structural floor* for the `audit` recipe's "Skill / harness
authoring" dimension. It enforces only the checklist items that are machine
decidable; judgement items (shape-based triggers, railroading, intent vs
mechanics) stay with the human/agent auditor.

Usage:

    python3 skill_architecture_lint.py <skill-dir-or-marketplace-root>

If the path contains `SKILL.md`, that single skill is linted. If it contains a
`skills/` directory (a marketplace checkout), every skill under it is linted.
The linter is dependency-free (standard library only).

Checks (each PASS / WARN / FAIL):

- SKILL.md present                                        (FAIL if missing)
- SKILL.md <= 250 lines                                   (FAIL over budget)
- frontmatter has `name` and `description`                (FAIL if missing)
- description ends on a trigger sentence ("Use when ...")  (WARN)
- a Core Rules / Cross-Cutting Invariants section exists   (WARN)
- a Gotchas section exists                                 (WARN)
- an Output Footer section exists                          (WARN)
- every scripts/*.py exposes argparse (AP-SKL-4)           (WARN per script)
- examples/ present when templates/ exist (AP-SKL-4)       (WARN)

Exit: 0 = no FAIL, 1 = at least one FAIL, 2 = path could not be resolved.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import frontmatter_field, split_frontmatter  # noqa: E402

LINE_BUDGET = 250
TRIGGER_HINTS = ("use when", "use for", "use this skill", "trigger when", "triggers on")
INVARIANT_HEADINGS = ("core rules", "cross-cutting invariants", "invariants")


@dataclass
class Finding:
    name: str
    status: str  # PASS, WARN, FAIL
    message: str = ""

    def render(self) -> str:
        return f"  {self.status} {self.name}: {self.message}" if self.message else f"  {self.status} {self.name}"


def _is_heading(line: str) -> bool:
    # ATX heading: 1-6 leading hashes followed by a space. Excludes `#region`,
    # shebangs, and other comment-style lines.
    s = line.lstrip()
    return s.startswith("#") and s.lstrip("#").startswith(" ")


def headings(body: str) -> list[str]:
    return [ln.lstrip("#").strip().lower() for ln in body.splitlines() if _is_heading(ln)]


def lint_skill(skill_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [Finding("SKILL.md present", "FAIL", "no SKILL.md in skill directory")]

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    n_lines = text.count("\n") + 1
    findings.append(
        Finding("line budget", "PASS" if n_lines <= LINE_BUDGET else "FAIL", f"{n_lines} lines (budget {LINE_BUDGET})")
    )

    fm, body = split_frontmatter(text)
    name = frontmatter_field(fm, "name")
    desc = frontmatter_field(fm, "description")
    if name and desc:
        findings.append(Finding("frontmatter", "PASS", f"name={name}"))
    else:
        missing = ", ".join(k for k, v in (("name", name), ("description", desc)) if not v)
        findings.append(Finding("frontmatter", "FAIL", f"missing: {missing}"))

    if desc:
        ends_trigger = any(h in desc.lower() for h in TRIGGER_HINTS)
        findings.append(
            Finding(
                "description trigger sentence",
                "PASS" if ends_trigger else "WARN",
                "names a trigger condition" if ends_trigger else "no 'Use when ...' trigger sentence found",
            )
        )

    hs = headings(body)
    findings.append(_heading_finding("invariants section", hs, INVARIANT_HEADINGS))
    findings.append(_heading_finding("gotchas section", hs, ("gotchas",)))
    findings.append(_heading_finding("output footer", hs, ("output footer", "output")))

    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.glob("*.py")):
            src = script.read_text(encoding="utf-8", errors="replace")
            has_cli = "argparse" in src or "add_argument" in src
            findings.append(
                Finding(
                    f"script CLI: {script.name}",
                    "PASS" if has_cli else "WARN",
                    "exposes argparse" if has_cli else "no argparse --help (AP-SKL-4)",
                )
            )
            # project-meta is the canonical home for frontmatter parsing; any
            # other skill re-rolling it should delegate to provenance.py.
            if skill_dir.name != "project-meta":
                rerolls_fm = ("split_frontmatter" in src or r'"\n---"' in src) and "provenance" not in src
                if rerolls_fm:
                    findings.append(
                        Finding(
                            f"frontmatter reuse: {script.name}",
                            "WARN",
                            "re-rolls frontmatter parsing; delegate to project-meta/scripts/provenance.py",
                        )
                    )

    if (skill_dir / "templates").is_dir():
        has_examples = (skill_dir / "examples").is_dir() and any((skill_dir / "examples").iterdir())
        findings.append(
            Finding(
                "examples present",
                "PASS" if has_examples else "WARN",
                "examples/ populated" if has_examples else "ships templates/ but no examples/ (AP-SKL-4)",
            )
        )

    # A skill that touches the shared memory/provenance harness must carry the
    # delegation pointer (resolver + thin floor), not freelance the protocol.
    if skill_dir.name != "project-meta":
        # Scan the whole skill (router + references + scripts), not just SKILL.md —
        # the harness touch or the resolver pointer may live in any of them.
        corpus = text
        for sub in ("references", "scripts"):
            d = skill_dir / sub
            if d.is_dir():
                for p in sorted(list(d.glob("*.md")) + list(d.glob("*.py"))):
                    corpus += "\n" + p.read_text(encoding="utf-8", errors="replace")
        low = corpus.lower()
        # Memory-specific signals only — bare "write-back"/"writeback" would
        # false-positive on e.g. a write-back *cache* in an unrelated skill.
        touches_harness = any(
            s in low for s in ("repo_memory", "memory contract", "memory write-back", "repo-memory-crud")
        )
        has_pointer = "project_meta_dir" in low or "shared-cli-delegation" in low
        if touches_harness and not has_pointer:
            findings.append(
                Finding(
                    "memory delegation pointer",
                    "WARN",
                    "references the memory protocol but no resolver + thin-floor pointer (see shared-cli-delegation.md)",
                )
            )

    return findings


def _heading_finding(name: str, hs: list[str], needles: tuple[str, ...]) -> Finding:
    present = any(any(needle in h for needle in needles) for h in hs)
    return Finding(name, "PASS" if present else "WARN", "present" if present else "section not found")


def resolve_skills(path: Path) -> list[Path]:
    if (path / "SKILL.md").is_file():
        return [path]
    skills_root = path / "skills" if (path / "skills").is_dir() else path
    return sorted(d for d in skills_root.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="A skill directory (with SKILL.md) or a marketplace root (with skills/)")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    skills = resolve_skills(root)
    if not skills:
        print(f"no skills found under {root}", file=sys.stderr)
        return 2

    total_fail = 0
    for skill in skills:
        findings = lint_skill(skill)
        fails = sum(1 for f in findings if f.status == "FAIL")
        warns = sum(1 for f in findings if f.status == "WARN")
        total_fail += fails
        print(f"{skill.name}: {len(findings) - fails - warns} pass, {warns} warn, {fails} fail")
        for f in findings:
            print(f.render())
        print()

    print(f"summary: {len(skills)} skill(s) linted, {total_fail} FAIL finding(s)")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
