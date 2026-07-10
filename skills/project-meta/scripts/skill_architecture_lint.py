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
- prose loop declaration cites loop-contract.md             (WARN, never FAIL)
- embedded project-meta resolver has dual-runtime parity    (WARN, never FAIL)

The loop-marker check (`references/loop-contract.md`, DASH-059/060): a prose
skill file (SKILL.md, recipes/*.md, modes/*.md, references/*.md) that reads
like a loop declaration — >=2 distinct loop markers (iteration cap, re-audit
round, wakeup, stop condition, ratchet vocabulary) — but does not cite
loop-contract.md WARNs. This is a precision heuristic, not a classifier: it
never FAILs, and it is scoped to prose files only (not scripts, where the
same vocabulary is normal implementation detail — see the known-non-matches
in `--self-test`).

The resolver-parity check (`references/shared-cli-delegation.md`, task A5): a
line in skill markdown that names the project-meta install path
(`.claude/skills/project-meta`, `.claude/plugins/.../project-meta`, or their
`.codex` equivalents) is an embedded copy of the shared-CLI resolver. If the
surrounding block (+-10 lines) shows neither a `.codex` path nor a
scoped-cache (`plugins/cache/*/project-meta`) path, and never cites
`shared-cli-delegation.md` (the canonical resolver), it WARNs — the snippet
has likely drifted from the dual-runtime 8-glob set in
`templates/hooks/scripts/verify-before-stop.sh`. Advisory only, and scoped to
markdown — the canonical hook scripts are not linted here.

Usage:

    python3 skill_architecture_lint.py <skill-dir-or-marketplace-root>
    python3 skill_architecture_lint.py --self-test

Exit: 0 = no FAIL, 1 = at least one FAIL, 2 = path could not be resolved.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import frontmatter_field, split_frontmatter  # noqa: E402

LINE_BUDGET = 250
TRIGGER_HINTS = ("use when", "use for", "use this skill", "trigger when", "triggers on")
INVARIANT_HEADINGS = ("core rules", "cross-cutting invariants", "invariants")

# Prose file globs the loop-marker check scopes to (references/loop-contract.md
# "prose skill file" set). Scripts are excluded — vocabulary like "budget" or
# "retry" in code/CLI help is normal implementation detail, not a loop
# declaration; see the known-non-matches in --self-test.
LOOP_MARKER_PROSE_GLOBS = ("SKILL.md", "recipes/*.md", "modes/*.md", "references/*.md")

# >=2 distinct markers (each counted once even if repeated) trips the WARN.
# Deliberately narrow phrases, not bare words like "loop" or "budget" alone —
# those false-positive on ordinary prose (a "feedback loop", a cost "budget").
LOOP_MARKERS = (
    "iteration cap",
    "max_iterations",
    "max iterations",
    "re-audit round",
    "re-audit rounds",
    "convergence loop",
    "scheduleWakeup".lower(),
    "wakeup",
    "stop condition",
    "stop_conditions",
    "stopping rule",
    "ratchet loop",
    "keep/discard",
    "budget exhaustion",
    "loop budget",
)
LOOP_CONTRACT_CITATION_HINTS = ("loop-contract.md", "loop_contract")

# Resolver-parity check (task A5): broad on purpose — a line naming either
# runtime's personal-skill or plugin install path for project-meta. False
# positives just WARN (advisory), never FAIL.
RESOLVER_TRIGGER_RE = re.compile(r"\.(?:claude|codex)/skills/project-meta|\.(?:claude|codex)/plugins/\S*project-meta")
RESOLVER_CODEX_RE = re.compile(r"\.codex/(?:skills/project-meta|plugins/\S*project-meta)")
RESOLVER_SCOPED_CACHE_RE = re.compile(r"plugins/cache/\S*project-meta")
RESOLVER_CITATION_HINT = "shared-cli-delegation"
RESOLVER_WINDOW = 10  # lines of context on each side of a trigger line

# Files carrying a deliberately partial resolver mention (e.g. a single
# install command) rather than the full dual-runtime snippet, verified to
# already point at the canonical doc — add entries as "skills/<skill>/<rel>"
# when a real exception is confirmed, not to silence an unreviewed WARN.
RESOLVER_PARITY_ALLOWLIST: tuple[str, ...] = ()


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

    findings.extend(loop_marker_findings(skill_dir))
    findings.extend(resolver_parity_findings(skill_dir))

    return findings


def _prose_files(skill_dir: Path) -> list[Path]:
    """Every prose skill file the loop-marker check scopes to (references/
    loop-contract.md "prose skill file" set): SKILL.md plus recipes/modes/
    references markdown. Scripts are excluded on purpose (see module docstring)."""
    out: list[Path] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        out.append(skill_md)
    for sub in ("recipes", "modes", "references"):
        d = skill_dir / sub
        if d.is_dir():
            out.extend(sorted(d.glob("*.md")))
    return out


def loop_marker_findings(skill_dir: Path) -> list[Finding]:
    """WARN (never FAIL) on a prose file that reads like a loop declaration
    (>=2 distinct LOOP_MARKERS) but does not cite loop-contract.md. Scoped to
    prose files only; a precision heuristic, not a classifier — see
    references/loop-contract.md and --self-test's known-non-matches."""
    findings: list[Finding] = []
    for path in _prose_files(skill_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        hits = sorted({m for m in LOOP_MARKERS if m in low})
        if len(hits) < 2:
            continue
        cited = any(h in low for h in LOOP_CONTRACT_CITATION_HINTS)
        rel = path.relative_to(skill_dir)
        if cited:
            findings.append(
                Finding(f"loop declaration: {rel}", "PASS", f"cites loop-contract.md (markers: {', '.join(hits)})")
            )
        else:
            findings.append(
                Finding(
                    f"loop declaration: {rel}",
                    "WARN",
                    f"declares a loop (markers: {', '.join(hits)}) without citing loop-contract.md",
                )
            )
    return findings


def resolver_parity_findings(skill_dir: Path) -> list[Finding]:
    """WARN (never FAIL) on an embedded project-meta resolver snippet whose
    surrounding block shows neither a Codex-tier path nor a scoped-cache path,
    and does not cite shared-cli-delegation.md (the canonical resolver order,
    project-meta/references/shared-cli-delegation.md). Scans all skill
    markdown (not just the prose-file subset the loop-marker check uses),
    since resolver snippets also live in templates/ and hook docs."""
    findings: list[Finding] = []
    for path in sorted(skill_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        trigger_idxs = [i for i, ln in enumerate(lines) if RESOLVER_TRIGGER_RE.search(ln)]
        if not trigger_idxs:
            continue
        rel_label = f"skills/{skill_dir.name}/{path.relative_to(skill_dir).as_posix()}"
        if rel_label in RESOLVER_PARITY_ALLOWLIST:
            continue
        # Merge trigger lines that share overlapping +-WINDOW context into
        # one block so a multi-line resolver snippet is not double-counted.
        blocks: list[list[int]] = []
        for i in trigger_idxs:
            lo, hi = max(0, i - RESOLVER_WINDOW), min(len(lines) - 1, i + RESOLVER_WINDOW)
            if blocks and lo <= blocks[-1][1] + 1:
                blocks[-1][1] = max(blocks[-1][1], hi)
            else:
                blocks.append([lo, hi])
        for lo, hi in blocks:
            block_text = "\n".join(lines[lo : hi + 1]).lower()
            has_codex = bool(RESOLVER_CODEX_RE.search(block_text))
            has_scoped_cache = bool(RESOLVER_SCOPED_CACHE_RE.search(block_text))
            cites_canonical = RESOLVER_CITATION_HINT in block_text
            if not has_codex and not has_scoped_cache and not cites_canonical:
                findings.append(
                    Finding(
                        f"resolver parity: {rel_label}:{lo + 1}",
                        "WARN",
                        "embedded project-meta resolver has no .codex path, no scoped-cache "
                        "path, and doesn't cite shared-cli-delegation.md — likely drifted "
                        "from the dual-runtime resolver in verify-before-stop.sh",
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


# Known-non-matches (references/loop-contract.md precision requirement,
# DASH-059/060): real repo files with loop-adjacent vocabulary that must NOT
# WARN — either because they don't clear the >=2-marker bar (checked directly
# below) or because they are scripts, not prose, and out of scope entirely.
KNOWN_NON_MATCHES = (
    "skills/openclaw-devops/references/runbook.md",  # cycle polling loop (cron cadence prose, not a loop-marker vocabulary)
    "skills/meta-debug/references/debug-pipeline.md",  # retry/loop_count helper prose; only 1 marker ("loop budget") — below the bar
    "skills/project-meta/references/multi-agent-protocols.md",  # dispatch_ledger budget/checkpoint fields; no iteration-cap/stop-condition vocabulary
)


def _self_test() -> int:
    import tempfile

    fails: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        if not cond:
            fails.append(f"{name}{': ' + detail if detail else ''}")

    # 1. Synthetic fixture: a prose reference file with >=2 loop markers and
    #    no citation must WARN.
    with tempfile.TemporaryDirectory() as td:
        skill_dir = Path(td) / "synthetic-skill"
        (skill_dir / "references").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: synthetic-skill\ndescription: \"test. Use when testing.\"\n---\n\n# Synthetic\n",
            encoding="utf-8",
        )
        (skill_dir / "references" / "undeclared-loop.md").write_text(
            "# Undeclared Loop\n\n"
            "This mode runs a convergence loop with an iteration cap of 5, "
            "checking a stop condition after each pass.\n",
            encoding="utf-8",
        )
        findings = loop_marker_findings(skill_dir)
        warn = [f for f in findings if f.status == "WARN"]
        check("synthetic fixture WARNs", len(warn) == 1, f"got {findings}")

        # citing loop-contract.md flips it to PASS
        (skill_dir / "references" / "undeclared-loop.md").write_text(
            "# Declared Loop\n\n"
            "See [`project-meta/references/loop-contract.md`](../../project-meta/references/loop-contract.md). "
            "This mode runs a convergence loop with an iteration cap of 5, "
            "checking a stop condition after each pass.\n",
            encoding="utf-8",
        )
        findings2 = loop_marker_findings(skill_dir)
        check(
            "cited fixture does not WARN",
            all(f.status != "WARN" for f in findings2) and any(f.status == "PASS" for f in findings2),
            f"got {findings2}",
        )

    # 2. Known-non-matches: real repo files must not WARN.
    repo_root = Path(__file__).resolve().parents[3]
    for rel in KNOWN_NON_MATCHES:
        path = repo_root / rel
        if not path.is_file():
            fails.append(f"known-non-match fixture missing from repo: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        hits = sorted({m for m in LOOP_MARKERS if m in low})
        check(f"known-non-match clean: {rel}", len(hits) < 2, f"unexpectedly hit markers {hits}")

    if fails:
        for f in fails:
            print(f"SELF-TEST FAIL {f}", file=sys.stderr)
        return 1
    print(f"SELF-TEST PASS (loop-marker precision: 1 synthetic WARN + 1 citation PASS + {len(KNOWN_NON_MATCHES)} known-non-match(es) clean)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", help="A skill directory (with SKILL.md) or a marketplace root (with skills/)")
    parser.add_argument("--self-test", action="store_true", help="run the loop-marker precision self-test (no path needed)")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.path:
        print("path is required unless --self-test is passed", file=sys.stderr)
        return 2

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
