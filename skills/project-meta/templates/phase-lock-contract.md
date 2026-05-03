---
template_name: phase-lock-contract
description: "Seed for an opt-in phase-locked workflow contract. Target repo installs this when /project-meta init is run with --workflow phase-lock."
source_reference: references/harness-engineering.md
intended_project_path: agents/phase-lock-contract.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-when-phases-or-gates-change
---

# Phase-Lock Contract Template

Use this seed when a project benefits from explicit phase locks: the agent
moves through brainstorm → plan → implement → review → finish, and each
phase is *gated* — the next does not start until the previous one signs
off.

The contract is opt-in. Lightweight repos (single-purpose scripts,
exploratory notebooks, throwaway prototypes) should not install it. Repos
where bug regression cost is high, where multiple agents collaborate, or
where review traceability matters should.

## Project Artifact Frontmatter

```yaml
---
artifact_name: phase-lock-contract
instantiated_from: project-meta/templates/phase-lock-contract.md
source_reference: project-meta/references/harness-engineering.md
project_scope: this repo only
owner: agent-facing
review_policy: user review when phases or gates change
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

Paste the following into `agents/phase-lock-contract.md` and edit the
phase definitions and gate scripts to match the project. The runtime state
lives in `.harness/phase-state.json` (created by
`scripts/phase_lock_check.py`).

```markdown
# Phase-Lock Contract

This repo enforces phase-locked work for non-trivial changes. Each phase
has an entry condition, an exit gate, and a deliverable. The next phase
does not start until the current phase's gate passes.

## Phases

| Phase | Entry condition | Deliverable | Exit gate |
|---|---|---|---|
| `brainstorm` | a non-trivial change is requested | a written approach (1-3 paragraphs) | the user (or designated reviewer) approves the approach |
| `plan` | brainstorm approved | a `plans/<task-id>.md` file with 2-5 minute task decomposition | the user approves the plan; tasks have explicit acceptance criteria |
| `implement` | plan approved | code changes corresponding to plan tasks | every plan task has matching diff; implementation runs `<verify-script>` clean |
| `review` | implementation gate passed | a review pass against the brainstorm + plan | reviewer agent (or human) signs off; no blocker findings open |
| `finish` | review signed off | merged branch + closed plan file | branch deleted; plan moved to `plans/done/`; lessons promoted to canonical memory if applicable |

Lightweight changes (typo fixes, single-line config, docs-only edits)
bypass the contract. Define what "lightweight" means in your project:

- ≤ N changed lines AND
- no test changes AND
- no public API change AND
- not in path patterns: <list>

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
  reference; `<verify-script>` passes; no debug code committed.
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
```

## Installation

`/project-meta init --workflow phase-lock` performs:

1. Create `agents/phase-lock-contract.md` from this seed.
2. Create `.harness/phase-state.json` with `phase: "none"`.
3. Create `.harness/gates/` with stub `brainstorm.sh`, `plan.sh`,
   `implement.sh`, `review.sh`, `finish.sh` files (each exits 0 by
   default; user fills in the actual checks).
4. Wire the `Stop` hook in `.claude/settings.json` to invoke
   `scripts/phase_lock_check.py` (from the hooks pack).
5. Add `.harness/` to `.gitignore` for state files; keep `gates/`
   tracked.
6. Update `AGENTS.md` to reference `agents/phase-lock-contract.md` in
   the read order.

After installation, the user defines:
- The lightweight criteria (in `agents/phase-lock-contract.md`).
- Each gate script (in `.harness/gates/`).
- The `<verify-script>` reference (project-specific test/lint
  command).

The contract is dormant until populated. Empty gate scripts pass by
default — the contract enforces nothing until the user codifies what
each gate checks.
