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

This repo's `.harness/gates/*.sh` are real, mechanically-checkable gates
(POSIX sh, deterministic, no network). Each exits 0 on pass, 1 on fail
with a one-line reason to stderr.

- **`brainstorm.sh`** — **stays a stub (`exit 0`) by decision.** There is
  nothing mechanical to check at this phase: the deliverable is a
  written approach reviewed by a human/reviewer agent, which is a
  judgment call, not a file-shape or command-exit-code fact. Revisit
  only if a future convention (e.g. a required `brainstorm-note.md`
  path) gives this phase a checkable artifact.
- **`plan.sh`** — checks that `.harness/phase-state.json` (path
  overridable via `HARNESS_STATE_FILE`, default `.harness/phase-state.json`)
  names a `build_plan` field (new optional field, written at plan entry)
  and that the file it points to exists on disk. Unset, missing, or
  pointing at a nonexistent path all exit 1.
- **`implement.sh`** — runs `scripts/ship_plugin.sh validate` and exits
  0 iff that exits 0. `validate` covers marketplace.json coherence, the
  version-bump gate (`check-version`), and per-plugin dev validators for
  any plugin touched vs `BASE_BRANCH`.
- **`review.sh`** — checks that `.harness/last-turn-meta.json` (path
  overridable via `HARNESS_LAST_TURN_META_FILE`) exists and contains a
  non-empty `review_tier` string. File-derived, not a ledger query
  (same precedent as D5 elsewhere in the harness): the review-tier
  decision is written to a small file by whatever review workflow ran,
  and this gate just confirms that record exists.
- **`finish.sh`** — runs `scripts/ship_plugin.sh check-version` and
  exits 0 iff that exits 0, i.e. a version bump exists vs `BASE_BRANCH`
  for every changed plugin (or the marketplace version, for root-only
  changes).

Each gate script's own header comment documents its check. The
phase-lock check script (`skills/project-meta/scripts/phase_lock_check.py`)
aggregates them: it reads `.harness/phase-state.json` for the current
phase and invokes `.harness/gates/<phase>.sh` from the repo root.

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
