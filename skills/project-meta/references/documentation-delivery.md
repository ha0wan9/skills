# Documentation Delivery

## Contents

- [Documentation Surfaces](#documentation-surfaces) — primary user-facing vs agent-facing layering
- [Existing Agent-Facing Framework](#existing-agent-facing-framework) — `AGENTS.md`, `SKILL.md`, references, templates, validator
- [Skill Layer Vs Project Layer](#skill-layer-vs-project-layer) — what lives where
- [Canonical Template Layer](#canonical-template-layer) — seeds, frontmatter contract
- [Project-Level Instantiated Artifacts](#project-level-instantiated-artifacts) — semantic paths, frontmatter requirements
- [Artifact Provenance Contract](#artifact-provenance-contract) — overwrite, delete, manifest rules
- [Collaboration Flow](#collaboration-flow) — request to commit pipeline
- [Default Mapping](#default-mapping) — this skill repo's surface
- [Responsibilities](#responsibilities) — agent-owned vs user-reviewed
- [Pre-Commit Delivery](#pre-commit-delivery) — required sections before commit
- [Review Checklist](#review-checklist) — final pass before delivery

Use this reference when updating the existing agent-facing documentation framework, preparing user-facing documentation, or showing the pre-commit delivery for harness changes.

## Documentation Surfaces

Preserve the existing agent-facing framework and add a user-facing review surface:

- Shared/user-facing documentation is the primary documentation. Users and agents both read it for project purpose, usage, architecture, and reviewed behavior.
- Agent-facing project documentation records agent-only operational notes: routing, traps, validation commands, writeback rules, and execution details that would clutter the shared docs.

Primary does not require eager full loading. Agents should use the agent-facing loader to route work, inspect shared docs lightly at cold start, then read only the relevant shared-doc sections unless the task requires the whole document. For long shared docs, agents may maintain a README structure map in agent-facing documentation to route section reads without duplicating user-facing prose.

## Existing Agent-Facing Framework

Project Meta already has an agent-facing documentation framework:

- `AGENTS.md`: repo bootstrap, read order, and durable project facts
- `SKILL.md`: trigger policy, core workflow, and reference routing
- `references/*.md`: focused progressive-disclosure protocols
- `templates/*.md`: skill-level canonical seed templates for repeatable project-level artifacts
- `scripts/validate_target_harness.py` (shipped with the skill): mechanical validation for the harness; the dev-repo validator `validate_project_meta.py` lives at the marketplace repo root, not in the skill
- `agents/openai.yaml`: UI metadata that affects skill discovery

Do not replace this framework with a parallel one. Extend it only when a new agent-facing rule has a clear owner and routing path.

## Skill Layer Vs Project Layer

Project Meta separates reusable skill protocols from project-specific documentation:

```text
Project Meta skill layer
  SKILL.md
    - trigger policy
    - bootstrap workflow
    - reference routing
  references/*.md
    - reusable protocols
    - harness patterns
    - documentation delivery rules
    - multi-agent coordination rules
  templates/*.md
    - skill-level canonical seed templates with source references and instantiation rules
  scripts/validate_target_harness.py
    - skill-level validation

Installed or target project layer
  AGENTS.md or local equivalent
    - project read order
    - project facts
    - topic routing
  agents/*.md or project docs
    - project-specific architecture, runtime, testing, operations, or documentation rules
  agents/readme-structure.md or AGENTS.md README Structure section
    - agent-maintained heading map and routing hints for long shared docs
  agents/readme-structure.md, agents/delegation.md, agents/pre-commit-delivery.md, or similar semantic paths
    - project-specific instantiated artifacts based on Project Meta seeds
  agents/project-artifacts.md or similar manifest
    - provenance index for Project Meta-instantiated artifacts when more than one exists
  README.md, docs/user/, or local user-facing docs
    - primary shared documentation reviewed by the user and read by agents
  USER.md
    - local user preferences, ignored by Git when appropriate
  .gitignore.template or local .gitignore rule
    - reusable ignore rule that keeps USER.md local-only
```

The skill layer defines how to build and evolve a harness. The project layer records what is true for a specific project after work begins.

## Canonical Template Layer

References define reusable protocol and reasoning rules. Templates define copyable skill-level seeds. Scripts validate rules that should not stay purely advisory.

Project Meta keeps canonical seed templates in `templates/*.md`:

- `templates/delegation.md`: bounded explorer, worker, and reviewer context packages.
- `templates/pre-commit-delivery.md`: delivery shown before commits.
- `templates/readme-structure-map.md`: agent-facing route map for long shared docs.
- `templates/user-preferences.md`: local `USER.md` seed for stable preferences.
- `templates/memory-writeback-check.md`: closeout decision for durable memory updates.
- `templates/project-artifact-manifest.md`: provenance index for generated project artifacts.

Each canonical template must declare `source_reference`, `intended_project_path`, `owner`, `secure_derivation`, and `review_policy` in frontmatter. Canonical template frontmatter describes the reusable skill-level seed. Project-level artifact frontmatter describes one concrete generated artifact in a target repo and must use the instantiation contract below.

## Project-Level Instantiated Artifacts

During `/project-meta init` or a later artifact-generation step, agents may instantiate project-level artifacts from canonical seeds. Do not create a generic committed template library such as `agents/templates/*.md` by default. Prefer semantic artifact paths that describe the concrete project output, such as `agents/readme-structure.md`, `agents/delegation.md`, `agents/pre-commit-delivery.md`, or `agents/memory-writeback-check.md`. Keep `USER.md` local-only for user preferences.

Do not create or commit a root `USER.template.md` in target projects by default. `USER.template.md` is a Project Meta skill-layer questionnaire and target-config input, while target-project user preferences should be rendered interactively into ignored local `USER.md`. Ask the user which preset and checklist items to enable, mark selected preferences with `[x]`, and omit unselected items unless the user requests an editable full checklist. If a user explicitly asks for a shared sanitized preference template, treat that as a separate shared/user-facing artifact and show it in the delivery before commit.

Project artifacts instantiated from Project Meta seeds must keep structurally valid provenance frontmatter. The frontmatter must be the first block in the file, delimited by `---`, parse as YAML, and contain only scalar values for the required provenance fields unless the project defines a stricter schema.

```yaml
---
artifact_name: <name>
instantiated_from: project-meta/templates/<name>.md
source_reference: project-meta/references/<reference>.md
project_scope: this repo only
owner: <agent-facing | shared-user-facing | local-user>
review_policy: <project review rule>
last_reviewed: YYYY-MM-DD
---
```

Required artifact fields:

- `artifact_name`: stable identifier for the concrete project artifact.
- `instantiated_from`: canonical Project Meta seed path, normally `project-meta/templates/<name>.md`.
- `source_reference`: Project Meta reference that owns the behavior, normally `project-meta/references/<reference>.md`.
- `project_scope`: target-project scope, usually `this repo only`.
- `owner`: one of `agent-facing`, `shared-user-facing`, or `local-user`.
- `review_policy`: target-project review rule in plain language.
- `last_reviewed`: ISO date `YYYY-MM-DD` or a project-approved immutable review marker.

## Artifact Provenance Contract

- Do not overwrite an existing project-level artifact without checking whether it was customized.
- In Secure or Strict mode, show a delivery before adding, overwriting, or deleting Project Meta-instantiated artifacts.
- If an instantiated artifact changes behavior triggers, review gates, commit policy, validation, or user-facing documentation behavior, require user review before commit.
- Generated artifacts should adapt paths, commands, ownership, and validation to the target project without copying unrelated Project Meta internals.
- Generated target-project artifacts must not expose the raw local user preference questionnaire by default; render selected user preferences into ignored `USER.md` instead.
- When more than one Project Meta-instantiated artifact exists, maintain `agents/project-artifacts.md` or an equivalent manifest.
- The manifest must list each artifact path and repeat the artifact's `instantiated_from`, `source_reference`, `owner`, `review_policy`, `last_reviewed`, and refresh or update trigger.
- Manifest entries must agree with each artifact's frontmatter; if they drift, treat the artifact frontmatter as the artifact-local source and repair the manifest before delivery.

## Collaboration Flow

```text
User request
  -> Project Meta trigger decision
  -> Load only relevant skill references
  -> Select canonical templates when reusable artifacts are needed
  -> Read or create project-level docs
  -> Instantiate or update project-level artifacts when useful
  -> Perform the project work
  -> Promote durable project lessons into project docs
  -> Prepare user-facing delivery
  -> User reviews delivery
  -> Commit and push approved scope
```

Use skill references for reusable rules. Use shared project documentation as the primary project explanation, with selective section loading when possible. Use agent-facing project documentation only for agent-specific execution details.

## Default Mapping

For this skill repository:

- Agent-facing docs: `AGENTS.md`, `SKILL.md`, `references/*.md`, `templates/*.md`, `scripts/validate_project_meta.py`, and tool metadata that controls agent behavior.
- Shared/user-facing docs: `README.md`, `USER.template.md`, and any future user guides or release notes.
- Local user preferences: `USER.md`, ignored by Git and not pushed.
- Ignore template: `.gitignore.template`, copied or merged into target projects so `USER.md` and accidental root `USER.template.md` files stay local-only.

In other projects, preserve coherent local conventions. If no convention exists, use `AGENTS.md` or equivalent for agent-facing guidance and `README.md` or `docs/user/` for user-facing guidance.

## Responsibilities

- Agent-facing docs are agent-owned within the existing framework: agents may update them when needed, then validate them mechanically where possible.
- Shared/user-facing docs are user-reviewed and primary: agents may draft or update them, but must surface the user-facing changes in a delivery before commit.
- Do not hide user-facing behavior changes only in agent-facing docs.
- Do not duplicate the same rule across both surfaces unless the user and agent genuinely need different versions of the same information.

## Pre-Commit Delivery

Before creating a commit for harness or documentation work, show the user a concise delivery with:

```text
User-facing docs:
- <files and what changed>

Agent-facing docs:
- <files and what changed>

Behavior or trigger changes:
- <what future agents will do differently>

Validation:
- <commands run and result>

Commit scope:
- <files intended for commit>
```

If the user-facing docs changed, explicitly ask for review before committing unless the user already approved the exact delivery in the current turn.

## Review Checklist

- Is the user-facing documentation understandable without reading agent internals?
- Does the shared/user-facing documentation contain the project-level explanation that both users and agents need?
- Did the change preserve the existing agent-facing framework instead of creating a parallel one?
- Are agent-facing docs specific enough for future agents to act on?
- Is `USER.md` kept local and out of Git?
- Do Project Meta-instantiated artifacts preserve `instantiated_from`, `source_reference`, owner, review policy, and last review metadata?
- Does each instantiated artifact have YAML frontmatter with the required provenance fields, and does the manifest agree with it?
- Are validation commands documented and passing?
- Does the commit scope match the delivery?
