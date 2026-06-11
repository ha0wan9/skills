---
artifact_name: project-artifact-manifest
instantiated_from: project-meta/templates/project-artifact-manifest.md
source_reference: project-meta/references/documentation-delivery.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before artifact policy changes
last_reviewed: 2026-06-11
---

# Project Artifact Manifest

Artifacts:
- path: docs/plans/project-board-v0.2-build-plan.md
  artifact_name: project-board-v0.2-build-plan
  instantiated_from: project-meta/templates/building-plan.md
  source_reference: docs/backlog/project-board-system.md
  owner: shared-user-facing
  review_policy: per-wave fresh-context review before land
  last_reviewed: 2026-06-06
  refresh_trigger: milestone v0.2 scope changes (historical — shipped)
- path: docs/plans/project-board-v0.3-build-plan.md
  artifact_name: project-board-v0.3-build-plan
  instantiated_from: project-meta/templates/building-plan.md
  source_reference: docs/backlog/project-board-system.md
  owner: shared-user-facing
  review_policy: per-wave fresh-context review before land
  last_reviewed: 2026-06-07
  refresh_trigger: milestone v0.3 scope changes (historical — shipped)
- path: docs/plans/global-meta-lifecycle-build-plan.md
  artifact_name: global-meta-lifecycle-build-plan
  instantiated_from: project-meta/templates/building-plan.md
  source_reference: docs/backlog/project-board-system.md; skills/project-meta/proposals/global-meta.md
  owner: shared-user-facing
  review_policy: user review when goal or readiness changes; per-PR fresh-context review before land
  last_reviewed: 2026-06-11
  refresh_trigger: v0.5 milestone scope changes, readiness re-audit, or a DASH-035 spike verdict that flips DASH-036
