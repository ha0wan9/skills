# Reference: the orchestration contract (schema — single owner)

**DASH-10.** The orchestration contract is a **committed, reviewable artifact signed ahead of a
run**. This file is the **single owner of its schema**: the template
([`templates/orchestration-contract.md`](../templates/orchestration-contract.md)) and the recipe
([`recipes/orchestrate.md`](../recipes/orchestrate.md)) bind to the fields defined here and must
not redefine them. Change the schema here, in one place.

A contract is **policy, not a run engine** (AP-COORD-7). It describes *how a chosen milestone
should be run*; the engine ([`engine-handoff.md`](engine-handoff.md)) executes it.

## What a contract covers

One contract per **chosen milestone / build plan**. It has a small **header** (provenance + which
plan it orchestrates) and a **per-task table** — one row per task in the build plan's build order.

## Per-task schema

Each task row carries exactly these fields:

| Field | Values | Meaning |
|---|---|---|
| `task` | free text + (optional) build-plan item id | the unit of work, traceable back to the `plan` build order |
| `model_tier` | `cli` · `sonnet` · `opus` · `fable` | deterministic → CLI (no model); judgment → Sonnet (fleet, default); escalation/synth → Opus (one escalation slot + one synthesis slot max per pipeline); conductor-only → Fable (at most one dispatched unblock call after Opus failed; justify per-slot). Escalate to Opus only on a demonstrated fleet shortfall, never precautionarily. (canon: `project-meta/references/multi-agent-protocols.md#model-tier`) |
| `parallelization` | `serial` · `parallel(N)` · `pipeline` | the fan-out shape. Fan-out is a *cost and a coordination* signal, not a quality one (AP-COORD-4: don't over-parallelize). |
| `orchestrator_effort` | `low` · `medium` · `high` | how much the Lead invests coordinating this task (brief depth, re-brief budget). Distinct from `model_tier` of the workers. |
| `human_checkpoint` | `none` · `before` · `after` · `both` | the explicit halt-and-ask points (🔴). New dep / ops / live backend / push / unresolved decision MUST carry a checkpoint (execution-policy). |
| `review_level` | `L0` · `L1` · `L2` · `L3` | the review-tier level for this task's output. **Names the level only** — the canonical L0–L3 definitions live in `project-meta/references/review-tier.md`. Auto-derive a floor with `review_tier.py`; the Lead escalates on judgment and states why (never silently de-escalates high stakes). |
| `budget_hint` | `<tier>:<class>:<fanout>` | the input line for `budget_hint.py` for this task. Coarse, non-predictive — see below. |

## Budget hint (DASH-22) — coarse, non-predictive

The contract carries a **budget hint**, never a forecast. Pre-run agentic token/runtime prediction
is order-of-magnitude unreliable, so the hint is a **wide low/expected/high band labelled "estimate,
not a guarantee."** Compute it with [`scripts/budget_hint.py`](../scripts/budget_hint.py), summing
the per-task `budget_hint` lines. Its purpose is to let the operator eyeball "this contract is
Opus-heavy / fan-out-wide" and adjust tiers/parallelism **before signing**.

The hint **does not drive the engine `budget`** and the skill **cannot enable or control the
engine** (AP-COORD-7). There is no calibration claim: the bands are heuristic constants, not fit to
a cost corpus (none exists yet).

## Tier-mix footer

Every signed contract includes a **tier-mix footer** line:

```
tier-mix: <tok-share>% fleet / <n>×opus / <n>×fable / <n>×cli
```

`<tok-share>` is the fleet token-share computed from the `budget_hint.py` per-task expected-token
totals (fleet expected tokens ÷ total expected tokens × 100). Target: ≥80 % fleet token-share.
`<n>×opus` and `<n>×fable` are the count of tasks at those tiers; `0×fable` is the documented
normal case (Fable is conductor-only; dispatched Fable is exceptional). Computed at contract-signing
time; re-check if any task's `model_tier` or `budget_hint` changes.

## Signing

A contract is **signed** when (a) every build-order task has a row, (b) the per-task review levels
and human checkpoints are set and justified where escalated, (c) the budget hint has been computed
and reviewed, and (d) the tier-mix footer is present and the fleet token-share target is met or the
deviation is explained. Signing is the gate **before** any engine emission. The signed contract is
committed (it is a shared, user-facing artifact → deliver for operator review before commit, like
every editing recipe).

## Invariants

- **Single owner.** Fields are defined here once; template + recipe bind, never redefine.
- **Policy, not mechanism.** No field describes engine internals (worker-pool size as a *mechanism*,
  run-journal format, retry loops). `parallelization` is a *requested shape*, handed to the engine.
- **Names, not copies.** `review_level` names review-tier levels; `model_tier` names the canon tiers.
  The contract does not restate those tables.
- **Traceable.** Every task row maps back to a build-plan item, so the contract is checkable against
  the plan it orchestrates.
