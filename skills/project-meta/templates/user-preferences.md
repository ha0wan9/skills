---
template_name: user-preferences
description: "Seed template for local project-specific user collaboration preferences."
source_reference: references/project-lifecycle.md
intended_project_path: USER.md
owner: local-user
secure_derivation: required
review_policy: user-review-owned-local-only
---

# User Preferences Template

Use this seed as the source for the `/project-meta init` preference questionnaire.

## Project Artifact Frontmatter

```yaml
---
artifact_name: user-preferences
instantiated_from: project-meta/templates/user-preferences.md
source_reference: project-meta/references/project-lifecycle.md
project_scope: this repo only
owner: local-user
review_policy: user-owned local-only
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```text
# User Preferences

Selected preset: <Minimal | Structured | Strict | Secure | Custom>

- [x] <selected stable collaboration preference>
- [x] <selected commit, review, validation, or interaction preference>
- [x] <selected tooling preference that should remain local>
```

## Instantiation Rules

- Keep the generated `USER.md` local-only and ignored by Git.
- Ask the user which preset and checklist items to enable before rendering, including when resetting or changing an existing `USER.md`.
- Render only the selected checked preferences into `USER.md`; do not copy the full questionnaire body.
- Do not create or commit a root `USER.template.md` in target projects by default.
- Do not store secrets, transient machine state, unresolved hypotheses, or project facts here.
- Promote project facts to project memory instead of user preference memory.
