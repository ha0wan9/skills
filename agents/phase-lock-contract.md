---
artifact_name: phase-lock-contract
instantiated_from: project-meta/templates/phase-lock-contract.md
source_reference: project-meta/templates/phase-lock-contract.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before gate-policy changes
last_reviewed: 2026-06-13
---

# Phase-Lock Contract

This repo enforces phase-locked work for non-trivial changes. Each phase
has an entry condition, an exit gate, and a deliverable. The next phase
does not start until the current phase's gate passes.

## Phases

| Phase | Entry condition | Deliverable | Exit gate |
|---|---|---|---|
| `brainstorm` | a non-trivial change is requested | a written approach (1-3 paragraphs) | the user (or designated reviewer) approves the approach |
| `plan` | brainstorm approved | a `plans/<task-id>.md` file with 2-5 minute task decomposition | the user approves the plan; tasks have explicit acceptance criteria |
| `implement` | plan approved | code changes corresponding to plan tasks | every plan task has matching diff; implementation runs `python3 scripts/validate_project_meta.py` clean |
| `review` | implementation gate passed | a review pass against the brainstorm + plan | reviewer agent (or human) signs off; no blocker findings open |
| `finish` | review signed off | merged branch + closed plan file | branch deleted; plan moved to `plans/done/`; lessons promoted to canonical memory if applicable |

Lightweight changes (typo fixes, single-line config, docs-only edits)
bypass the contract. Define what "lightweight" means in your project:

- ≤ 20 changed lines AND
- no test changes AND
- no public API change AND
- not in path patterns: `skills/**, AGENTS.md, scripts/**, .claude/**, .claude-plugin/**, agents/**`

## Runtime State

State persists in `.harness/phase-state.json`:

```json
{
  "task_id": "<id>",
  "phase": "brainstorm | plan | implement | review | finish | none",
  "started_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "last_gate_pass_utc": "YYYY-MM-DDTHH:MM:SSZ | null",
  "deliverables": {
    "brainstorm": "<path or inline summary> | null",
    "plan": "<path> | null",
    "implement": ["<commit-sha>", ...],
    "review": "<review-comment-id> | null"
  }
}
```

`scripts/phase_lock_check.py` (installed by /project-meta init) reads this
file to verify gate passage before the next phase starts. The `Stop` hook
in `.claude/settings.json` invokes this script on every turn end.

## Gate Definitions

Define what each gate verifies. Examples:

- **plan gate**: `plans/<task-id>.md` exists, has at least one
  `## Tasks` section, every task has acceptance criteria.
- **implement gate**: every task in the plan has a matching diff or
  reference; `python3 scripts/validate_project_meta.py` passes; no debug code committed.
- **review gate**: a review summary exists; no `BLOCKER` findings open.

Encode each gate as a small bash or python script under
`.harness/gates/<phase>.sh`. Gates exit 0 on pass, non-zero on fail. The
phase-lock check script aggregates them.

## Bypass

When a change is genuinely lightweight, the agent (or user) declares
bypass:

```
/phase-lock bypass --reason "<reason>"
```

Bypasses are logged to `.harness/bypass-log.jsonl`. Periodic audit
should review bypass frequency; if bypasses become routine, the
lightweight criteria are too narrow.

## Anti-patterns

- **Phase-lock as ceremony, not safety.** If gates always pass on first
  try, they're rubber stamps. Tighten gates until they actually catch
  something or remove them.
- **Treating bypass as the default.** A repo where most changes bypass
  isn't using the contract. Either tighten lightweight criteria or
  uninstall the contract.
- **Gates as a prose checklist.** Gates that are not mechanically
  checkable degrade to honor system. Make gates scripts. AP-VAL-1.
- **Plan drift.** A plan that doesn't get updated as implementation
  proceeds becomes stale. Either update or mark superseded; never
  ignore. AP-COORD-3.
