# Project Lifecycle Harness

## Contents

- [Init Command](#init-command) — `/project-meta init` cold-start workflow
- [Preference Presets](#preference-presets) — Minimal, Structured, Strict, Secure, Custom
- [Interactive User Preference Rendering](#interactive-user-preference-rendering) — how to render `USER.md`
- [Lifecycle](#lifecycle) — Bootstrap, Operate, Observe, Promote, Prune
- [Universal Project Model](#universal-project-model) — project type classification
- [Project Type Artifact Map](#project-type-artifact-map) — recommended artifacts per project type
- [Artifact Instantiation Rules](#artifact-instantiation-rules) — semantic paths, provenance, manifest
- [Iteration Triggers](#iteration-triggers) — when to update the harness
- [Promotion Rules](#promotion-rules) — what gets written to canonical memory
- [Project Closeout](#project-closeout) — finishing meaningful work

Use this reference when bootstrapping a project harness or deciding how it should evolve after real project work.

## Init Command

> Route contract (mode, required references, output) for `/project-meta init` lives in [`cli-command-patterns.md`](cli-command-patterns.md). This file owns the lifecycle detail: workflow steps, preference presets, project type classification, and artifact instantiation.

Use `/project-meta init` as the explicit cold-start command for a repo or project.

The init command must not depend on existing `USER.md`, because an empty project will not have local preferences yet. On init:

1. Detect existing docs and conventions without assuming they are complete.
2. Create or repair the project-level agent-facing entrypoint. When Claude Code is the primary consumer, use `CLAUDE.md` as the canonical entrypoint and `AGENTS.md` as the mirror. When Codex is primary or tool context is unknown, use `AGENTS.md`.
3. Create or repair the shared/user-facing project entrypoint, usually `README.md` or `docs/user/`.
4. Ensure local `USER.md` and accidental root `USER.template.md` files will be ignored by Git, using `.gitignore.template` or an equivalent ignore rule.
5. Use the installed Project Meta `USER.template.md` as target-config input and questionnaire source. Do not copy its original body into the target repo.
6. Ask the user to choose a preset and any optional checklist items before relying on user-specific behavior.
7. Render only the selected preset, checked preferences, and explicit free-form preferences into ignored local `USER.md`.
8. Instantiate project-specific artifacts from skill-level `templates/*.md` when the project needs repeatable agent-facing artifacts.
9. When the target repo will host bounded-execution agents (Codex-class workers, automated execution flows), offer to instantiate `agents/execution-rules.md` from `templates/execution-rules.md` and add the AGENTS.md insert. Skip this for documentation or content-only repos unless the user requests it.
10. Run available validation, including `python3 skill/scripts/validate_target_harness.py <target-repo>` when the target repo path is known, and present a delivery before any commit.

If the user asks for init in a repo that already has coherent conventions, preserve those conventions and only fill missing pieces.

## Preference Presets

Offer presets first, then allow checkbox-level customization:

- Minimal: create local `USER.md`; follow basic read order; use map-first/selective README loading; write back only durable memory; run validation when available; do not automatically commit or push.
- Structured: Minimal plus pre-commit delivery; user-facing docs review; validation before commit; memory writeback closeout; final answer includes changed files, validation, and commit or push status.
- Strict: Structured plus complex-task planning/review; Lead-owned multi-agent context packages; branch/PR flow; commit after approved operations; push after approved operations.
- Secure: Structured plus local-only user preferences; no secrets, transient local state, or unresolved hypotheses in memory; ask before destructive Git operations; require explicit write scopes for sub-agents; require delivery before overwriting project-level artifacts.
- Custom: user selects individual preferences from the checklist.

Recommended checklist categories:

- Commit and push policy
- Pre-commit delivery
- Documentation mode
- Memory writeback policy
- Multi-agent policy
- Validation strictness
- Review gates
- Privacy and locality
- Safety gates
- Branch or PR strategy
- Interaction style

## Interactive User Preference Rendering

`USER.template.md` belongs to the installed Project Meta skill. During `/project-meta init`, treat it as a configuration input, not as a file to copy.

Rendering flow:

1. Load the installed `USER.template.md` or equivalent preference seed.
2. Ask the user to choose one preset.
3. Ask which optional checklist categories or individual items should be enabled.
4. Generate target-root `USER.md` with only the selected preset, selected preferences marked `[x]`, and explicit free-form preferences.
5. Omit unselected items unless the user asks for an editable full checklist.
6. Verify `USER.md` is ignored before any commit.
7. Do not create, stage, or commit target-root `USER.template.md` unless the user explicitly requests a sanitized shared preference template.

The rendered `USER.md` is the local target configuration. The template is only the source used to ask questions and produce that local file.

Use the same rendering flow when the user later asks to reset or change `USER.md` options. Do not edit from stale local preferences alone; reload the installed template so new presets, wording, and checklist items are available. Prefer the renderer script when available:

```bash
python3 scripts/render_user_preferences.py --target-root <repo> --reset
```

For non-interactive operation, pass `--preset`, repeated `--enable`, and optional `--freeform` values. Use `--full-checklist` only when the user explicitly wants an editable checklist with unselected items preserved.

## Lifecycle

1. Bootstrap: identify the repo type, existing conventions, canonical memory files, tooling, and validation commands.
2. Operate: use only the relevant memory and project-specific rules for the current task.
3. Observe: track durable facts, repeated failures, review findings, workflow friction, and validation gaps.
4. Promote: move only validated reusable lessons into the right canonical file.
5. Prune: remove stale, duplicated, or contradictory guidance when project reality changes.

## Universal Project Model

Do not assume the repo is an application. Classify the project before adding guidance:

- application or service
- library or package
- documentation, content, or knowledge base
- data, research, or evaluation project
- infrastructure, automation, or tooling repo
- standalone skill or agent-harness repo

The project type determines which topical memory files are useful. For example, an app may need architecture, runtime, testing, and operations files. A documentation repo may only need style, publishing, and source-of-truth files.

## Project Type Artifact Map

Use this default map during `/project-meta init`. Preserve coherent project conventions and instantiate only the artifacts that remove real repeated work.

| Project type | Recommended project artifacts | Notes |
| --- | --- | --- |
| application or service | `delegation`, `pre-commit-delivery`, `readme-structure-map`, `memory-writeback-check`, `execution-rules`, `project-artifact-manifest` | Add project-specific validation, local dev server, E2E, observability, and release handoff details. |
| library or package | `pre-commit-delivery`, `memory-writeback-check`, `readme-structure-map`, `execution-rules`, `project-artifact-manifest` | Emphasize API compatibility, changelog/release checks, examples, and package tests. |
| documentation, content, or knowledge base | `readme-structure-map`, `pre-commit-delivery`, `memory-writeback-check`, `project-artifact-manifest` | Emphasize source-of-truth, user review, publishing flow, and heading-bounded loading. Skip `execution-rules` unless bounded-execution agents touch the repo. |
| data, research, or evaluation project | `delegation`, `memory-writeback-check`, `pre-commit-delivery`, `execution-rules`, `project-artifact-manifest` | Emphasize reproducibility, dataset boundaries, eval commands, and result provenance. |
| infrastructure, automation, or tooling repo | `delegation`, `pre-commit-delivery`, `memory-writeback-check`, `execution-rules`, `project-artifact-manifest` | Emphasize safety gates, rollback, dry-run validation, secrets boundaries, and operator handoff. `execution-rules` is highest-priority here. |
| standalone skill or agent-harness repo | all canonical templates | Emphasize progressive disclosure, artifact provenance, validation coverage, and cross-tool metadata. |

`user-preferences` is special: use it to render local `USER.md` when user preferences are needed, but do not commit the generated local file and do not create a target-repo `USER.template.md` unless the user explicitly asks for a sanitized shared preference artifact.

## Artifact Instantiation Rules

- Skill-level templates are canonical seeds; project-level outputs are concrete project artifacts, not templates.
- Do not create committed `agents/templates/*.md` libraries in target projects by default.
- Prefer semantic project paths such as `agents/readme-structure.md`, `agents/pre-commit-delivery.md`, `agents/delegation.md`, `agents/memory-writeback-check.md`, or another path that names the concrete project artifact.
- Include `instantiated_from`, `source_reference`, `project_scope`, `owner`, `review_policy`, and `last_reviewed` in every committed project artifact instantiated from a skill template.
- Do not generate or commit a root `USER.template.md` in target projects by default. User preference presets should be rendered interactively and directly into ignored local `USER.md`.
- In Secure or Strict mode, do not overwrite project-level artifacts without showing a delivery.
- If more than one Project Meta-instantiated artifact exists, create or update a project artifact manifest such as `agents/project-artifacts.md`.

## Iteration Triggers

Consider updating the harness after:

- a user correction reveals a stable preference or repeated misunderstanding
- a bug, review finding, or failed command exposes a reusable trap
- a new command, tool, dependency, or validation workflow becomes canonical
- a repo convention changes
- a topical memory file becomes stale, overlapping, or too small to justify loading
- the same planning or coordination problem appears more than once

## Promotion Rules

- Promote repo facts into project memory.
- Promote stable user collaboration preferences into user-preference memory.
- Promote tool-specific compatibility notes into mirrors only after canonical memory is updated.
- Promote repeated manual checks into scripts, checklists, templates, tests, or documented validation commands.
- Do not promote one-off task logs, guesses, local transient state, or unresolved hypotheses.

## Project Closeout

Before finishing meaningful project work:

1. Verify the requested outcome with the available checks.
2. Decide whether any lesson is durable enough to write back.
3. Update the smallest canonical file that owns that lesson.
4. Sync mirrors only if canonical structure or high-priority guidance changed.
5. Remove or replace stale guidance discovered during the task.
