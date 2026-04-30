---
template_name: memory-writeback-check
description: "Seed template for deciding whether a lesson should become durable project memory."
source_reference: references/repo-memory-crud.md
intended_project_path: agents/memory-writeback-check.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-when-memory-policy-changes
---

# Memory Writeback Check Template

Use this seed at task closeout before updating canonical memory.

## Project Artifact Frontmatter

```yaml
---
artifact_name: memory-writeback-check
instantiated_from: project-meta/templates/memory-writeback-check.md
source_reference: project-meta/references/repo-memory-crud.md
project_scope: this repo only
owner: agent-facing
review_policy: user review when memory policy changes
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```text
Durable lesson:
- <lesson>

Memory owner:
- <AGENTS.md | agents/*.md | USER.md | mirror | none>

Writeback decision:
- <write now | suggest only | skip>

Reason:
- <why this will or will not matter again>

Validation:
- <command, review, or evidence confirming the lesson>
```

## Instantiation Rules

- Write repo facts to project memory and user preferences to `USER.md`.
- Do not write session logs, guesses, secrets, or local transient state.
- Prefer replacing stale guidance over adding contradictory notes.
- Do not store this as a generic target-project template under `agents/templates/`; instantiate a concrete project writeback check instead.
