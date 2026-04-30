---
name: project-meta
description: "Bootstrap, audit, and evolve a repository or project agent-work harness with /project-meta command workflows such as /project-meta init, status, validate, deliver, and audit: canonical memory files such as AGENTS.md and local USER.md, existing agent-facing documentation framework, user-facing documentation delivery, topical references, canonical templates and project-level artifact instantiation, trigger policy, preference presets, behavior guardrails, multi-agent planning/review, mirror sync, pre-commit delivery, and durable knowledge writeback. Use when starting work in a repo, creating or repairing repo memory, improving agent instructions, coordinating complex project work, or updating harness guidance after validated lessons."
---

# Project Meta

Use this skill when starting work in a repo, designing or maintaining project memory, improving agent instructions, coordinating complex project work, or turning validated lessons into durable project harness updates.

Keep this file as the skill entrypoint. Load the linked reference files only as needed.

## Trigger Decision

Use this skill for any of these triggers:

- Command trigger: the user says `/project-meta <command>`, especially `init`, `status`, `validate`, `deliver`, or `audit`.
- Bootstrap trigger: entering a repo or project where agent instructions, memory, or read order matter.
- Memory trigger: creating, repairing, splitting, pruning, or syncing canonical memory files.
- Harness trigger: improving agent instructions, behavior guardrails, validation loops, or project-specific operating rules.
- Documentation trigger: updating the existing agent-facing docs, user-facing docs, or pre-commit delivery expectations.
- Iteration trigger: a project lesson, failure, review finding, or recurring workflow should become durable guidance.
- Coordination trigger: the user explicitly asks for multi-agent work, or task complexity warrants planning, delegated execution, and review.
- User-preference trigger: the user asks to create, reset, or change local `USER.md` options.

Do not use the skill for ordinary implementation work that does not touch project memory, operating rules, coordination, or durable knowledge.

## Bootstrap Order

1. Find repo-level shared docs such as `README.md`, plus the repo's canonical project-memory and user-preference files.
2. If this is `/project-meta init`, do not depend on existing `USER.md`; load the init workflow and create or repair project memory first.
3. Read the canonical project-memory file when it exists; use it as the routing layer for what to load next.
4. Inspect shared docs lightly before full loading: title, first section, table of contents, heading map, or agent-facing README structure map. Read the full shared doc only when it is short or directly relevant to the task.
5. Read the canonical user-preference file when it exists.
6. If the project-memory file routes to `agents/*.md` or another topical-memory directory, load only the files relevant to the current task.
7. Load canonical templates from `templates/*.md` only when instantiating or reviewing project-specific artifacts.
8. Load this skill's reference files only when you need them:
   - [`references/project-lifecycle.md`](references/project-lifecycle.md)
   - [`references/cli-command-patterns.md`](references/cli-command-patterns.md)
   - [`references/agent-behavior-protocol.md`](references/agent-behavior-protocol.md)
   - [`references/execution-policy.md`](references/execution-policy.md)
   - [`references/documentation-delivery.md`](references/documentation-delivery.md)
   - [`references/repo-memory-structure.md`](references/repo-memory-structure.md)
   - [`references/repo-memory-crud.md`](references/repo-memory-crud.md)
   - [`references/mirrors-and-updates.md`](references/mirrors-and-updates.md)
   - [`references/harness-engineering.md`](references/harness-engineering.md)
   - [`references/multi-agent-protocols.md`](references/multi-agent-protocols.md)

## Core Rules

- Treat the repo's canonical project-memory and user-preference files as the source of truth; treat tool-specific mirrors such as `CLAUDE.md` and `.github/copilot-instructions.md` as secondary.
- If the repo has no established convention, default to `AGENTS.md` for project memory and `USER.md` for stable user preferences.
- On first project init, or when the user asks to reset or change local preferences, use the installed `USER.template.md` as a questionnaire and target-config input. Ask which preset and checklist items to enable, then create or repair ignored local `USER.md` with only selected checked preferences. Prefer `scripts/render_user_preferences.py` when available. Do not copy or commit `USER.template.md` into a target repo by default.
- Shared/user-facing docs are the primary project explanation, but primary does not mean eager full-context loading. Use selective reads unless the task requires the whole document.
- If a shared doc becomes long or structurally important, maintain a README structure map in agent-facing documentation. Store headings, section purposes, routing hints, and update triggers there; do not copy user-facing prose.
- References define protocols; templates define copyable skill-level seeds. Project-level artifacts instantiated from Project Meta seeds must be concrete to that project and keep `instantiated_from`, `source_reference`, owner, review policy, and last review metadata.
- The canonical `/project-meta <command>` route table lives in `references/cli-command-patterns.md`. Keep this entrypoint to trigger policy and reference-routing summaries; do not duplicate command workflow contracts here.
- In larger repos, prefer a short project-memory loader/index plus narrow topical memory files.
- If the repo-memory structure is missing, bloated, inconsistent, or messy enough to slow future work, restructure it instead of working around it.
- Keep repo memory concise, durable, and free of speculative or session-only notes.
- Update only the canonical file that matches the lesson learned. Sync mirrors only when canonical structure or high-priority guidance changed.
- Verify external best practices from official or primary sources when the task depends on tooling or framework guidance that may have changed.
- Check available skills and use obvious matches immediately.
- Treat repeated agent mistakes as missing harness: improve documentation, routing, validation, or tooling instead of only patching the immediate output.
- Make the harness agent-legible: a concise map, versioned sources of truth, selective loading, behavior guardrails, and rules that can be verified or promoted into tooling.
- Preserve the existing agent-facing documentation framework and pair it with user-facing documentation prepared for user review.
- Trigger the multi-agent protocol when the user explicitly asks for it or when complexity warrants it. For complex work, separate planning from execution: a lead agent owns decomposition, context packaging, review criteria, and integration while workers handle bounded subtasks.
- Before committing harness changes, present a concise delivery for user review that separates user-facing documentation from agent-facing documentation.

## Gotchas

Non-obvious traps the agent will hit without being warned. Keep these here, not in references — the agent reads them before encountering the situation.

- **`USER.md` is local-only and Git-ignored.** Never stage or commit it. The skill's `.gitignore.template` must be merged into the target repo's `.gitignore` before any `USER.md` exists, otherwise the first init may track it accidentally.
- **`USER.template.md` is a skill-layer questionnaire, not a target-repo file.** Do not copy it into target repos. Render selected presets and checked items directly into ignored local `USER.md` via `scripts/render_user_preferences.py`.
- **`templates/*.md` are skill-level seeds, not a target-repo template library.** Instantiate at semantic project paths (`agents/delegation.md`, `agents/pre-commit-delivery.md`, `agents/readme-structure.md`, etc.); do not commit a generic `agents/templates/*.md` directory in the target repo.
- **Every instantiated artifact carries a YAML provenance frontmatter block** (`artifact_name`, `instantiated_from`, `source_reference`, `project_scope`, `owner`, `review_policy`, `last_reviewed`). Do not strip these fields when editing — the manifest and audit checks rely on them.
- **`scripts/validate_project_meta.py` requires a git working tree** for the `check_memory_boundaries` git ignore checks. Outside one, those sub-checks are skipped (the script no longer crashes), but a full validation still requires running from the dev repo or a git checkout.
- **Mirrors (`CLAUDE.md`, `.github/copilot-instructions.md`) are secondary**, not alternate manuals. Do not write a rule into a mirror that is not already in the canonical memory file. Sync mirrors only after canonical structure or high-priority guidance has changed.
- **`/project-meta init` does not depend on existing `USER.md`.** Do not assume preferences exist before init runs; ask for preset and checklist selection first, then render `USER.md`.

## Quick Workflow

1. Bootstrap the repo context from the canonical memory files and a lightweight read of shared docs when present.
2. Classify the task: bootstrap, memory CRUD, harness design, project iteration, mirror sync, or complex coordination.
3. If this is a `/project-meta` command, load `references/cli-command-patterns.md` and run the mapped workflow.
4. Load only the reference files needed for the task classification.
5. Decide whether repo memory should stay monolithic or use a loader plus topical files.
6. If the current structure is missing, messy, contradictory, or clearly inefficient to load, clean it up as part of the task instead of preserving the disorder.
7. Extract only the constraints relevant to the current task.
8. Check whether important memory rules are merely advisory or can be made mechanically checkable.
9. When a protocol needs a repeated output shape, use the matching skill-level canonical template seed and instantiate a concrete project artifact instead of rewriting the shape ad hoc.
10. During the task, keep short notes only for durable reusable knowledge.
11. Before finishing, update the correct canonical file if and only if the lesson is durable and specific enough to matter again.

## When To Load References

- Need to run `/project-meta init`, start a project, preserve lessons across iterations, or decide what should evolve after project work:
  - load [`references/project-lifecycle.md`](references/project-lifecycle.md)
- Need to reset or change local `USER.md` options:
  - load [`references/project-lifecycle.md`](references/project-lifecycle.md), then run `python3 scripts/render_user_preferences.py --target-root <repo> --reset`
- Need to interpret `/project-meta <command>` workflows or change the supported command route table:
  - load [`references/cli-command-patterns.md`](references/cli-command-patterns.md)
- Need behavior guardrails for any agent editing, reviewing, or refactoring project memory:
  - load [`references/agent-behavior-protocol.md`](references/agent-behavior-protocol.md)
- Need hard-stop categories, soft budgets, or worker constraints for bounded-execution agents (Codex-class workers, scope gates, halt-and-ask rules):
  - load [`references/execution-policy.md`](references/execution-policy.md), then [`templates/execution-rules.md`](templates/execution-rules.md) when instantiating
- Need to create or review agent-facing docs, user-facing docs, or pre-commit delivery:
  - load [`references/documentation-delivery.md`](references/documentation-delivery.md)
- Need to instantiate or review project-specific artifacts from skill-level templates:
  - load [`references/documentation-delivery.md`](references/documentation-delivery.md), then the relevant `templates/*.md` seed
- Need to decide monolith vs split memory, or how the project-memory loader should stay thin:
  - load [`references/repo-memory-structure.md`](references/repo-memory-structure.md)
- Need to inspect long shared docs while minimizing context:
  - use `python3 scripts/extract_doc_context.py <doc> --index`, then a bounded `--heading` or `--query` extraction
- Need create/read/update/delete rules for canonical memory files:
  - load [`references/repo-memory-crud.md`](references/repo-memory-crud.md)
- Need mirror policy for tool-specific instruction files:
  - load [`references/mirrors-and-updates.md`](references/mirrors-and-updates.md)
- Need to audit or redesign a repo-memory harness for agent-legibility, enforcement, or recurring cleanup:
  - load [`references/harness-engineering.md`](references/harness-engineering.md)
- User explicitly asks for multi-agent coordination, or task complexity warrants planning, delegated execution, and review:
  - load [`references/multi-agent-protocols.md`](references/multi-agent-protocols.md)

## End Check

- Would a future agent likely waste time, break something, or repeat this discovery without the note?
- Is the note durable, repo-relevant or user-relevant, and specific enough to act on?
- Should the lesson remain documentation, or should it become a linter, script, template, checklist, or recurring cleanup routine?
- Has the pre-commit delivery been shown to the user when a commit will be created?
- If the note passes the durability check, update the relevant canonical memory file. If not, leave memory untouched.
