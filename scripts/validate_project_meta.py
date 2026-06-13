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
    "references/review-tier.md",
    "references/code-graph-integration.md",
    "references/codex-operating-loop.md",
}

REQUIRED_TEMPLATES = {
    "templates/delegation.md": "references/multi-agent-protocols.md",
    "templates/execution-rules.md": "references/execution-policy.md",
    "templates/memory-writeback-check.md": "references/repo-memory-crud.md",
    "templates/pre-commit-delivery.md": "references/documentation-delivery.md",
    "templates/project-artifact-manifest.md": "references/documentation-delivery.md",
    "templates/readme-structure-map.md": "references/repo-memory-structure.md",
    "templates/user-preferences.md": "references/project-lifecycle.md",
    "templates/codex-operating-loop.md": "references/codex-operating-loop.md",
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
    "/project-meta roadmap": {
        "mode": "editing",
        "required_refs": (
            "review-tier",
            "multi-agent-protocols",
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
        "scripts/review_tier.py",
        "scripts/render_user_preferences.py",
        "scripts/validate_target_harness.py",
        "templates/board.dashboard.html",
        "references/linear-mirror.md",
        "recipes/roadmap.md",
        "recipes/refine.md",
        "recipes/mirror-linear.md",
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
    # 5 anchor phrases that must appear verbatim in the description.
    # These are the minimum trigger-matching anchors; the description may be
    # trimmed for token budget as long as all five survive.
    for token in (
        "/project-meta",
        "AGENTS.md",
        "USER.md",
        "multi-agent",
        "mirror",
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


def check_linear_mirror_docs() -> None:
    ref = read("references/linear-mirror.md")
    recipe = read("recipes/mirror-linear.md")
    for token in (
        "Push-only",
        "Interactive-only",
        "Dry-run by default",
        "link back",
        "linear_id",
        "board.py mirror-linear",
        "Reverse drift",
    ):
        require(token in ref, f"linear-mirror reference missing: {token}")
    for token in (
        "Read-only by default",
        "references/issue-tracking-integration.md",
        "--json",
        "board.py edit <PROJECT-BOARD-ID> --linear-id",
        "Headless push",
        "Two-way sync",
    ):
        require(token in recipe, f"mirror-linear recipe missing: {token}")


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
        require("showDirectoryPicker" in html, "dashboard must offer pickerless repo-folder edit-back")
        require("indexedDB" in html, "dashboard must persist the repo folder handle across reloads")
        require("showSaveFilePicker" in html, "dashboard must keep the save-picker edit-back fallback")
        require("items.patched.jsonl" in html, "dashboard must include download-patched-store fallback")
        require("roadmap.patched.json" in html, "dashboard must include patched roadmap fallback")
        require("items_sha256" in html, "dashboard must patch roadmap items_sha256 for edit-back")
        require("Browser edit-back" in html, "dashboard must surface the browser edit-back banner")
        require("CLI remains canonical" in html, "dashboard must state the CLI stays canonical")

        mirror = run_python_script_result("scripts/board.py", "mirror-linear", "--root", str(target_root))
        require(mirror.returncode == 0, f"board mirror-linear failed: {mirror.stderr}")
        require("Linear mirror dry-run/export only" in mirror.stdout, "mirror-linear must be dry-run by default")
        require("create TEST-001" in mirror.stdout, "mirror-linear dry-run must list rows to push")
        mirror_json = run_python_script("scripts/board.py", "mirror-linear", "--root", str(target_root), "--json")
        exported = json.loads(mirror_json)
        require(exported.get("dry_run") is True, "mirror-linear JSON must mark dry_run=true")
        require(exported["items"][0]["action"] == "create", "mirror-linear must create rows without linear_id")
        require("Repo backlink:" in exported["items"][0]["body"], "mirror-linear body must link back to repo")

        set_linear = run_python_script_result(
            "scripts/board.py", "edit", "TEST-001", "--root", str(target_root), "--linear-id", "LIN-123"
        )
        require(set_linear.returncode == 0, f"board edit --linear-id failed: {set_linear.stderr}")
        mirror_json = run_python_script("scripts/board.py", "mirror-linear", "--root", str(target_root), "--json")
        exported = json.loads(mirror_json)
        test_item = next(item for item in exported["items"] if item["id"] == "TEST-001")
        require(test_item["action"] == "update", "mirror-linear must update rows with linear_id")
        require(test_item["linear_id"] == "LIN-123", "mirror-linear must export linear_id")

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

        # DASH-23 ladder: capture (inbox) -> promote (items, fuzzy) -> refine (refined).
        cap = run_python_script_result(
            "scripts/board.py", "inbox-add", "--root", str(target_root),
            "--id", "CAP-9", "--title", "fuzzy capture",
        )
        require(cap.returncode == 0, f"board inbox-add failed: {cap.stderr}")
        prom = run_python_script_result("scripts/board.py", "promote", "CAP-9", "--root", str(target_root))
        require(prom.returncode == 0, f"board promote failed: {prom.stderr}")
        inbox_file = target_root / "docs" / "backlog" / "inbox.jsonl"
        inbox_left = [ln for ln in inbox_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        require(not any('"id": "CAP-9"' in ln for ln in inbox_left), "promote must drain the inbox row")
        listing = run_python_script("scripts/board.py", "list", "--root", str(target_root), "--json")
        promoted = next(r for r in json.loads(listing) if r["id"] == "CAP-9")
        require(promoted["maturity"] == "fuzzy", "promoted item must land as fuzzy")
        ref = run_python_script_result(
            "scripts/board.py", "refine", "CAP-9", "--root", str(target_root),
            "--acceptance-shape", "objective threshold", "--rough-size", "S",
        )
        require(ref.returncode == 0, f"board refine failed: {ref.stderr}")
        listing = run_python_script("scripts/board.py", "list", "--root", str(target_root), "--json")
        refined = next(r for r in json.loads(listing) if r["id"] == "CAP-9")
        require(refined["maturity"] == "refined", "refine must advance fuzzy -> refined")

        # Regression: U+2028/U+2029 (and other non-\n unicode separators) in field content
        # must NOT corrupt the store — read_jsonl must split on "\n" only, not str.splitlines().
        sep_title = "alpha\u2028beta\u2029gamma"
        sep = run_python_script_result(
            "scripts/board.py", "add", "--root", str(target_root),
            "--id", "SEP-1", "--title", sep_title,
        )
        require(sep.returncode == 0, f"board add with U+2028/U+2029 failed: {sep.stderr}")
        sep_tx = run_python_script_result("scripts/board.py", "tx", "--root", str(target_root))
        require(sep_tx.returncode == 0, f"store corrupted by U+2028/U+2029: {sep_tx.stderr}{sep_tx.stdout}")
        listing = run_python_script("scripts/board.py", "list", "--root", str(target_root), "--json")
        sep_item = next(r for r in json.loads(listing) if r["id"] == "SEP-1")
        require(sep_item["title"] == sep_title, "U+2028/U+2029 must round-trip intact in the stored title")

        # Harness settings tab: a derived view of the enforcement profile + optional capabilities.
        # State is derived from real artifacts — there is no .harness/settings.json (AP-VAL-2) — and
        # the /project-meta settings CLI stays the canonical writer.
        require('data-tab="settings"' in template, "template must expose the Harness settings tab")
        require("renderSettings" in template, "template must render the harness settings panel")
        require("Enforcement profile" in template, "template must include the enforcement profile selector")
        # Direct profile write-back (File System Access, via the connected repo folder) +
        # the capability command planner.
        require("connectRepoDir" in template, "settings page must offer direct profile write-back via the repo folder")
        require("writeProfile" in template, "settings page must write HARNESS_PROFILE into .claude/settings.json")
        require("data-cap-toggle" in template, "settings page must stage capability changes via toggles")
        require("Pending changes" in template, "settings page must surface a staged command plan")
        # Per-capability drill-down (e.g. "which hooks, wired to what").
        require("data-cap-detail" in template, "capability cards must expose a detail drill-down")
        require("renderCapDetail" in template, "settings page must render per-capability detail")
        require("Wired hooks" in template, "hooks detail must list the wired hooks")

        bare_render = run_python_script_result("scripts/board.py", "render", "--root", str(target_root))
        require(bare_render.returncode == 0, f"bare harness render failed: {bare_render.stderr}")
        bare_html = (target_root / "docs" / "dashboard.html").read_text(encoding="utf-8")
        require("/project-meta settings" in bare_html, "settings page must route to the canonical settings CLI")
        mb = re.search(r"const BOARD_DATA = (\{.*?\});", bare_html, re.DOTALL)
        require(mb is not None, "dashboard must embed BOARD_DATA harness state")
        bare = json.loads(mb.group(1)).get("harness", {})
        require(bare.get("profile") == "unset", "bare repo must derive HARNESS_PROFILE=unset")
        bare_caps = {c["key"]: c["state"] for c in bare.get("capabilities", [])}
        require(
            set(bare_caps) == {"hooks", "phase-lock", "multi-host", "issue-tracker", "code-graph", "land-queue"},
            "harness must report the six optional capabilities",
        )
        require(all(s == "off" for s in bare_caps.values()), "capabilities must read 'off' with no artifacts")

        # Detection + drill-down: a wired hook reads 'on' and its detail maps each event->script
        # (flagging a dangling wiring + an orphan script); a present-but-unrouted doc reads 'half'.
        hooks_dir = target_root / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (target_root / ".claude" / "settings.json").write_text(
            '{"env": {"HARNESS_PROFILE": "standard"}, "hooks": {'
            '"SessionStart": [{"hooks": [{"type": "command", "command": ".claude/hooks/load.sh"}]}], '
            '"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": ".claude/hooks/missing.sh"}]}]}}',
            encoding="utf-8",
        )
        (hooks_dir / "load.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (hooks_dir / "extra.sh").write_text("#!/bin/sh\n", encoding="utf-8")   # on disk, unwired -> orphan
        (target_root / "agents").mkdir(exist_ok=True)
        (target_root / "agents" / "issue-tracking.md").write_text("# tracker\nUses Linear.\n", encoding="utf-8")
        det = run_python_script_result("scripts/board.py", "render", "--root", str(target_root))
        require(det.returncode == 0, f"render with harness artifacts failed: {det.stderr}")
        det_html = (target_root / "docs" / "dashboard.html").read_text(encoding="utf-8")
        md = re.search(r"const BOARD_DATA = (\{.*?\});", det_html, re.DOTALL)
        require(md is not None, "dashboard must embed BOARD_DATA harness state (detection case)")
        det_h = json.loads(md.group(1))["harness"]
        require(det_h.get("profile") == "standard", "must derive HARNESS_PROFILE from .claude/settings.json")
        det_caps = {c["key"]: c for c in det_h["capabilities"]}
        require(det_caps["hooks"]["state"] == "on", "hooks present + wired must read 'on'")
        require(det_caps["issue-tracker"]["state"] == "half", "present-but-unrouted issue-tracker must read 'half-installed'")
        hd = det_caps["hooks"]["detail"]
        wired_by_event = {w["event"]: w for w in hd.get("wired", [])}
        require(
            wired_by_event.get("SessionStart", {}).get("script") == ".claude/hooks/load.sh",
            "hooks detail must map each event to its resolved script",
        )
        require(wired_by_event.get("SessionStart", {}).get("present") is True, "an existing hook script must read present=true")
        require(wired_by_event.get("PreToolUse", {}).get("present") is False, "a wired-but-missing hook script must read present=false")
        require(".claude/hooks/extra.sh" in (hd.get("orphans") or []), "a script on disk with no wiring must be flagged as an orphan")
        require(det_caps["issue-tracker"]["detail"]["routed_in"] == [], "unrouted issue-tracker detail must report no routing files")
        require("mirrors" in det_caps["multi-host"]["detail"], "multi-host detail must enumerate mirror targets")


def check_review_tier() -> None:
    ref = read("references/review-tier.md")
    for token in ("L0", "L1", "L2", "L3", "review_tier.py", "escalate", "floor", "HARNESS_PROFILE"):
        require(token in ref, f"review-tier reference missing: {token}")
    script = read("scripts/review_tier.py")
    for token in ("suggest_level", "HARNESS_PROFILE", "must_rule", "new_skill"):
        require(token in script, f"review_tier.py missing: {token}")
    # Functional: the heuristic floor ladder + the high-stakes no-de-escalate rule.
    cases = (
        (("--files", "1", "--lines", "5"), "L0"),
        (("--files", "3", "--lines", "60"), "L1"),
        (("--files", "8", "--lines", "200"), "L2"),
        (("--harness-hit",), "L2"),
        (("--new-skill", "--profile", "strict"), "L3"),
        (("--new-skill", "--profile", "minimal"), "L3"),  # high stakes must not de-escalate
    )
    for cli_args, expected in cases:
        out = run_python_script("scripts/review_tier.py", *cli_args)
        require(
            f"suggested floor: {expected}" in out,
            f"review_tier.py {cli_args} expected {expected}; got: {out.splitlines()[0] if out else '<none>'}",
        )
        # The escalation caveat must print for EVERY level, not just the last case.
        require("ESCALATE on judgment" in out, f"review_tier.py {cli_args} must print the escalation caveat")


def check_inbox_concurrency() -> None:
    """DASH-24: capture is append-only and multi-instance-safe. Concurrent
    inbox-add calls must all land with no lost, duplicated, or corrupted lines."""
    import concurrent.futures

    with tempfile.TemporaryDirectory() as td:
        target_root = Path(td) / "repo"
        init = run_python_script_result("scripts/board.py", "init", "--root", str(target_root))
        require(init.returncode == 0, f"board init failed: {init.stderr}")
        n = 12

        def add(i: int) -> int:
            return run_python_script_result(
                "scripts/board.py", "inbox-add", "--root", str(target_root),
                "--id", f"CAP-{i:03d}", "--title", f"cap {i}",
            ).returncode

        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
            codes = list(ex.map(add, range(n)))
        require(all(c == 0 for c in codes), "concurrent inbox-add calls must all succeed")

        inbox = target_root / "docs" / "backlog" / "inbox.jsonl"
        rows = [json.loads(line) for line in inbox.read_text(encoding="utf-8").splitlines() if line.strip()]
        require(len(rows) == n, f"inbox must contain all {n} concurrent appends, got {len(rows)}")
        require(len({r['id'] for r in rows}) == n, "concurrent appends must not lose or duplicate rows")


def check_dashboard_wiki() -> None:
    """DASH-25: README + docs/*.md render into the dashboard as a derived wiki, and a
    </script> in doc content cannot break out of the embedded data."""
    with tempfile.TemporaryDirectory() as td:
        target_root = Path(td) / "repo"
        run_python_script_result("scripts/board.py", "init", "--root", str(target_root))
        (target_root / "README.md").write_text("# Proj\n\nSee [[Guide]].\n\n## Setup\n- a\n", encoding="utf-8")
        (target_root / "docs").mkdir(exist_ok=True)
        # guide.md exercises the renderer's XSS surface: </script>, a javascript: link, and an
        # attribute-breakout attempt via a quote in the link target.
        (target_root / "docs" / "guide.md").write_text(
            "# Guide\n\nUse `x`, beware `</script>`.\n\n"
            "[evil](javascript:document.cookie) and [q](\"onmouseover=alert(1)x)\n",
            encoding="utf-8",
        )
        r = run_python_script_result("scripts/board.py", "render", "--root", str(target_root))
        require(r.returncode == 0, f"render with docs failed: {r.stderr}")
        html = (target_root / "docs" / "dashboard.html").read_text(encoding="utf-8")
        require(html.count("</script>") == 1, "doc content must not add a second </script> (breakout guard)")
        m = re.search(r"const BOARD_DATA = (\{.*?\});", html, re.DOTALL)
        require(m is not None, "dashboard must embed BOARD_DATA")
        docs = {d["slug"]: d for d in json.loads(m.group(1)).get("docs", [])}
        require("readme" in docs and "guide" in docs, "wiki must collect README + docs/*.md")
        require("<li>a</li>" in docs["readme"]["html"], "wiki must render markdown lists")
        require('data-wikilink="guide"' in docs["readme"]["html"], "wiki must render [[wikilinks]]")
        guide = docs["guide"]["html"]
        require("&lt;/script&gt;" in guide, "wiki must HTML-escape </script> in doc content")
        require("javascript:" not in guide, "wiki must neutralize javascript: link hrefs (XSS)")
        require('href="#"' in guide, "blocked-scheme links must fall back to href=\"#\"")
        require('"onmouseover' not in guide, "link href must escape quotes (no attribute breakout)")


def check_capture_hook() -> None:
    """DASH-02: the capture hook is dry-run-first — logs a candidate, never writes the
    canonical store; HARNESS_PROFILE=minimal disables it; always exits 0."""
    import os

    hook = ROOT / "templates" / "hooks" / "scripts" / "capture-out-of-scope.sh"
    require(hook.is_file(), "capture-out-of-scope.sh must exist")
    with tempfile.TemporaryDirectory() as td:
        env = {k: v for k, v in os.environ.items() if k != "HARNESS_PROFILE"}
        env.update({"BOARD_ROOT": td, "BOARD_CAPTURE_MODE": "dryrun"})
        r = subprocess.run(["bash", str(hook)], input='{"event":"SessionEnd"}', capture_output=True, text=True, env=env)
        require(r.returncode == 0, f"capture hook must exit 0: {r.stderr}")
        backlog = Path(td) / "docs" / "backlog"
        require((backlog / ".capture-dryrun.log").is_file(), "dry-run capture must write a candidate log")
        require(not (backlog / "items.jsonl").exists(), "capture must NOT write items.jsonl")
        require(not (backlog / "roadmap.json").exists(), "capture must NOT write roadmap.json")
        require(not (backlog / "inbox.jsonl").exists(), "dry-run capture must NOT write inbox.jsonl")
    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "BOARD_ROOT": td, "HARNESS_PROFILE": "minimal"}
        r = subprocess.run(["bash", str(hook)], input="{}", capture_output=True, text=True, env=env)
        require(r.returncode == 0, "capture hook (minimal) must exit 0")
        require(not (Path(td) / "docs" / "backlog" / ".capture-dryrun.log").exists(), "minimal profile must disable capture")


def check_skillmd_recipe_table_sync() -> None:
    """D2 router repair: SKILL.md Recipes table must contain every verb in the
    cli-command-patterns.md route table.

    Allowlist: documented sub-workflows that intentionally appear only as recipe
    files, not as top-level route-table rows in cli-command-patterns.md:
      - refine: explicitly documented as a sub-workflow of roadmap (not a core verb)
      - mirror-linear: a board.py sub-command exposed via board CLI, not a /project-meta verb
    """
    # Parse verb set from SKILL.md ## Recipes table (rows starting with "| `")
    skill_md = read("SKILL.md")
    recipes_heading = "## Recipes"
    recipes_pos = skill_md.find(recipes_heading)
    require(recipes_pos != -1, "SKILL.md must contain a ## Recipes section")
    # Find the table within the Recipes section (stop at the next ## heading)
    next_section = skill_md.find("\n## ", recipes_pos + 1)
    recipes_section = skill_md[recipes_pos:next_section] if next_section != -1 else skill_md[recipes_pos:]
    skillmd_verbs: set[str] = set()
    for line in recipes_section.splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|", line)
        if m:
            skillmd_verbs.add(m.group(1))

    # Parse verb set from cli-command-patterns.md route table (rows starting with "| `/project-meta ")
    cli = read("references/cli-command-patterns.md")
    cli_verbs: set[str] = set()
    for line in cli.splitlines():
        m = re.match(r"\|\s*`/project-meta\s+([^`]+)`\s*\|", line)
        if m:
            cli_verbs.add(m.group(1).strip())

    # Allowlist: verbs present in cli-command-patterns.md route table but intentionally
    # absent from the SKILL.md table (documented sub-workflows / board sub-commands).
    # After D2 repair, the only expected gaps are board-CLI sub-commands surfaced via
    # mirror-linear (a board.py sub-command, not a /project-meta verb).
    # `refine` appears in SKILL.md (added by D2) but not in the cli route table —
    # it is a recipe-only sub-workflow; the allowlist direction here is cli->skillmd.
    allowlist: set[str] = set()  # verbs in cli route table that need not be in SKILL.md

    failures = []
    for verb in sorted(cli_verbs - allowlist):
        if verb not in skillmd_verbs:
            failures.append(
                f"verb '{verb}' is in cli-command-patterns.md route table but missing from SKILL.md Recipes table"
            )
    for failure in failures:
        raise CheckError(failure)


def check_trigger_coverage() -> None:
    """D6 token-coverage gate (deterministic, stdlib only).

    Loads evals/triggers.json with should_trigger and should_not_trigger phrase lists.
    Tokenizes the SKILL.md description (frontmatter field) + the Trigger Decision section
    into a content-token set (lowercased, stop-words removed).

    A should_trigger phrase 'passes' if it shares at least one non-stopword content token
    with the description token set (description is the auto-trigger surface).
    Fails if fewer than 80% of should_trigger phrases hit the description token set.

    For should_not_trigger phrases, emits warnings (not failures) when they overlap heavily
    (≥3 content tokens in common with the description+trigger-section token set).

    This is a token-coverage gate — it does NOT measure precision or recall.
    """
    import json as _json

    evals_path = ROOT / "evals" / "triggers.json"
    require(evals_path.is_file(), "evals/triggers.json must exist for the trigger coverage gate")
    evals = _json.loads(evals_path.read_text(encoding="utf-8"))
    should_trigger = evals.get("should_trigger", [])
    should_not_trigger = evals.get("should_not_trigger", [])
    require(len(should_trigger) >= 5, "evals/triggers.json must have at least 5 should_trigger phrases")
    require(len(should_not_trigger) >= 5, "evals/triggers.json must have at least 5 should_not_trigger phrases")

    # Stop-words: common English function words that add no signal
    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "up", "about", "into", "through", "is",
        "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might",
        "this", "that", "these", "those", "i", "my", "me", "we", "our", "you",
        "your", "it", "its", "they", "their", "them", "he", "she", "his", "her",
        "what", "which", "who", "how", "when", "where", "why", "set", "up",
        "as", "if", "not", "no", "so", "than", "then", "there", "here",
    }

    def tokenize(text: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9][-a-z0-9]*", text.lower())
        return {t for t in tokens if t not in STOPWORDS and len(t) >= 2}

    skill_md = read("SKILL.md")

    # Extract description from frontmatter
    fm_end = skill_md.find("\n---", 4)
    require(fm_end != -1, "SKILL.md frontmatter must close with ---")
    frontmatter = skill_md[4:fm_end]
    description = ""
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip().strip('"')
            break
    require(description, "SKILL.md must have a description field in frontmatter")

    # Extract Trigger Decision section
    trigger_pos = skill_md.find("## Trigger Decision")
    next_section_pos = skill_md.find("\n## ", trigger_pos + 1) if trigger_pos != -1 else -1
    trigger_section = ""
    if trigger_pos != -1:
        trigger_section = skill_md[trigger_pos:next_section_pos] if next_section_pos != -1 else skill_md[trigger_pos:]

    desc_tokens = tokenize(description)
    full_tokens = desc_tokens | tokenize(trigger_section)

    # Coverage gate: count how many should_trigger phrases share ≥1 token with the description
    hits = 0
    misses = []
    for phrase in should_trigger:
        phrase_tokens = tokenize(phrase)
        if phrase_tokens & desc_tokens:
            hits += 1
        else:
            misses.append(phrase)

    coverage = hits / len(should_trigger) if should_trigger else 1.0
    floor = 0.80
    if coverage < floor:
        raise CheckError(
            f"trigger token-coverage gate: {hits}/{len(should_trigger)} should_trigger phrases "
            f"({coverage:.0%}) share a content token with the description — below the {floor:.0%} floor. "
            f"Misses: {misses}"
        )

    # Warn (not fail) for should_not_trigger phrases that overlap heavily with full token set
    warnings = []
    for phrase in should_not_trigger:
        phrase_tokens = tokenize(phrase)
        overlap = phrase_tokens & full_tokens
        if len(overlap) >= 3:
            warnings.append(f"  should_not_trigger '{phrase}' overlaps heavily: {sorted(overlap)}")
    if warnings:
        print(f"  WARN check_trigger_coverage: {len(warnings)} should_not phrases overlap heavily (not a failure):")
        for w in warnings:
            print(w)


def check_board_crud_contract() -> None:
    """The Project Board CRUD rules are an agent-facing reference, routed from SKILL.md +
    init, and enforced by the board-guard PreToolUse hook + the Stop board.py tx leg."""
    import os

    crud = read("references/project-board-crud.md")
    for token in ("board.py", "only writer", "derived", "items_sha256", "board.py tx", "promote", "refine"):
        require(token in crud, f"references/project-board-crud.md missing: {token}")
    require("references/project-board-crud.md" in read("SKILL.md"), "SKILL.md must route the board CRUD contract")
    require("references/project-board-crud.md" in read("recipes/init.md"), "init --board must route the board CRUD contract")

    guard = ROOT / "templates" / "hooks" / "scripts" / "board-guard.sh"
    require(guard.is_file(), "board-guard.sh must exist")
    fragment = read("templates/hooks/settings.json.fragment")
    require("board-guard.sh" in fragment and "PreToolUse" in fragment, "settings.json.fragment must wire board-guard under PreToolUse")
    require("board.py tx" in read("templates/hooks/scripts/verify-before-stop.sh"), "verify-before-stop.sh must run board.py tx for store integrity")

    # Functional: the profile ladder via PreToolUse exit codes (2 = block, 0 = allow).
    def run(profile: str, file_path: str) -> int:
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
        env = {**os.environ, "HARNESS_PROFILE": profile}
        return subprocess.run(["bash", str(guard)], input=payload, capture_output=True, text=True, env=env).returncode

    require(run("standard", "docs/dashboard.html") == 2, "standard must block hand-edits to the derived dashboard")
    require(run("standard", "docs/backlog/items.jsonl") == 0, "standard must allow store edits (dashboard-only guard)")
    require(run("strict", "docs/backlog/items.jsonl") == 2, "strict must block hand-edits to the CLI-managed store")
    require(run("strict", "docs/dashboard.html") == 2, "strict must block dashboard hand-edits too")
    require(run("standard", "src/app.py") == 0, "guard must not touch unrelated files")
    require(run("minimal", "docs/dashboard.html") == 0, "minimal must disable the guard")


def check_audit_convergence() -> None:
    """The audit Convergence MUST (SKILL.md Core Rule / recipes/audit.md step 8) is
    hook-backed (DASH-032): audit_ledger.py exists, passes its deterministic self-test,
    is wired into the Stop hook, and is named in the canon so determinism_gap_scan can
    pair the MUST prose with its enforcing hook."""
    ledger = ROOT / "scripts" / "audit_ledger.py"
    require(ledger.is_file(), "scripts/audit_ledger.py must exist")
    require("audit_ledger.py" in read("templates/hooks/scripts/verify-before-stop.sh"),
            "verify-before-stop.sh must run the audit convergence gate (audit_ledger.py)")
    require("audit_ledger.py" in read("SKILL.md"),
            "SKILL.md converge-MUST must name audit_ledger.py")
    require("audit_ledger.py" in read("recipes/audit.md"),
            "recipes/audit.md step 8 must spec the audit_ledger.py record calls")
    require("audit_ledger.py" in read("recipes/deliver.md"),
            "recipes/deliver.md must fail fast on a red audit ledger")
    r = subprocess.run([sys.executable, str(ledger), "--self-test"], capture_output=True, text=True)
    require(r.returncode == 0, f"audit_ledger.py --self-test failed: {(r.stderr or r.stdout).strip()[:300]}")


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
    check_linear_mirror_docs,
    check_trigger_cases,
    check_template_provenance,
    check_template_surface_contract,
    check_doc_context_extractor,
    check_user_preference_renderer,
    check_board_cli,
    check_review_tier,
    check_inbox_concurrency,
    check_dashboard_wiki,
    check_capture_hook,
    check_board_crud_contract,
    check_audit_convergence,
    check_skillmd_recipe_table_sync,
    check_trigger_coverage,
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
