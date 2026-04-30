---
template_name: delegation
description: "Seed template for bounded explorer, worker, and reviewer delegation."
source_reference: references/multi-agent-protocols.md
intended_project_path: agents/delegation.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-before-behavior-changing-commit
---

# Delegation Template

Use this seed when a project needs reusable context packages for multi-agent work.

## Project Artifact Frontmatter

```yaml
---
artifact_name: delegation
instantiated_from: project-meta/templates/delegation.md
source_reference: project-meta/references/multi-agent-protocols.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before first behavior-changing commit
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```text
Role: <Explorer | Worker | Reviewer>
Goal: <exact question or artifact>
Read first:
- <smallest required path>
- <smallest required path>
Ownership: <read-only | may edit exact files>
Constraints:
- <relevant AGENTS.md, SKILL.md, or project artifact rule>
Output format: <findings | patch summary | review notes | decision>
Review criteria:
- <pass/fail condition>
Memory policy: <may suggest updates | may edit canonical memory | report only>
```

## Instantiation Rules

- Keep project-specific file paths, validation commands, and ownership boundaries in the instantiated project artifact.
- Do not remove the `instantiated_from` or `source_reference` fields.
- Do not store this as a generic target-project template under `agents/templates/`; instantiate a concrete project artifact instead.
- In Secure or Strict mode, do not overwrite an existing project artifact without showing a delivery.
