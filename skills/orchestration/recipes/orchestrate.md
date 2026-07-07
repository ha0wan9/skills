# Recipe: orchestrate

**DASH-09.** Turn a **chosen milestone** into a run: reuse the project-meta build plan, produce an
orchestration plan, fill + budget-hint + **sign** the contract, then (only on your invocation)
**emit** it to the engine. This is the step *past* `/project-meta plan` — `plan` produces the
falsifiable build plan; `orchestrate` decides how it is run.

## When to load

- User invokes `/orchestrate` or asks to "orchestrate" a milestone / build plan / multi-agent run.
- A milestone already has a `plan` build plan and the user wants to run it across agents.

## Mode

**editing** — produces a committed, reviewable contract artifact. Judgment-heavy (tier/parallel/
checkpoint decisions) → runs on the **main session model (Fable-class when available; see model-tier
canon)** (the conductor tier). Per-task review panels delegate to Sonnet (fleet). Interactive: this
skill emits to the engine **only when the user invoked `orchestrate`** (the two-bar opt-in;
[`engine-handoff.md`](../references/engine-handoff.md)).

## Required references

- [`references/orchestration-contract.md`](../references/orchestration-contract.md) — the contract
  **schema** (single owner) every task row binds to.
- [`references/engine-handoff.md`](../references/engine-handoff.md) — the opt-in posture + the
  cross-runtime backings the **emit** step uses.
- `project-meta/references/review-tier.md` — the L0–L3 levels a task's `review_level` names.
- `project-meta/references/multi-agent-protocols.md` — the dispatch paradigm + model-tier canon.
- `project-meta/references/codex-operating-loop.md` — required only when the contract's
  `operating_loop` is Codex long-running / Goal / Heartbeat / remote-check-in oriented.

## Prerequisite

A **chosen milestone with a build plan**. If there is no build plan yet, route back to project-meta:
groom with `roadmap`, then `plan` the milestone. `orchestrate` does **not** decide *what* goes in the
milestone — it decides how the already-planned work runs.

## Workflow — produce → sign → emit

1. **Read the build plan.** Take its **build order** (the dependency-ordered task list) as the rows
   of the contract. Reuse the plan's items verbatim — do not re-decompose.
2. **Snapshot the run context.** Fill the contract-level `operating_loop`,
   `harness_profile_snapshot`, `artifact_review_surface`, `state_writeback_target`, and
   `verification_oracle`. For Codex long-running / Goal / Heartbeat / remote-check-in runs, cite
   the Codex operating-loop canon and make sure the oracle is concrete before signing.
3. **Produce the orchestration plan.** For each task decide: `model_tier` (deterministic→cli ·
   bounded high-fanout judgment→haiku (opt-in utility rung below fleet; extract/classify/label/
   summarize only — never code edits/reviews) · judgment→sonnet fleet default · escalation/synth→
   opus · conductor→fable; escalate only on a demonstrated fleet shortfall), `parallelization`
   (serial / parallel(N) / pipeline — fan-out is a cost, not a quality lever; AP-COORD-4),
   `orchestrator_effort`, `human_checkpoint` (🔴 for new dep / ops / live backend / push / open
   decision), and `review_level` (auto-derive a floor with `review_tier.py`; escalate on judgment
   and **state why** — never silently de-escalate high stakes).
4. **Budget-hint it.** Run [`scripts/budget_hint.py`](../scripts/budget_hint.py) (python3, stdlib
   only — no install) over the per-task `tier:class:fanout` lines. Paste the wide low/expected/high
   band into the contract, plus its **auto-computed tier-mix line** (the tool prints one — do not
   hand-compute it) and any `WARN: fleet token-share below 80% target` line it appends when the
   haiku+sonnet fleet share falls short. It is a
   **hint to eyeball Opus-heaviness / fan-out width before signing — "estimate, not a guarantee,"**
   not the engine `budget`. If it looks Opus-heavy or too wide, or the WARN fires, adjust
   tiers/parallelism and re-run.
5. **Instantiate + deliver the contract.** Fill
   [`templates/orchestration-contract.md`](../templates/orchestration-contract.md). Include the
   tier-mix footer pasted verbatim from `budget_hint.py`'s output:
   `tier-mix: <tok-share>% fleet / <n>×opus / <n>×fable / <n>×cli` (target ≥80 % fleet token-share;
   fleet = haiku + sonnet expected tokens). It is a shared, user-facing artifact → **deliver it for
   operator review before any `git commit`** (pre-commit delivery), like every editing recipe.
6. **Sign.** Mark `status: signed` only when every sign-off box holds (run context complete, all
   tasks rowed, review levels + escalation reasons set, checkpoints enumerated, budget hint
   reviewed, delivered). Signing is the gate before emission.
7. **Emit to the engine** — *only because the user invoked `orchestrate`* (the sanctioned opt-in).
   Translate the signed contract via [`engine-handoff.md`](../references/engine-handoff.md): the
   Workflow tool on Claude Code, the Agents-SDK on Codex, or the **Agent/Task subagent-loop floor**
   when no scripted engine is available. The engine owns the run loop; the contract is policy
   (AP-COORD-7). A `human_checkpoint` or a BLOCKER review verdict **stops forward dispatch** under any
   backing.

## Output contract

A committed, signed `docs/plans/<milestone>-orchestration-contract.md`, delivered for review before
commit; the engine emission (or floor dispatch) is driven from it. Run outcomes flow back to the
project board status (the dashboard renders ①②③ + run status).

## Anti-patterns

- **Building a run engine** (worker pool / run-journal / retry loop) instead of emitting to the
  scripted engine — AP-COORD-7. Own policy, delegate mechanism.
- **Calling the engine autonomously / from a hook / when the user didn't invoke `orchestrate`,** or
  trying to enable `ultracode` (user-only). The engine call is foreground, on invocation, post-sign.
- **Treating the budget hint as a forecast** or feeding it to the engine `budget`. It is coarse and
  non-predictive by design.
- **Re-decomposing the milestone.** The build plan already decomposed it; `orchestrate` runs that
  plan, it does not re-plan.
- **Signing a long-running Codex run without an oracle, artifact surface, or writeback target.**
  That creates an operating loop with nowhere reviewable to land.
- **Emitting an unsigned or undelivered contract,** or batch-collecting BLOCKERs instead of halting on
  the first one (AP-COORD-2).
