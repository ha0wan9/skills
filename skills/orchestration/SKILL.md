---
name: orchestration
description: "Turn a chosen roadmap milestone or build plan into a committed, reviewable orchestration contract — per task: model tier, parallelization, orchestrator effort, human-in-the-loop checkpoints, review level, and a non-predictive budget hint — then hand the signed contract to the runtime's scripted engine (Claude Code Workflow or Codex Agents-SDK), degrading to an Agent/Task subagent loop when no scripted engine is available. Owns orchestration policy, never the run engine: it builds no worker pool or run loop, and only calls the Workflow tool when you invoke it. Use when you want to orchestrate a milestone across multiple agents, draft or review an orchestration contract before a run, or estimate the model and token cost of a multi-agent run before committing."
metadata: {version: 0.5.1, compat: [claude-code, codex], published: [claude-marketplace]}
---

# Orchestration

> **Runtimes:** Claude Code · Codex &nbsp;|&nbsp; **Published:** Claude Marketplace
> _OpenClaw / no scripted engine: degrades to the Agent/Task subagent-loop floor._

Turn a **chosen milestone** (from a project-meta roadmap) into a **committed, reviewable
orchestration contract**, then hand that signed contract to the runtime's scripted engine —
without re-implementing the engine. This skill owns the **policy** (which tasks run at which
tier, in what parallel shape, behind which review level and human checkpoints, at roughly what
cost); the **engine owns the mechanism** (the actual run loop). AP-COORD-7.

It sits one step past `/project-meta plan`: `plan` produces the falsifiable build plan for one
milestone; `orchestrate` decides *how that plan is run*.

## Trigger Decision

Use this skill when:

- **Command trigger:** the user says `/orchestrate` or asks to "orchestrate" a milestone, build
  plan, or a body of multi-agent work.
- **Contract trigger:** the user wants to draft, review, or sign an **orchestration contract**
  before a run (model tiers, parallelization, checkpoints, review level, budget hint).
- **Budget trigger:** the user wants a coarse **cost/token estimate** for a multi-agent run
  before committing to it.

Do **not** use this skill to *build* a run engine, to launch the engine from a hook or
autonomously, or to enable `ultracode` session-mode. It prepares and (only on your invocation)
emits to the engine; it never owns or enables it. For grooming the backlog/roadmap or turning a
milestone into a build plan first, use **project-meta** (`roadmap`, then `plan`).

## Dependency & Canon

This skill **declares `project-meta` as a dependency** (the upstream/root skill). The canonical
cross-cutting conventions live there and are cited from **one** place each (single swappable
pointer); the floor below is a self-contained ~10-line restatement so the skill still runs if
project-meta is not installed. When both are present, **project-meta is canonical.**

- **Multi-agent paradigm (canon):** `project-meta/references/multi-agent-protocols.md`.
- **Review levels L0–L3 (canon):** `project-meta/references/review-tier.md` — the contract's
  `review_level` field names these levels; it does **not** copy the tier table.
- **Codex operating loop (canon):** `project-meta/references/codex-operating-loop.md` — the
  contract snapshots the run context when a Codex-primary run is long-running, artifact-reviewed,
  Goal/Heartbeat-backed, or remotely steered; it does **not** create a separate Codex harness.

**Floor (works without project-meta installed):**

- **Roles:** Lead (orchestrator / contract owner) · Planner · Explorer (read-only) · Worker
  (edits a bounded surface) · Reviewer (independent check on clean context).
- **Reviewer-Between-Subtasks:** brief a fresh worker → a fresh, separate reviewer on clean
  context (diff + brief only); a BLOCKER halts forward dispatch until the user decides
  (AP-COORD-2). A scripted/background runner must stop on the first BLOCKER, never batch them.
- **Model tier:** deterministic → CLI · bounded high-fanout judgment → Haiku (`haiku`, opt-in utility rung below fleet — extract/classify/label/summarize only, never code edits/reviews) · judgment → Sonnet/Luna (fleet, default) · escalation/synth → Opus/Terra · conductor → session model (Fable/Sol-class when available). Escalate one agent to Opus/Terra only on a demonstrated fleet shortfall, never precautionarily (`project-meta/references/multi-agent-protocols.md#model-tier`).
- **Review level:** every review fast; tokens proportionate to stakes — L0 self-check · L1 one
  reviewer · L2 parallel panel · L3 adversarial + pressure (`#review-tier`).
- **Elastic harness:** long-running Codex runs snapshot `HARNESS_PROFILE` / optional bounds and
  name the artifact surface + oracle; elasticity tunes advisory visibility, never authority.
- **Engine boundary (AP-COORD-7):** the contract is **policy**; the scripted engine (Claude Code
  Workflow / Codex Agents-SDK) is **mechanism**. Reference the engine generically so a rename
  can't rot the contract; never hand-roll the run loop; apply safety invariants at promotion time.

## Route

| Verb | Recipe | What it does |
|---|---|---|
| `orchestrate` | [`recipes/orchestrate.md`](recipes/orchestrate.md) | For a chosen milestone: reuse the project-meta build plan, produce an orchestration plan, fill + budget-hint + **sign** the contract, then **emit** it to the engine (engine call only on your invocation). |

## References & assets

- [`references/orchestration-contract.md`](references/orchestration-contract.md) — the contract
  **schema** (single owner): the per-task fields the artifact and recipe both bind to.
- [`references/engine-handoff.md`](references/engine-handoff.md) — how a signed contract is emitted
  to the engine, the two-bar opt-in posture, and the cross-runtime backings + floor.
- [`templates/orchestration-contract.md`](templates/orchestration-contract.md) — the committed,
  reviewable contract artifact, instantiated per run.
- [`scripts/budget_hint.py`](scripts/budget_hint.py) — the coarse, **non-predictive** budget hint
  (`--task tier:class:fanout`). A hint to set expectations before signing, not a forecast, and not
  the engine `budget`.
- [`examples/sample-orchestration-contract.md`](examples/sample-orchestration-contract.md) — a
  filled, **signed** contract orchestrating the v0.3 build plan's Wave 2.

## Cross-Cutting Invariants

- **Policy, not mechanism (AP-COORD-7).** Own the contract; never build a run loop, worker pool, or
  run-journal that duplicates the engine. Reference the engine generically so a rename can't rot it.
- **Engine call only on invocation.** Emit to the Workflow tool / Agents-SDK **only** because the
  user invoked `orchestrate` (the two-bar opt-in: a recipe that names the tool + its cost surface).
  Never from a hook, never autonomously, and never enable `ultracode` (user-only).
- **Sign before emit.** No engine emission before the contract is filled, delivered for operator
  review, and signed. The signed contract is the gate.
- **Checkpoints are synchronous.** A `human_checkpoint` or a BLOCKER review verdict stops forward
  dispatch under any backing — never batch BLOCKERs to end-of-run (AP-COORD-2).
- **The budget hint is not a forecast** and does not drive the engine `budget`.
- **Cross-runtime or floor.** Every contract is emittable on each declared runtime (Workflow / Codex
  Agents-SDK) or degrades to the Agent/Task subagent-loop floor — never an un-runnable contract.

## Gotchas

- **`orchestrate` does not decide *what* is in the milestone.** It runs an already-planned milestone.
  No build plan yet → route back to project-meta (`roadmap`, then `plan`) first.
- **Fan-out is a cost, not a quality lever** (AP-COORD-4). A wide `parallelization` widens the budget
  hint and the coordination surface; it does not improve outcomes by itself.
- **`ultracode` ≠ the Workflow tool.** A skill may call the Workflow tool on invocation; it can never
  enable `ultracode` session-mode (`effortLevel:"ultracode"` set by a skill silently no-ops).
- **Installed alone?** Without project-meta, the Dependency & Canon floor above is the whole contract
  — roles, reviewer-between, model tiers, review levels. With project-meta present, it is canonical.

## Skill Arbitration

When the request could match `orchestration` **and** a peer skill, resolve as follows and state the resolution before acting.

| Request shape | Owner | Notes |
|---|---|---|
| Orchestrate a milestone, draft/review/sign a contract, estimate run cost (`/orchestrate`, contract trigger, budget trigger) | **`orchestration`** | acts |
| Dispatch-policy canon, review-tier levels (`multi-agent-protocols.md`, `review-tier.md`), ad-hoc multi-agent coordination inside a `/project-meta` verb, repo harness / memory work | **`project-meta`** | `project-meta`'s `references/multi-agent-protocols.md` stays canonical; this skill cites it, never duplicates it |
| Create/manage a Claude or Codex config *profile*, or the user's global config root (`~/.claude*`, `~/.codex*`) | **`global-meta`** | defer; user-level config is out of scope here — `global-meta` owns it (and itself defers orchestration *policy* back to this skill + project-meta's canon) |
| Actual engine execution (Workflow tool, "ultracode" session-mode, Codex Agents-SDK run loop) | **the runtime engine** — not a skill | user-gated; never re-implemented here — AP-COORD-7 |

If the request is unclear, ask before acting. Never silently invoke both.

## Output

`/orchestrate` produces a committed, **signed** `docs/plans/<milestone>-orchestration-contract.md`,
delivered for operator review before commit, from which the engine emission (or floor dispatch) is
driven. Run outcomes flow back to the project board status surface (the dashboard renders ①②③ + run
status). The contract — policy signed ahead of the run — is the durable, reviewable artifact.
