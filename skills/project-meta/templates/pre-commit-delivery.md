---
template_name: pre-commit-delivery
description: "Seed template for user review before committing harness or documentation changes."
source_reference: references/documentation-delivery.md
intended_project_path: agents/pre-commit-delivery.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-before-every-commit-when-enabled
---

# Pre-Commit Delivery Template

Use this seed when a project requires a review packet before commit.

## Project Artifact Frontmatter

```yaml
---
artifact_name: pre-commit-delivery
instantiated_from: project-meta/templates/pre-commit-delivery.md
source_reference: project-meta/references/documentation-delivery.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before commit
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

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

## Instantiation Rules

- Add project-specific required checks under `Validation`.
- If user-facing docs changed, ask for review before committing unless the user already approved the exact delivery.
- Keep local-only files such as `USER.md` out of commit scope.
- Do not store this as a generic target-project template under `agents/templates/`; instantiate a concrete project delivery artifact instead.
