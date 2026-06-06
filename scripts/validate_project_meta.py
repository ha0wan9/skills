#!/usr/bin/env python3
"""Minimal validation suite for the project-meta skill.

The checks intentionally use only the Python standard library so they can run in
fresh repos without installing PyYAML or a test framework.
"""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "project-meta"
# Files inside the installable project-meta skill resolve under SKILL_ROOT.
# Repo-meta files (`README.md`, `AGENTS.md`, repo `.gitignore`) resolve under
# REPO_ROOT — the marketplace root that hosts multiple skills.
# Git invocations target REPO_ROOT because the working tree is at that level.
ROOT = SKILL_ROOT

REQUIRED_REFERENCES = {
    "references/project-lifecycle.md",
    "references/agent-behavior-protocol.md",
    "references/cli-command-patterns.md",
    "references/documentation-delivery.md",
    "references/execution-policy.md",
    "references/repo-memory-structure.md",
    "references/repo-memory-crud.md",
    "references/mirrors-and-updates.md",
    "references/harness-engineering.md",
    "references/multi-agent-protocols.md",
}

REQUIRED_TEMPLATES = {
    "templates/delegation.md": "references/multi-agent-protocols.md",
    "templates/execution-rules.md": "references/execution-policy.md",
    "templates/memory-writeback-check.md": "references/repo-memory-crud.md",
    "templates/pre-commit-delivery.md": "references/documentation-delivery.md",
    "templates/project-artifact-manifest.md": "references/documentation-delivery.md",
    "templates/readme-structure-map.md": "references/repo-memory-structure.md",
    "templates/user-preferences.md": "references/project-lifecycle.md",
}

LOCAL_USER_TEMPLATE = "templates/user-preferences.md"
FORBIDDEN_PROJECT_TEMPLATE_PREFIX = "agents/templates/"

# After the recipe split (one file per verb), the route table maps verb -> recipe
# and each recipe owns its own "Required references" section. `required_refs` are
# therefore validated against the recipe file `recipes/<verb>.md`, not the route row.
COMMAND_ROUTE_EXPECTATIONS = {
    "/project-meta init": {
        "mode": "editing",
        "required_refs": (
            "project-lifecycle",
            "repo-memory-structure",
            "repo-memory-crud",
            "documentation-delivery",
            "execution-policy",
        ),
    },
    "/project-meta status": {
        "mode": "read-only",
        "required_refs": (
            "repo-memory-structure",
            "mirrors-and-updates",
        ),
    },
    "/project-meta validate": {
        "mode": "read-only",
        "required_refs": (
            "harness-engineering",
            "repo-memory-structure",
            "anti-patterns",
            "skill-critics",
        ),
    },
    "/project-meta deliver": {
        "mode": "read-only",
        "required_refs": (
            "documentation-delivery",
            "multi-agent-protocols",
            "multi-host-manifests",
        ),
    },
    "/project-meta audit": {
        "mode": "read-only by default",
        "required_refs": (
            "harness-engineering",
            "anti-patterns",
            "repo-memory-structure",
        ),
    },
}


class CheckError(AssertionError):
    pass


@dataclass(frozen=True)
class TriggerCase:
    name: str
    prompt: str
    should_use: bool
    expected_refs: tuple[str, ...] = ()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def parse_simple_frontmatter(text: str) -> dict[str, str]:
    require(text.startswith("---\n"), "SKILL.md must start with YAML frontmatter")
    end = text.find("\n---", 4)
    require(end != -1, "SKILL.md frontmatter must close with ---")
    return parse_key_value_block(text[4:end], "frontmatter")


def parse_key_value_block(text: str, context: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        require(
            not raw_line.startswith((" ", "\t", "-")),
            f"{context} must contain only top-level scalar key/value lines: {raw_line}",
        )
        require(":" in raw_line, f"Invalid frontmatter line: {raw_line}")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        require(key, f"{context} contains an empty key")
        require(value, f"{context} key {key!r} must have a scalar value")
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        result[key] = value
    return result


def extract_fenced_block_after_heading(text: str, heading: str, language: str = "yaml") -> str:
    heading_index = text.find(heading)
    require(heading_index != -1, f"Missing heading: {heading}")
    pattern = re.compile(r"```" + re.escape(language) + r"\n(.*?)\n```", re.DOTALL)
    match = pattern.search(text, heading_index)
    require(match is not None, f"Missing {language} fenced block after {heading}")
    return match.group(1)


def parse_simple_openai_yaml(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped == "interface:":
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        result[key.strip()] = value
    return result


def linked_references(skill_md: str) -> set[str]:
    return set(re.findall(r"\]\((references/[^)]+\.md)\)", skill_md))


def git_tracked_files() -> set[str] | None:
    """Return tracked files, or None if not in a git working tree.

    The skill ships with this validator and may be executed from an installed
    location that is not a git checkout. Outside a git working tree, return
    None so callers can skip git-dependent checks instead of raising.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return set(result.stdout.splitlines())


def git_ignores(path: str) -> bool | None:
    """Return whether path is git-ignored, or None outside a git working tree."""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=REPO_ROOT,
        )
    except FileNotFoundError:
        return None
    if result.returncode == 128:
        return None
    return result.returncode == 0


def run_python_script(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=cwd or ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_python_script_result(
    *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )


def classify_prompt(prompt: str) -> tuple[bool, set[str]]:
    """Small heuristic model of project-meta trigger/routing behavior."""
    p = prompt.lower()
    refs: set[str] = set()
    use = False

    bootstrap_terms = ("start work in this repo", "bootstrap", "cold repo", "new repo")
    memory_terms = ("agents.md", "user.md", "repo memory", "canonical memory", "mirror")
    harness_terms = ("agent instructions", "harness", "guardrails", "behavior protocol")
    lifecycle_terms = ("iterate", "project lifecycle", "validated lesson", "durable lesson")
    multi_terms = ("multi-agent", "sub-agent", "delegated", "planning/review")
    cli_commands = set(COMMAND_ROUTE_EXPECTATIONS)

    if any(command in p for command in cli_commands):
        use = True
        refs.add("references/cli-command-patterns.md")
    if "/project-meta init" in p or any(term in p for term in bootstrap_terms):
        use = True
        refs.add("references/project-lifecycle.md")
    if "/project-meta deliver" in p:
        use = True
        refs.add("references/documentation-delivery.md")
    if "/project-meta audit" in p:
        use = True
        refs.add("references/harness-engineering.md")
    if any(term in p for term in memory_terms):
        use = True
        refs.update(
            {
                "references/repo-memory-structure.md",
                "references/repo-memory-crud.md",
            }
        )
    if "mirror" in p or "claude.md" in p or "copilot" in p:
        use = True
        refs.add("references/mirrors-and-updates.md")
    if any(term in p for term in harness_terms):
        use = True
        refs.update(
            {
                "references/harness-engineering.md",
                "references/agent-behavior-protocol.md",
            }
        )
    if any(term in p for term in lifecycle_terms):
        use = True
        refs.add("references/project-lifecycle.md")
    if any(term in p for term in multi_terms):
        use = True
        refs.add("references/multi-agent-protocols.md")

    ordinary_terms = ("fix a bug", "implement the api", "change the button", "add endpoint")
    if not use and any(term in p for term in ordinary_terms):
        return False, set()

    return use, refs


TRIGGER_CASES = (
    TriggerCase(
        name="explicit init command",
        prompt="/project-meta init",
        should_use=True,
        expected_refs=("references/cli-command-patterns.md", "references/project-lifecycle.md"),
    ),
    TriggerCase(
        name="status command",
        prompt="/project-meta status",
        should_use=True,
        expected_refs=("references/cli-command-patterns.md",),
    ),
    TriggerCase(
        name="deliver command",
        prompt="/project-meta deliver",
        should_use=True,
        expected_refs=("references/cli-command-patterns.md", "references/documentation-delivery.md"),
    ),
    TriggerCase(
        name="audit command",
        prompt="/project-meta audit",
        should_use=True,
        expected_refs=("references/cli-command-patterns.md", "references/harness-engineering.md"),
    ),
    TriggerCase(
        name="bootstrap cold repo",
        prompt="Start work in this repo cold and bootstrap the project memory.",
        should_use=True,
        expected_refs=("references/project-lifecycle.md",),
    ),
    TriggerCase(
        name="repair canonical memory",
        prompt="Repair AGENTS.md and USER.md so canonical memory is clean.",
        should_use=True,
        expected_refs=(
            "references/repo-memory-structure.md",
            "references/repo-memory-crud.md",
        ),
    ),
    TriggerCase(
        name="sync mirrors",
        prompt="Sync CLAUDE.md and copilot mirror guidance after AGENTS.md changed.",
        should_use=True,
        expected_refs=("references/mirrors-and-updates.md",),
    ),
    TriggerCase(
        name="behavior guardrails",
        prompt="Improve the agent instructions with behavior protocol guardrails.",
        should_use=True,
        expected_refs=("references/agent-behavior-protocol.md",),
    ),
    TriggerCase(
        name="multi-agent explicit",
        prompt="Use multi-agent planning/review with sub-agent delegation.",
        should_use=True,
        expected_refs=("references/multi-agent-protocols.md",),
    ),
    TriggerCase(
        name="ordinary implementation",
        prompt="Fix a bug in the API handler without changing project memory.",
        should_use=False,
    ),
)


def check_required_files() -> None:
    # Repo-meta files live at the dev repo root, outside the installable skill.
    for path in ("README.md", "AGENTS.md", "scripts/validate_project_meta.py"):
        require((REPO_ROOT / path).is_file(), f"Missing required repo file: {path}")
    # Skill content lives under skill/.
    for path in (
        ".gitignore.template",
        "SKILL.md",
        "USER.template.md",
        "agents/openai.yaml",
        "scripts/extract_doc_context.py",
        "scripts/board.py",
        "scripts/render_user_preferences.py",
        "scripts/validate_target_harness.py",
        "templates/board.dashboard.html",
        *sorted(REQUIRED_TEMPLATES),
        *sorted(REQUIRED_REFERENCES),
    ):
        require((ROOT / path).is_file(), f"Missing required file: {path}")


def check_skill_metadata() -> None:
    skill = read("SKILL.md")
    meta = parse_simple_frontmatter(skill)
    require(meta.get("name") == "project-meta", "SKILL.md name must be project-meta")
    description = meta.get("description", "")
    require(description, "SKILL.md description is required")
    require(len(description) <= 1024, "SKILL.md description exceeds 1024 chars")
    require("<" not in description and ">" not in description, "Description uses angle brackets")
    for token in (
        "agent-work harness",
        "/project-meta commands",
        "/project-meta init",
        "AGENTS.md",
        "USER.md",
        "preference presets",
        "existing agent-facing documentation framework",
        "user-facing documentation delivery",
        "canonical templates",
        "project-level artifact instantiation",
        "trigger policy",
        "behavior guardrails",
        "multi-agent",
        "pre-commit delivery",
        "mirror sync",
        "durable knowledge",
    ):
        require(token in description, f"Description missing trigger token: {token}")


def check_marketplace_description_sync() -> None:
    """The project-meta SKILL.md description is canonical; the marketplace plugin
    entry must copy it verbatim and carry a version. Prevents the manifest from
    silently drifting away from the skill's trigger text (the drift that lets
    install-time discovery and trigger-time matching diverge)."""
    skill_desc = parse_simple_frontmatter(read("SKILL.md")).get("description", "")
    manifest = json.loads(read_repo(".claude-plugin/marketplace.json"))
    plugins = {p.get("name"): p for p in manifest.get("plugins", [])}
    require("project-meta" in plugins, "marketplace.json missing project-meta plugin entry")
    entry = plugins["project-meta"]
    require(
        entry.get("description") == skill_desc,
        "marketplace.json project-meta description must match SKILL.md verbatim "
        "(re-copy the SKILL.md description into the plugin entry)",
    )
    require(entry.get("version"), "marketplace.json project-meta entry must declare a version")


def check_reference_routing() -> None:
    skill = read("SKILL.md")
    links = linked_references(skill)
    missing_links = REQUIRED_REFERENCES - links
    require(not missing_links, f"SKILL.md missing reference links: {sorted(missing_links)}")
    for link in links:
        require((ROOT / link).is_file(), f"SKILL.md links missing reference: {link}")


def check_memory_boundaries() -> None:
    agents = read_repo("AGENTS.md")
    user_template = read("USER.template.md")
    gitignore = read_repo(".gitignore")
    gitignore_template = read(".gitignore.template")
    tracked = git_tracked_files()
    require("USER.md" in agents, "AGENTS.md must route stable user preferences to USER.md")
    require(
        "Multi-agent protocols should be triggerable" not in agents,
        "AGENTS.md should not store the stable multi-agent user preference",
    )
    require(
        "rtk is installed" not in agents.lower(),
        "AGENTS.md should not store local RTK installation state",
    )
    require(
        "read it selectively at cold start" in agents,
        "AGENTS.md must keep README loading lightweight at cold start",
    )
    require(
        "skills/project-meta/scripts/extract_doc_context.py" in agents,
        "AGENTS.md must mention the bounded doc context extractor",
    )
    require(
        "skills/project-meta/scripts/render_user_preferences.py" in agents,
        "AGENTS.md must mention the user preference renderer",
    )
    require("/USER.md" in gitignore, ".gitignore must ignore root local USER.md")
    require("/USER.md" in gitignore_template, ".gitignore.template must ignore root local USER.md")
    require(
        "/USER.template.md" in gitignore_template,
        ".gitignore.template must ignore accidental root USER.template.md in target projects",
    )
    if tracked is not None:
        require("USER.md" not in tracked, "USER.md must not be tracked by Git")
        require(
            "skills/project-meta/USER.template.md" in tracked,
            "skills/project-meta/USER.template.md must be tracked by Git",
        )
    ignored = git_ignores("skills/project-meta/.gitignore.template")
    if ignored is not None:
        require(
            not ignored,
            "skills/project-meta/.gitignore.template must be visible to Git so it can be committed",
        )
    require(
        "Do not copy or commit this file into target project repositories by default" in user_template,
        "USER.template.md must state it is not copied into target projects by default",
    )
    require(
        "target-config input" in user_template and "questionnaire source" in user_template,
        "USER.template.md must act as target-config input and questionnaire source",
    )
    require(
        "Do not copy this template body verbatim into `USER.md`" in user_template,
        "USER.template.md must forbid verbatim copying into USER.md",
    )
    require(
        "Mark selected preferences with `[x]`" in user_template,
        "USER.template.md must require checked selected preferences",
    )
    require(
        "Omit unselected checklist items" in user_template,
        "USER.template.md must prevent exposing unselected checklist items by default",
    )


def check_protocol_completeness() -> None:
    cli = read("references/cli-command-patterns.md")
    for token in (
        "Canonical Route Contract",
        "Recipe Directory",
        "/project-meta init",
        "/project-meta status",
        "/project-meta validate",
        "/project-meta deliver",
        "/project-meta audit",
        "Reserved Commands",
        "not a separate shell binary",
        "command routing and workflow contracts are canonical here",
        "Implementation Risks",
        "Command surface bloat",
    ):
        require(token in cli, f"CLI command patterns missing: {token}")
    # The USER.md reset/update route moved into the init recipe during the recipe split.
    init_recipe = read("recipes/init.md")
    require(
        "scripts/render_user_preferences.py --target-root <repo> --reset" in init_recipe,
        "init recipe must route USER.md reset/update to the renderer",
    )

    multi = read("references/multi-agent-protocols.md")
    for token in (
        "Explicit trigger",
        "Complexity trigger",
        "at least two signals",
        "Delegation Template",
        "Ownership:",
        "Review criteria:",
        "Memory policy:",
        "Review Mechanism",
        "Integration Checklist",
    ):
        require(token in multi, f"multi-agent protocol missing: {token}")

    behavior = read("references/agent-behavior-protocol.md")
    for token in (
        "Think before editing",
        "Keep it simple",
        "Make surgical changes",
        "Stay goal-driven",
        "Success Criteria Template",
    ):
        require(token in behavior, f"behavior protocol missing: {token}")

    execution = read("references/execution-policy.md")
    for token in (
        "Three Tiers",
        "MUST STOP",
        "SHOULD ASK",
        "MAY PROCEED WITH NOTE",
        "Soft Budgets",
        "Codex-Class Worker Constraints",
        "Relationship To Runtime Enforcement",
        "Destructive operations",
        "Network commands",
        "Dependency changes",
        "Structural renames",
        "Scope expansion",
        "is not a runtime sandbox",
        "Unclear target files",
        "File modification under a read-only command",
        "claim correctness when validation cannot be run",
    ):
        require(token in execution, f"execution policy missing: {token}")

    execution_template = read("templates/execution-rules.md")
    for token in (
        "target files are unclear",
        "read-only workflow",
        "claim correctness when validation cannot be run",
    ):
        require(
            token in execution_template,
            f"execution-rules template missing: {token}",
        )

    structure = read("references/repo-memory-structure.md")
    for token in (
        "Shared Docs Loading Policy",
        "README Structure Map",
        "agents/readme-structure.md",
        "routing aid",
        "heading-first bounded extractor",
        "heading map",
        "Read targeted sections",
        "Primary means authoritative",
        "eager full-context loading",
    ):
        require(token in structure, f"repo memory structure missing: {token}")

    lifecycle = read("references/project-lifecycle.md")
    for token in (
        "Init Command",
        "/project-meta init",
        "Preference Presets",
        ".gitignore.template",
        "Project Type Artifact Map",
        "Artifact Instantiation Rules",
        "Interactive User Preference Rendering",
        "target-config input",
        "Generate target-root `USER.md` with only the selected preset",
        "Omit unselected items unless the user asks for an editable full checklist",
        "Use the same rendering flow when the user later asks to reset or change `USER.md` options",
        "scripts/render_user_preferences.py --target-root <repo> --reset",
        "Do not copy its original body into the target repo",
        "do not create a target-repo `USER.template.md`",
        "application or service",
        "standalone skill or agent-harness repo",
        "Skill-level templates are canonical seeds; project-level outputs are concrete project artifacts, not templates.",
        "agents/project-artifacts.md",
        "Minimal",
        "Structured",
        "Strict",
        "Secure",
        "Bootstrap",
        "Operate",
        "Observe",
        "Promote",
        "Prune",
        "Safety gates",
    ):
        require(token in lifecycle, f"project lifecycle missing: {token}")

    crud = read("references/repo-memory-crud.md")
    for token in (
        "Read the canonical memory files and the `README.md` structure map first.",
        "bounded extraction",
        "Load the full `README.md` only when",
    ):
        require(token in crud, f"repo memory CRUD read rule missing: {token}")
    require(
        "Read `README.md` and the canonical memory files first" not in crud,
        "repo memory CRUD must not regress to eager full README loading",
    )

    delivery = read("references/documentation-delivery.md")
    for token in (
        "Agent-facing project documentation",
        "Shared/user-facing documentation",
        "Shared/user-facing documentation is the primary documentation",
        "agent-only operational notes",
        "Existing Agent-Facing Framework",
        "Skill Layer Vs Project Layer",
        "Project Meta skill layer",
        "Installed or target project layer",
        "agents/readme-structure.md",
        "templates/*.md",
        "agents/templates/*.md",
        "Canonical Template Layer",
        "Project-Level Instantiated Artifacts",
        "Artifact Provenance Contract",
        "instantiated_from",
        "Do not create or commit a root `USER.template.md` in target projects by default",
        "skill-layer questionnaire and target-config input",
        "rendered interactively into ignored local `USER.md`",
        "mark selected preferences with `[x]`",
        "Collaboration Flow",
        "README structure map",
        "Primary does not require eager full loading",
        "Use shared project documentation as the primary project explanation",
        "Do not replace this framework",
        "Pre-Commit Delivery",
        "User-facing docs:",
        "Agent-facing docs:",
        "Commit scope:",
        "USER.md",
        ".gitignore.template",
    ):
        require(token in delivery, f"documentation delivery missing: {token}")


def check_command_route_contract() -> None:
    cli = read("references/cli-command-patterns.md")
    require(
        "| Command | Mode | Recipe |" in cli,
        "CLI command route table header is missing or changed",
    )
    require(
        "command routing and workflow contracts are canonical here" in cli,
        "CLI command patterns must declare canonical route ownership",
    )

    table_lines = [
        line
        for line in cli.splitlines()
        if line.startswith("| `/project-meta ") and line.rstrip().endswith("|")
    ]
    for command, expectation in COMMAND_ROUTE_EXPECTATIONS.items():
        matching = [line for line in table_lines if f"| `{command}` |" in line]
        require(matching, f"Missing route table row for {command}")
        row = matching[0]
        require(
            f"| {expectation['mode']} |" in row,
            f"{command} route mode must be {expectation['mode']}",
        )
        # The route table maps verb -> recipe; the recipe owns the references.
        verb = command.split()[-1]
        recipe_path = f"recipes/{verb}.md"
        require(
            recipe_path in row,
            f"{command} route table must link its recipe {recipe_path}",
        )
        recipe = read(recipe_path)
        for ref in expectation["required_refs"]:
            require(
                ref in recipe,
                f"{recipe_path} missing required reference: {ref}",
            )


def check_ui_metadata() -> None:
    meta = parse_simple_openai_yaml(read("agents/openai.yaml"))
    require(meta.get("display_name") == "Project Meta", "openai.yaml display_name mismatch")
    default_prompt = meta.get("default_prompt", "")
    require("/project-meta" in default_prompt, "default_prompt must mention /project-meta")
    require(
        "$project-meta" not in default_prompt,
        "default_prompt must not mention obsolete $project-meta syntax",
    )
    for token in (
        "/project-meta init",
        "status",
        "validate",
        "deliver",
        "audit",
        "agent-work harness",
        "preference presets",
        "existing agent-facing documentation framework",
        "user-facing delivery",
        "skill-level templates",
        "project-specific artifacts",
        "multi-agent",
        "pre-commit delivery",
        "durable lesson",
    ):
        require(token in default_prompt, f"default_prompt missing: {token}")


def check_readme_layout() -> None:
    """Validate the marketplace README surfaces project-meta usage.

    The marketplace README hosts multiple skills and is structurally lighter
    than the original project-meta-skill repo README. We check that it
    surfaces project-meta install/usage, references the marketplace.json
    plugin install path, and links to the skill's own SKILL.md for full
    detail.
    """
    readme = read_repo("README.md")
    for token in (
        ".claude-plugin/marketplace.json",
        "/plugin marketplace add",
        "/plugin install",
        "skills/project-meta",
        "skills/dl-research",
    ):
        require(token in readme, f"marketplace README missing {token}")
    for token in (
        "/project-meta init",
        "/project-meta status",
        "/project-meta validate",
        "/project-meta deliver",
        "/project-meta audit",
    ):
        require(
            token in readme,
            f"marketplace README must list project-meta command surface: {token}",
        )


def check_user_template_presets() -> None:
    template = read("USER.template.md")
    for token in (
        "/project-meta init",
        "Minimal",
        "Structured",
        "Strict",
        "Secure",
        "Custom",
        "Commit And Push",
        "Pre-Commit Delivery",
        "Documentation Mode",
        "Memory Writeback",
        "Multi-Agent",
        "Validation",
        "local-only user preferences",
        "destructive Git operations",
        "explicit write scopes",
        "Safety gates",
        "Tooling Preferences",
        "RTK",
        "Interaction Style",
        ".gitignore.template",
        "Do not copy or commit this file into target project repositories by default",
        "target-config input",
        "Rendering Contract",
        "Mark selected preferences with `[x]`",
        "Omit unselected checklist items",
        "resetting or changing local preferences",
        "accidental root `USER.template.md`",
    ):
        require(token in template, f"USER.template.md missing preset token: {token}")


def check_trigger_cases() -> None:
    for case in TRIGGER_CASES:
        should_use, refs = classify_prompt(case.prompt)
        require(
            should_use == case.should_use,
            f"Trigger case {case.name!r} expected should_use={case.should_use}, got {should_use}",
        )
        missing_refs = set(case.expected_refs) - refs
        require(
            not missing_refs,
            f"Trigger case {case.name!r} missing expected refs: {sorted(missing_refs)}",
        )


def check_template_provenance() -> None:
    for path, source_reference in sorted(REQUIRED_TEMPLATES.items()):
        text = read(path)
        meta = parse_simple_frontmatter(text)
        template_name = Path(path).stem
        require(
            meta.get("template_name") == template_name,
            f"{path} template_name must be {template_name}",
        )
        require(meta.get("description"), f"{path} must include description")
        require(
            meta.get("source_reference") == source_reference,
            f"{path} source_reference must be {source_reference}",
        )
        require((ROOT / source_reference).is_file(), f"{path} source_reference missing")
        require(meta.get("intended_project_path"), f"{path} must include intended_project_path")
        require(
            meta.get("owner") in {"agent-facing", "shared-user-facing", "local-user"},
            f"{path} owner must be a known documentation surface",
        )
        require(
            meta.get("secure_derivation") == "required",
            f"{path} must require secure derivation",
        )
        require("review" in meta.get("review_policy", ""), f"{path} must include review_policy")
        block = extract_fenced_block_after_heading(text, "## Project Artifact Frontmatter")
        block_lines = [line for line in block.splitlines() if line.strip()]
        require(
            block_lines and block_lines[0] == "---" and block_lines[-1] == "---",
            f"{path} artifact frontmatter example must be delimited by ---",
        )
        artifact_body = "\n".join(block_lines[1:-1])
        artifact = parse_key_value_block(artifact_body, f"{path} artifact frontmatter")

        required_fields = {
            "artifact_name",
            "instantiated_from",
            "source_reference",
            "project_scope",
            "owner",
            "review_policy",
            "last_reviewed",
        }
        missing_fields = required_fields - set(artifact)
        require(not missing_fields, f"{path} artifact frontmatter missing: {sorted(missing_fields)}")
        require(
            artifact.get("artifact_name") == template_name,
            f"{path} artifact_name must be {template_name}",
        )
        require(
            artifact.get("instantiated_from") == f"project-meta/{path}",
            f"{path} artifact instantiated_from must point to project-meta/{path}",
        )
        require(
            artifact.get("source_reference") == f"project-meta/{source_reference}",
            f"{path} artifact source_reference must point to project-meta/{source_reference}",
        )
        require(
            artifact.get("project_scope") == "this repo only",
            f"{path} artifact project_scope must be this repo only",
        )
        owner = artifact.get("owner", "")
        require(
            owner in {"agent-facing", "shared-user-facing", "local-user"},
            f"{path} artifact owner must be a known documentation surface",
        )
        review_policy = artifact.get("review_policy", "")
        require(
            "review" in review_policy or (owner == "local-user" and "local-only" in review_policy),
            f"{path} artifact review_policy must require review or local-only ownership",
        )
        require(
            artifact.get("last_reviewed") == "YYYY-MM-DD",
            f"{path} artifact last_reviewed must use YYYY-MM-DD placeholder",
        )
        require("## Instantiation Rules" in text, f"{path} missing Instantiation Rules section")


def check_template_surface_contract() -> None:
    for path in sorted(REQUIRED_TEMPLATES):
        text = read(path)
        meta = parse_simple_frontmatter(text)
        block = extract_fenced_block_after_heading(text, "## Project Artifact Frontmatter")
        block_lines = [line for line in block.splitlines() if line.strip()]
        artifact = parse_key_value_block("\n".join(block_lines[1:-1]), f"{path} artifact frontmatter")

        template_name = meta.get("template_name", "")
        owner = meta.get("owner", "")
        intended_path = meta.get("intended_project_path", "")
        artifact_owner = artifact.get("owner", "")

        if path == LOCAL_USER_TEMPLATE:
            require(template_name == "user-preferences", "local-user template must be user-preferences")
            require(owner == "local-user", "user-preferences template owner must be local-user")
            require(artifact_owner == "local-user", "user-preferences artifact owner must be local-user")
            require(intended_path == "USER.md", "user-preferences intended_project_path must be USER.md")
            require(
                not intended_path.startswith(FORBIDDEN_PROJECT_TEMPLATE_PREFIX),
                "user-preferences must not be treated as a committed target-project template",
            )
            for token in (
                "Render only the selected checked preferences into `USER.md`",
                "Do not create or commit a root `USER.template.md` in target projects by default",
                "resetting or changing an existing `USER.md`",
            ):
                require(token in text, f"user-preferences surface contract missing: {token}")
            continue

        require(owner == "agent-facing", f"{path} owner must be agent-facing")
        require(artifact_owner == "agent-facing", f"{path} artifact owner must be agent-facing")
        require(
            intended_path.startswith("agents/"),
            f"{path} intended_project_path must be an agent-facing project artifact",
        )
        require(
            not intended_path.startswith(FORBIDDEN_PROJECT_TEMPLATE_PREFIX),
            f"{path} intended_project_path must not create a generic target-project template library",
        )
        require(intended_path.endswith(".md"), f"{path} intended_project_path must be Markdown")
        require(intended_path != "USER.md", f"{path} must not render to USER.md")
        require(
            "USER.template.md" not in intended_path,
            f"{path} must not create a target-project USER.template.md",
        )
        require(
            "local-user" not in {owner, artifact_owner},
            f"{path} must not use local-user ownership",
        )


def check_doc_context_extractor() -> None:
    extractor = read("scripts/extract_doc_context.py")
    for token in (
        "REPO_ROOT",
        "ALLOWED_EXTENSIONS",
        "MAX_MAX_LINES = 200",
        "MAX_WITHIN_LINES = 500",
        "MAX_CONTEXT_LINES = 50",
        "resolve_repo_markdown_path",
        "validate_line_budgets",
    ):
        require(token in extractor, f"doc context extractor missing hardening token: {token}")

    extractor_path = str(SKILL_ROOT / "scripts" / "extract_doc_context.py")
    rejection_cases = (
        (
            (extractor_path, "README.md", "--index", "--max-lines", "201"),
            "--max-lines may not exceed 200",
            REPO_ROOT,
        ),
        (
            (extractor_path, "/etc/hosts", "--index"),
            "outside repo root",
            REPO_ROOT,
        ),
        (
            ("scripts/extract_doc_context.py", "scripts/render_user_preferences.py", "--index"),
            "Markdown extension",
            None,
        ),
    )
    for args, stderr_token, cwd in rejection_cases:
        result = run_python_script_result(*args, cwd=cwd)
        require(
            result.returncode != 0 and stderr_token in result.stderr,
            f"doc context extractor must reject {args}: {stderr_token}",
        )

    index = run_python_script(extractor_path, "README.md", "--index", cwd=REPO_ROOT)
    require("H2 skills > Install" in index, "doc context index must include README Install heading")
    require(
        "H2 skills > Bounded Doc Loading" in index,
        "doc context index must include bounded loading docs",
    )

    excerpt = run_python_script(
        extractor_path,
        "README.md",
        "--heading",
        "Install",
        "--query",
        "git repo",
        "--within-lines",
        "80",
        "--max-lines",
        "20",
        cwd=REPO_ROOT,
    )
    require("reason: heading match" in excerpt, "doc context extractor must report heading match")
    require("git repo" in excerpt, "doc context extractor must find body query within heading")
    line_count = sum(1 for line in excerpt.splitlines() if re.match(r"^\d+:", line))
    require(line_count <= 20, "doc context extractor must respect --max-lines")


def check_user_preference_renderer() -> None:
    script = read("scripts/render_user_preferences.py")
    for token in (
        "USER.template.md",
        "--reset",
        "--enable",
        "--full-checklist",
        "--ensure-ignore",
        "resolve_output_path",
        "output must stay under target root",
        "Do not commit this file",
    ):
        require(token in script, f"user preference renderer missing token: {token}")

    with tempfile.TemporaryDirectory() as tmp:
        target_root = Path(tmp)
        result = run_python_script_result(
            "scripts/render_user_preferences.py",
            "--target-root",
            str(target_root),
            "--preset",
            "Structured",
            "--enable",
            "Commit And Push",
            "--enable",
            "Validation",
            "--freeform",
            "Explain key decisions in Chinese.",
            "--reset",
            "--ensure-ignore",
        )
        require(result.returncode == 0, f"user preference renderer failed: {result.stderr}")

        rendered_path = target_root / "USER.md"
        require(rendered_path.is_file(), "user preference renderer must write USER.md")
        rendered = rendered_path.read_text(encoding="utf-8")
        require("Selected preset: Structured" in rendered, "rendered USER.md missing selected preset")
        require("- [x] Structured:" in rendered, "rendered USER.md missing checked preset")
        require("### Commit And Push" in rendered, "rendered USER.md missing selected category")
        require("### Validation" in rendered, "rendered USER.md missing validation category")
        require("Explain key decisions in Chinese." in rendered, "rendered USER.md missing freeform item")
        require("Minimal:" not in rendered, "rendered USER.md must not expose unselected presets")
        require("- [ ]" not in rendered, "rendered USER.md must not expose unchecked items by default")
        require("Do not copy or commit this file" not in rendered, "rendered USER.md must not copy template body")
        require(not (target_root / "USER.template.md").exists(), "renderer must not create USER.template.md")

        gitignore = (target_root / ".gitignore").read_text(encoding="utf-8")
        require("/USER.md" in gitignore, "renderer must add USER.md ignore rule")
        require("/USER.template.md" in gitignore, "renderer must add USER.template.md ignore rule")

        outside = run_python_script_result(
            "scripts/render_user_preferences.py",
            "--target-root",
            str(target_root),
            "--output",
            str(target_root.parent / "USER.md"),
            "--preset",
            "Minimal",
            "--reset",
        )
        require(
            outside.returncode != 0 and "output must stay under target root" in outside.stderr,
            "user preference renderer must reject outputs outside target root",
        )


def check_board_cli() -> None:
    template = read("templates/board.dashboard.html")
    require("__BOARD_DATA_JSON__" in template, "board dashboard template must expose data injection marker")
    require("const BOARD_DATA" in template, "board dashboard template must render injected board data")

    with tempfile.TemporaryDirectory() as td:
        target_root = Path(td) / "repo"
        init = run_python_script_result("scripts/board.py", "init", "--root", str(target_root))
        require(init.returncode == 0, f"board init failed: {init.stderr}")

        no_render = run_python_script_result("scripts/board.py", "init", "--root", str(target_root), "--no-render")
        require(no_render.returncode != 0, "board init must not allow --no-render")

        add = run_python_script_result(
            "scripts/board.py",
            "add",
            "--root",
            str(target_root),
            "--id",
            "TEST-001",
            "--kind",
            "feat",
            "--title",
            "Smoke item",
            "--maturity",
            "refined",
            "--status",
            "scheduled",
            "--version",
            "v0.1",
        )
        require(add.returncode == 0, f"board add failed: {add.stderr}")

        tx = run_python_script_result("scripts/board.py", "--root", str(target_root), "tx")
        require(tx.returncode == 0 and "PASS (1 items" in tx.stdout, f"board tx failed: {tx.stderr}{tx.stdout}")

        items = target_root / "docs" / "backlog" / "items.jsonl"
        roadmap = json.loads((target_root / "docs" / "backlog" / "roadmap.json").read_text(encoding="utf-8"))
        items_hash = hashlib.sha256(items.read_bytes()).hexdigest()
        require(
            roadmap.get("_meta", {}).get("items_sha256") == items_hash,
            "roadmap _meta.items_sha256 must match current items.jsonl",
        )

        dashboard = target_root / "docs" / "dashboard.html"
        require(dashboard.is_file(), "board render must write docs/dashboard.html")
        html = dashboard.read_text(encoding="utf-8")
        require("Smoke item" in html, "dashboard must include rendered item data")
        require("docs/backlog/items.jsonl" in html, "dashboard must point to canonical item store")

        # Regression: a value containing </script> must not break out of the dashboard's
        # <script> block (would corrupt BOARD_DATA + enable stored XSS once DASH-02/DASH-25
        # feed arbitrary content). The renderer must escape it to <.
        inj = run_python_script_result(
            "scripts/board.py", "add", "--root", str(target_root),
            "--id", "XSS-1", "--title", "inj",
            "--body", "x</script><img src=y onerror=alert(1)>",
        )
        require(inj.returncode == 0, f"board add (injection case) failed: {inj.stderr}")
        html_xss = (target_root / "docs" / "dashboard.html").read_text(encoding="utf-8")
        require(
            "</script><img src=y onerror=alert(1)>" not in html_xss,
            "dashboard must escape </script> in item content (script-break / XSS guard)",
        )
        require("\\u003c/script" in html_xss, "dashboard must emit escaped \\u003c for <")

        # Regression: every disposition verb must map to a value in DISPOSITION_VALUES
        # (the `defer`->`deferred` mapping was previously wrong, failing validation).
        for verb, expected in (("defer", "deferred"), ("trim", "trimmed"), ("wontfix", "wontfix")):
            d = run_python_script_result("scripts/board.py", verb, "TEST-001", "--root", str(target_root))
            require(d.returncode == 0, f"board {verb} failed: {d.stderr}")
            listing = run_python_script("scripts/board.py", "list", "--root", str(target_root), "--json")
            require(
                f'"disposition": "{expected}"' in listing,
                f"board {verb} must persist disposition={expected}",
            )


CHECKS = (
    check_required_files,
    check_skill_metadata,
    check_marketplace_description_sync,
    check_reference_routing,
    check_memory_boundaries,
    check_protocol_completeness,
    check_command_route_contract,
    check_ui_metadata,
    check_readme_layout,
    check_user_template_presets,
    check_trigger_cases,
    check_template_provenance,
    check_template_surface_contract,
    check_doc_context_extractor,
    check_user_preference_renderer,
    check_board_cli,
)


def main() -> int:
    failures: list[str] = []
    for check in CHECKS:
        try:
            check()
            print(f"PASS {check.__name__}")
        except CheckError as exc:
            failures.append(f"{check.__name__}: {exc}")
            print(f"FAIL {check.__name__}: {exc}")

    if failures:
        print("\nValidation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"\nAll {len(CHECKS)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
