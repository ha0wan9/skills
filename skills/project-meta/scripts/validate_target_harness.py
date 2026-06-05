#!/usr/bin/env python3
"""Validate a target repository's Project Meta harness.

Run this from the installed skill against a target project repo:

    python3 <skill-install-dir>/scripts/validate_target_harness.py [target_repo]

If `target_repo` is omitted, the script walks up from the current working
directory to find the nearest `.git` ancestor. The validator is intentionally
dependency-free and uses only the Python standard library.

Checks (each marked PASS, WARN, or FAIL):

- AGENTS.md present at the target repo root.
- USER.md is git-ignored (or absent).
- README structure map exists when README is long.
- Every `agents/*.md` artifact carries Project Meta provenance frontmatter
  when its filename matches a known template seed.
- Mirror files (`CLAUDE.md`, `.github/copilot-instructions.md`) do not contain
  rules that are missing from AGENTS.md.
- Execution rules are present when AGENTS.md mentions bounded-execution
  agents, hard stops, or `agents/execution-rules.md`.
- Issue-tracker capability, when installed, is fully wired: the doc is routed
  from canonical memory and the advisory hook (if present) has its doc and is
  wired in settings.json. A half-installed capability is a FAIL.

This validator does not enforce runtime safety. It checks that the *policy*
artifacts a target repo should ship are present and well-formed. Runtime
enforcement is the job of Claude Code permissions/hooks, Codex approval
modes, or repo-side pre-commit/CI gates.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


KNOWN_INSTANTIATED_ARTIFACTS = {
    "agents/delegation.md",
    "agents/pre-commit-delivery.md",
    "agents/readme-structure.md",
    "agents/memory-writeback-check.md",
    "agents/project-artifacts.md",
    "agents/execution-rules.md",
    "agents/issue-tracking.md",
}

REQUIRED_PROVENANCE_FIELDS = (
    "artifact_name",
    "instantiated_from",
    "source_reference",
    "project_scope",
    "owner",
    "review_policy",
    "last_reviewed",
)

EXECUTION_RULES_SIGNALS = (
    "execution-rules",
    "Execution Rules",
    "MUST STOP",
    "SHOULD ASK",
    "halt and ask",
    "bounded-execution",
)

LONG_README_LINE_THRESHOLD = 200


@dataclass
class Finding:
    name: str
    status: str  # PASS, WARN, FAIL
    message: str = ""

    def render(self) -> str:
        if self.message:
            return f"{self.status} {self.name}: {self.message}"
        return f"{self.status} {self.name}"


def discover_target_root(arg: str | None) -> Path:
    if arg:
        candidate = Path(arg).resolve(strict=True)
        if not candidate.is_dir():
            raise ValueError(f"target must be a directory: {candidate}")
        return candidate
    cwd = Path.cwd().resolve()
    for parent in (cwd, *cwd.parents):
        if (parent / ".git").exists():
            return parent
    return cwd


# Intentionally NOT delegated to provenance.parse_scalars: this flattens ALL
# keys including indented/nested ones, whereas parse_scalars is top-level only.
# Different semantics — keep local to avoid a behavior change.
def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def git_ignores(root: Path, path: str) -> bool | None:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=root,
        )
    except FileNotFoundError:
        return None
    if result.returncode == 128:
        return None
    return result.returncode == 0


def check_agents_md(root: Path) -> Finding:
    if (root / "AGENTS.md").is_file():
        return Finding("AGENTS.md present", "PASS")
    return Finding(
        "AGENTS.md present",
        "FAIL",
        "AGENTS.md is missing at the target repo root",
    )


def check_user_md_ignored(root: Path) -> Finding:
    user_md = root / "USER.md"
    if not user_md.exists():
        return Finding(
            "USER.md handling",
            "PASS",
            "USER.md absent (will be created locally during init)",
        )
    ignored = git_ignores(root, "USER.md")
    if ignored is None:
        return Finding(
            "USER.md handling",
            "WARN",
            "could not determine git ignore status (no git working tree?)",
        )
    if ignored:
        return Finding("USER.md handling", "PASS", "USER.md is git-ignored")
    return Finding(
        "USER.md handling",
        "FAIL",
        "USER.md exists but is NOT git-ignored; add /USER.md to .gitignore",
    )


def check_readme_structure_map(root: Path) -> Finding:
    readme = root / "README.md"
    if not readme.is_file():
        return Finding(
            "README structure map",
            "PASS",
            "no README.md to route (skipping)",
        )
    line_count = sum(1 for _ in readme.open("r", encoding="utf-8", errors="replace"))
    if line_count <= LONG_README_LINE_THRESHOLD:
        return Finding(
            "README structure map",
            "PASS",
            f"README.md is short ({line_count} lines); no structure map required",
        )
    structure_paths = (
        root / "agents" / "readme-structure.md",
        root / "AGENTS.md",
    )
    for path in structure_paths:
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if "README" in text and ("Structure" in text or "structure-map" in text):
                return Finding(
                    "README structure map",
                    "PASS",
                    f"long README ({line_count} lines) routed via {path.relative_to(root)}",
                )
    return Finding(
        "README structure map",
        "WARN",
        f"README.md is long ({line_count} lines) but no agent-facing structure map "
        "found in agents/readme-structure.md or AGENTS.md",
    )


def check_artifact_provenance(root: Path) -> Finding:
    issues: list[str] = []
    for relative in sorted(KNOWN_INSTANTIATED_ARTIFACTS):
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        meta = parse_frontmatter(text)
        if meta is None:
            issues.append(f"{relative}: missing YAML frontmatter")
            continue
        missing = [field for field in REQUIRED_PROVENANCE_FIELDS if field not in meta]
        if missing:
            issues.append(f"{relative}: missing fields {missing}")
            continue
        instantiated_from = meta.get("instantiated_from", "")
        if not instantiated_from.startswith("project-meta/templates/"):
            issues.append(
                f"{relative}: instantiated_from should reference project-meta/templates/, got '{instantiated_from}'"
            )
    if issues:
        return Finding(
            "artifact provenance",
            "FAIL",
            "; ".join(issues),
        )
    return Finding(
        "artifact provenance",
        "PASS",
        "all known instantiated artifacts have provenance frontmatter (or are absent)",
    )


def check_mirror_alignment(root: Path) -> Finding:
    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        return Finding(
            "mirror alignment",
            "WARN",
            "AGENTS.md missing; cannot compare mirrors against canonical",
        )
    agents_text = agents_path.read_text(encoding="utf-8", errors="replace").lower()
    mirrors = (
        root / "CLAUDE.md",
        root / ".github" / "copilot-instructions.md",
    )
    issues: list[str] = []
    for mirror in mirrors:
        if not mirror.is_file():
            continue
        mirror_text = mirror.read_text(encoding="utf-8", errors="replace")
        for line in mirror_text.splitlines():
            stripped = line.strip()
            if len(stripped) < 30:
                continue
            if not stripped.startswith("-") and not stripped.startswith("*"):
                continue
            words = re.findall(r"[A-Za-z]{6,}", stripped.lower())
            if not words:
                continue
            distinctive = [w for w in words if w not in {"agents", "memory", "project", "should"}]
            if not distinctive:
                continue
            sample = distinctive[0]
            if sample not in agents_text:
                issues.append(
                    f"{mirror.relative_to(root)}: rule mentioning '{sample}' "
                    "is not present in AGENTS.md"
                )
                break
    if issues:
        return Finding(
            "mirror alignment",
            "WARN",
            "; ".join(issues),
        )
    return Finding(
        "mirror alignment",
        "PASS",
        "mirrors do not appear to introduce rules absent from AGENTS.md",
    )


def check_execution_rules(root: Path) -> Finding:
    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        return Finding(
            "execution rules",
            "WARN",
            "AGENTS.md missing; cannot determine whether execution rules are required",
        )
    agents_text = agents_path.read_text(encoding="utf-8", errors="replace")
    artifact_path = root / "agents" / "execution-rules.md"
    artifact_present = artifact_path.is_file()
    artifact_referenced = "execution-rules" in agents_text or "execution rules" in agents_text.lower()
    needs_execution_rules = any(
        signal in agents_text or signal in agents_text.lower()
        for signal in EXECUTION_RULES_SIGNALS
    )
    if artifact_present and artifact_referenced:
        return Finding(
            "execution rules",
            "PASS",
            "agents/execution-rules.md present and referenced from AGENTS.md",
        )
    if artifact_present and not artifact_referenced:
        return Finding(
            "execution rules",
            "WARN",
            "agents/execution-rules.md exists but AGENTS.md does not reference it",
        )
    if needs_execution_rules and not artifact_present:
        return Finding(
            "execution rules",
            "FAIL",
            "AGENTS.md mentions execution rules / bounded-execution agents but "
            "agents/execution-rules.md is missing",
        )
    return Finding(
        "execution rules",
        "PASS",
        "no execution-rules signal in AGENTS.md; artifact not required",
    )


def check_issue_tracker(root: Path) -> Finding:
    """Issue-tracker capability integrity: a capability is on iff fully wired.

    - Not installed (no doc, no hook) -> PASS (skipped).
    - Doc present but not routed from canonical memory -> FAIL (half-install).
    - Reminder hook present without its doc -> FAIL (hook without workflow).
    - Reminder hook present but not wired in settings.json -> WARN.
    Provenance of agents/issue-tracking.md is covered by check_artifact_provenance.
    """
    doc = root / "agents" / "issue-tracking.md"
    hook = root / ".claude" / "hooks" / "issue-tracker-reminder.sh"
    doc_present = doc.is_file()
    hook_present = hook.is_file()

    if not doc_present and not hook_present:
        return Finding(
            "issue-tracker capability",
            "PASS",
            "not installed (skipping)",
        )

    issues: list[str] = []

    if hook_present and not doc_present:
        issues.append(
            "reminder hook installed but agents/issue-tracking.md is missing "
            "(hook without workflow)"
        )

    if doc_present:
        routed = False
        for memory_name in ("AGENTS.md", "CLAUDE.md"):
            memory = root / memory_name
            if memory.is_file():
                text = memory.read_text(encoding="utf-8", errors="replace")
                # Require a pointer to the artifact path, not the bare stem — an
                # incidental mention of "issue-tracking" must not count as routing.
                if "agents/issue-tracking.md" in text:
                    routed = True
                    break
        if not routed:
            issues.append(
                "agents/issue-tracking.md present but not routed (no pointer to "
                "agents/issue-tracking.md in AGENTS.md / CLAUDE.md) — half-install"
            )

    if issues:
        return Finding("issue-tracker capability", "FAIL", "; ".join(issues))

    if hook_present:
        settings = root / ".claude" / "settings.json"
        wired = (
            settings.is_file()
            and "issue-tracker-reminder" in settings.read_text(
                encoding="utf-8", errors="replace"
            )
        )
        if not wired:
            return Finding(
                "issue-tracker capability",
                "WARN",
                "reminder hook script present but not wired under UserPromptSubmit "
                "in .claude/settings.json",
            )

    return Finding(
        "issue-tracker capability",
        "PASS",
        "installed and wired (doc routed" + (", hook wired" if hook_present else "") + ")",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Target repository root (default: walk up from cwd to nearest .git)",
    )
    args = parser.parse_args(argv)

    try:
        root = discover_target_root(args.target)
    except (FileNotFoundError, ValueError) as exc:
        print(f"could not resolve target repo root: {exc}", file=sys.stderr)
        return 2

    print(f"target: {root}")
    findings = [
        check_agents_md(root),
        check_user_md_ignored(root),
        check_readme_structure_map(root),
        check_artifact_provenance(root),
        check_mirror_alignment(root),
        check_execution_rules(root),
        check_issue_tracker(root),
    ]
    for finding in findings:
        print(finding.render())
    failed = [f for f in findings if f.status == "FAIL"]
    warned = [f for f in findings if f.status == "WARN"]
    print()
    print(f"summary: {len(findings) - len(failed) - len(warned)} pass, {len(warned)} warn, {len(failed)} fail")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
