---
template_name: project-artifact-manifest
description: "Seed template for tracking Project Meta-instantiated project artifacts and their provenance."
source_reference: references/documentation-delivery.md
intended_project_path: agents/project-artifacts.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-before-artifact-policy-changes
---

# Project Artifact Manifest

Use this seed when a project instantiates multiple concrete artifacts from Project Meta skill-level templates.

The manifest is the project-level index for instantiated artifacts. It must agree with each artifact's YAML frontmatter and should be refreshed whenever an artifact, its canonical seed, or its source reference changes.

## Project Artifact Frontmatter

```yaml
---
artifact_name: project-artifact-manifest
instantiated_from: project-meta/templates/project-artifact-manifest.md
source_reference: project-meta/references/documentation-delivery.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before artifact policy changes
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```text
# Project Artifact Manifest

Artifacts:
- path: agents/<artifact>.md
  artifact_name: <name>
  instantiated_from: project-meta/templates/<name>.md
  source_reference: project-meta/references/<reference>.md
  owner: <agent-facing | shared-user-facing | local-user>
  review_policy: <project review rule>
  last_reviewed: <YYYY-MM-DD or approved immutable review marker>
  refresh_trigger: <when to refresh this artifact>
```

## Instantiation Rules

- Keep one manifest for Project Meta-instantiated artifacts when more than one exists.
- Each entry must correspond to a concrete project artifact and repeat its required provenance fields.
- `path`, `artifact_name`, `instantiated_from`, `source_reference`, `owner`, `review_policy`, `last_reviewed`, and `refresh_trigger` are required for each entry.
- If a manifest entry and artifact frontmatter disagree, repair the manifest against the artifact frontmatter before delivery.
- Refresh `last_reviewed` when a source template or source reference changes.
- Do not use this manifest to create a target-project template library under `agents/templates/`.
- In Secure or Strict mode, show a delivery before adding, overwriting, or deleting project-level artifacts.
