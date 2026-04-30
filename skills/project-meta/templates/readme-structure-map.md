---
template_name: readme-structure-map
description: "Seed template for an agent-facing heading map and routing guide for long shared docs."
source_reference: references/repo-memory-structure.md
intended_project_path: agents/readme-structure.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-when-routing-changes-user-facing-behavior
---

# README Structure Map Template

Use this seed when a shared doc is long enough that full reads waste context.

## Project Artifact Frontmatter

```yaml
---
artifact_name: readme-structure-map
instantiated_from: project-meta/templates/readme-structure-map.md
source_reference: project-meta/references/repo-memory-structure.md
project_scope: this repo only
owner: agent-facing
review_policy: user review when routing changes user-facing behavior
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```text
Source: <README.md | docs/user/index.md | other shared doc>
Last reviewed: <commit or YYYY-MM-DD>

Heading map:
- <H1/H2 path> lines <start-end>: <one-line purpose>

Routing hints:
- <task type>: read <heading path> with <bounded command or line range>

Update triggers:
- shared-doc heading changed
- section order changed
- user-facing behavior changed
- bounded extractor output no longer matches expected lines
```

## Instantiation Rules

- Store headings, line ranges, section purposes, and routing hints only.
- Do not copy user-facing prose into this map.
- Prefer `python3 scripts/extract_doc_context.py <doc> --index` when available.
- Do not store this as a generic target-project template under `agents/templates/`; instantiate the concrete README route map for the project.
