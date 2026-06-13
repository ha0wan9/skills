---
template_name: codex-operating-loop
description: "Seed for a target repo's agents/codex-operating-loop.md: durable Codex threads, disk-backed memory, elastic harness profile state, side-panel/browser artifact review, Goals/Heartbeats, remote check-ins, and verification oracles."
source_reference: references/codex-operating-loop.md
intended_project_path: agents/codex-operating-loop.md
owner: agent-facing
secure_derivation: required
review_policy: review-when-codex-loop-or-automation-changes
---

# Codex Operating Loop Template

SEED - instantiate to `agents/codex-operating-loop.md` when Codex is the primary host for long-running repo work. This artifact is part of the elastic harness ecosystem: it records how the repo's Codex loop uses `HARNESS_PROFILE`, optional elastic bounds, hooks, receipts, lessons, board/issue tracking, and verification oracles.

## Project Artifact Frontmatter

```yaml
---
artifact_name: codex-operating-loop
instantiated_from: project-meta/templates/codex-operating-loop.md
source_reference: project-meta/references/codex-operating-loop.md
project_scope: this repo only
owner: agent-facing
review_policy: review-when-codex-loop-or-automation-changes
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```markdown
# Codex Operating Loop

Use this file when Codex is running long-lived work in this repository: pinned threads, remote check-ins, side-panel/browser artifact review, Goals, Heartbeats, recurring monitors, or multi-turn project state.

## State Surfaces

| Surface | Path / tool | Rule |
| --- | --- | --- |
| Canonical memory | AGENTS.md + agents/*.md | Durable rules and routing only. No task logs. |
| Recent handoff | .harness/session-receipt.json | Git-ignored transient receipt. Promote only durable facts. |
| Elastic profile | HARNESS_PROFILE=<PROFILE>; bounds=<FLOOR>..<CEILING>; effective=.harness/effective-profile | Effective profile tunes advisory reminders only. Invariant gates keep raw HARNESS_PROFILE. |
| Work queue | <BOARD_OR_TRACKER> | Open loops live here, with repo backlinks. |
| Review artifact | <HTML_OR_APP_OR_DOC_PATH> | Prefer inspectable artifacts for visual/table/slide/UI work. |
| Verification oracle | <TEST_OR_CHECK_COMMAND_OR_ACCEPTANCE_RULE> | A Goal is not done until this passes or the human approval gate is recorded. |

## Rules

- Files are durable memory; thread history is cache.
- Memory write-backs must be reviewable as diffs.
- Steering can refine the active goal, but it does not expand write scope or bypass approval-sensitive actions.
- Browser or side-panel observations that affect future work must change an artifact, issue, board item, or delivery summary.
- Goals must name a concrete finish line: tests, fixtures, artifact inspection, checklist, or human approval.
- Heartbeats must name cadence, data source, action boundary, writeback target, and stop/escalation condition.
- Remote check-ins unblock decisions; they do not bypass destructive/network/auth/dependency/public-API gates.
- External messages are drafted by default. Sending requires explicit user authorization.
- Elasticity tunes friction, not authority: `.harness/effective-profile` may affect receipt/lesson reminder verbosity, but it cannot authorize writes, sends, installs, network calls, dependency changes, public API changes, or merges.
- The loop is on only when this artifact is routed from AGENTS.md and each backing capability it names is installed or explicitly marked manual.
```

## AGENTS.md Insert

Add this to the target repo's canonical `AGENTS.md` when the artifact is instantiated:

```markdown
## Codex Operating Loop

For Codex-primary long-running work, read [agents/codex-operating-loop.md](agents/codex-operating-loop.md) before creating Goals, Heartbeats, recurring monitors, side-panel/browser review artifacts, or remote-check-in loops.
```

## Instantiation Rules

- Fill every `<ANGLE_BRACKET>` placeholder before committing the instantiated artifact.
- Route the artifact from canonical `AGENTS.md`.
- Add a row to `agents/project-artifacts.md` when that manifest exists.
- Pair the artifact with hooks/session receipts and board or issue-tracker storage when those capabilities are enabled.
- Fill the elastic profile row from the current `/project-meta settings` state. If hooks or elastic bounds are absent, write `manual-policy-only` or `disabled`; do not imply enforcement that is not installed.
- Do not create a Codex-only strictness dial. Use the existing `HARNESS_PROFILE` and bounded elastic profile machinery.
- Do not store this template under `agents/templates/` in the target repo.
