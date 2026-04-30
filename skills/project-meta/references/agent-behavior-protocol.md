# Agent Behavior Protocol

Use this reference when writing, reviewing, or refactoring project harness guidance.

## Principles

- Think before editing: identify the task type, assumptions, target files, and success criteria.
- Keep it simple: prefer the smallest memory structure and protocol that solves the recurring problem.
- Make surgical changes: touch only files required by the request or necessary consistency updates.
- Stay goal-driven: define what must be true at the end and verify it before finalizing.
- Preserve context discipline: load only relevant references and avoid bulk-loading the whole harness.
- Keep memory clean: write only durable, reusable knowledge into canonical memory.

## Success Criteria Template

Before editing, state or infer:

```text
Goal: <requested outcome>
Target files: <files likely to change>
Must remain unchanged: <scope boundaries>
Validation: <diff check, lint, tests, review pass, or none available>
Memory writeback: <none | AGENTS.md | USER.md | topical reference | mirror>
```

## Editing Rules

- Every changed line should trace to the user request, a required consistency update, or a validated durable lesson.
- Keep `SKILL.md` as the router and move detailed guidance into `references/`.
- Keep `AGENTS.md` as the project-memory loader for this repo.
- Keep `USER.md` for stable user collaboration preferences.
- Prefer replacing stale guidance over appending exceptions.
- If a rule is repeatedly missed, strengthen routing, examples, validation, or tooling.

## Review Questions

- Did the change improve future agent behavior without bloating the entrypoint?
- Is the new guidance project-specific, user-specific, or general reference material?
- Is the trigger too broad, too narrow, or dependent on body text that will not load before triggering?
- Can the guidance be validated mechanically?
- Did the change introduce another source of truth?
