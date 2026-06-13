# Multi-Agent Protocols

## Contents

- [Default Rule](#default-rule) — single agent unless complexity justifies coordination
- [Trigger Modes](#trigger-modes) — explicit vs complexity triggers
- [Orchestration Backings](#orchestration-backings) — one prose contract, per-runtime mechanical backings
- [Model Tier](#model-tier) — cheap default for dispatched agents, escalate one-on-signal
- [Mandatory Subagent Dispatch](#mandatory-subagent-dispatch) — when project-meta editing recipes MUST dispatch
- [Roles](#roles) — Lead, Planner, Explorer, Worker, Reviewer
- [Context Mapping Phase](#context-mapping-phase) — optional pre-decomposition Explorer fan-out for the context-mapping read-pattern
- [Context Package](#context-package) — fields every delegation must include
- [Delegation Template](#delegation-template) — copyable shape
- [Ownership Rules](#ownership-rules) — write-set boundaries, ordering barriers
- [Fleet Delivery Workflow](#fleet-delivery-workflow) — worktree fan-out → Lead review → optional re-review → auto-merge on green gates
- [Review Mechanism](#review-mechanism) — consistency, drift, routing, enforcement passes
- [Reviewer-Between-Subtasks Protocol](#reviewer-between-subtasks-protocol) — the enforcement loop
- [Synchronous Gates Under Orchestration](#synchronous-gates-under-orchestration) — hard STOP-and-return boundaries
- [Mechanical Enforcement](#mechanical-enforcement) — the hooks+CLI backing for the dispatch gate and audit ledger
- [Integration Checklist](#integration-checklist) — final reconciliation before commit
- [Failure Signals](#failure-signals) — when the protocol itself needs improvement

Use this reference when complex project-harness work benefits from explicit planning, delegated execution, and independent review.

## Default Rule

Use a single agent unless the task has enough complexity, uncertainty, or independent workstreams to justify coordination overhead.

## Trigger Modes

Use this protocol when either trigger applies:

- Explicit trigger: the user asks for multi-agent work, planning/execution separation, delegated workers, independent review, parallel agents, or a lead agent coordinating sub-agents.
- Complexity trigger: the lead agent judges that the task is complex enough to benefit from planning, bounded execution, and review.

For the complexity trigger, use the protocol when at least two signals apply, or when one strong signal clearly creates meaningful coordination or review risk:

- the task spans multiple independent files, tools, packages, domains, or repositories
- the work needs both exploration and implementation
- the work has independent subtasks that can proceed in parallel
- the work has meaningful risk from conflicting edits, stale guidance, or cross-file drift
- the task needs an explicit review pass before integration
- the requested outcome is ambiguous enough that planning artifacts would reduce rework

When this protocol is triggered, the lead agent should state the trigger reason before delegating work.

For complex work, separate planning from execution:

1. The lead agent plans, decomposes, and sets context.
2. Worker agents execute bounded subtasks with explicit ownership.
3. Reviewer agents check the resulting artifacts against stated criteria.
4. The lead agent integrates results and owns the final answer.

## Orchestration Backings

**This protocol is a runtime-agnostic contract, not a runtime feature.** The prose loop below (Roles, Context Package, Reviewer-Between-Subtasks) is the single source of truth. It has *mechanical backings* — one per declared compat runtime — that must be **behaviorally equivalent** to the prose, never a replacement for it. This mirrors `execution-policy.md` "Relationship To Runtime Enforcement": markdown rules are advisory; real enforcement is per-runtime; **all declared runtimes' backings must agree**.

| Tier | Claude Code | Codex | Any runtime (floor) |
|---|---|---|---|
| Model-driven dispatch | Agent tool / subagents / Agent Teams | native subagents — `.codex/agents/*.toml` role configs (native roles `default`/`worker`/`explorer`; concurrency/depth globals exist but exact TOML keys are Codex-version-dependent — verify against your CLI), opt-in | the prose per-subtask loop |
| Deterministic scripted orchestration | **Workflow** tool (`pipeline`/`parallel`/barrier/`resumeFromRunId`/`budget`) | **Agents SDK + `codex mcp`** (handoffs/gating/traces) | the prose per-subtask loop |

Rules for backings:

- **The prose loop is the floor.** On any runtime lacking a scripted engine, execute the prose loop directly. A backing may accelerate it; none may delete or thin it.
- **One contract, two backings.** A MUST-rule in this protocol that is mechanized on one runtime (e.g. a Claude Code Workflow) but has no backing on another declared compat runtime (Codex) **and** no prose fallback is an `AP-VAL-1`/`AP-SKL-4` gap — see `anti-patterns.md`. Provide the Codex backing (an Agents-SDK script and/or `.codex/agents/*.toml` role configs, generated by `scripts/render_host_manifests.py --hosts codex-subagents`) or keep the prose path.
- **Roles map across runtimes.** This protocol's Explorer (read-only) is Codex's native `explorer`; Worker is `worker`; Reviewer is a *derived* custom agent on a `default` base (Codex has no native reviewer role). The generated `.codex/agents/*.toml` seeds *declare* each role's intended capability (e.g. explorer/reviewer non-editing, only worker writes) — but, like all markdown/prose rules, the declaration alone is advisory. Actual non-editing enforcement comes from the runtime's sandbox/approval config (Codex sandbox modes; Claude Code permissions/hooks), per `execution-policy.md` "Relationship To Runtime Enforcement" — not from the seed text. Treat the seed as the policy; the runtime config does the blocking.
- **Genuinely runtime-specific** (do not assume parity): `resumeFromRunId` journaling/cache-replay, `budget`-scaled loops, and git-worktree peer isolation are Claude Code Workflow specifics; `.codex/commands/` custom slash-commands are not yet available on Codex (as of early 2026, Codex CLI ~0.115 — re-verify, this is a point-in-time negative claim), so a "saved deliver-workflow as a `/`-command" has no Codex equivalent — invoke the Codex backing via an Agents-SDK script or a subagent prompt instead.

## Model Tier

A dispatched agent is **not** the Lead. The Lead owns framing, synthesis, and the final answer (Roles); a spawned Worker / Reviewer / Explorer / scout runs a *bounded, context-isolated* subtask. Size the model to that bound, not to the importance of the parent task.

Three tiers govern a pipeline run:

| tier | Claude Code model (2026) | Codex model tier (2026) | role |
|---|---|---|---|
| **fleet** (default) | Sonnet 4.6 | GPT-5.4 | every dispatched bounded role: Workers, Reviewers, Explorers, scouts, finders, verifiers, extract/summarize/lint-adjacent judgment |
| **escalation/synth** | Opus 4.8 | GPT-5.5 | (a) the single escalate-on-demonstrated-shortfall agent; (b) cross-agent synthesis where one context reconciles many fleet outputs; (c) adversarial/security review where a miss is expensive |
| **conductor** | the **active session model** (Fable 5 when available) | the **active session model** (GPT-5.5 when available) | Lead/session only: framing, contract signing, architecture forks, final canon gate; plus at most **one** dispatched "unblock" call after an Opus/GPT-5.5 escalation already failed |

Rules:

- **Default every dispatched agent to the fleet tier (Sonnet / GPT-5.4).** This is the floor for all spawned roles on both the model-driven and scripted backings (`agent(prompt, {model: 'sonnet'})` in a Workflow; GPT-5.4 role seeds or equivalent Codex agent config).
- **Escalate a *single* agent to the escalation tier (Opus / GPT-5.5) only on a demonstrated fleet shortfall** — it already failed, or returned low-quality output at fleet — **never precautionarily.** Opus/GPT-5.5 is never a fan-out tier; at most twice per pipeline run (one escalation slot + one synthesis slot).
- **Fable / GPT-5.5 conductor is never dispatched in fan-out.** It is the session conductor. Any non-zero dispatched conductor-tier count must be individually justified (at most one unblock call after the escalation tier already failed). Conductor = Fable/GPT-5.5 is a *target*, not a guarantee: on a Sonnet/GPT-5.4 session the conductor is Sonnet/GPT-5.4 — the contract must say so.
- **The fleet panel (opt-in, L2).** N diverse-lens Sonnet/GPT-5.4 reviewers with a majority verdict is the *same mechanism* as `review-tier.md` L2 (3–4× fleet + opt Opus/GPT-5.5 synth) — not a new mandatory rung. Choose it at contract time for high-volume bounded judgments where a single reviewer's failure signal is ambiguous. Cost claim, stated honestly: a panel is cheaper than an Opus/GPT-5.5 retry **only when** panel output tokens ≪ retry output tokens (typical for bounded verdicts); same-model panels do not decorrelate systematic failure modes — diversity comes from lens prompts. A capability-ceiling failure (e.g. a missed subtle security bug) skips the panel and escalates directly. Never chain panel-then-escalate-the-panel: cap the combined path at one escalation.
- **Tier-mix target:** ≥80 % of *estimated output tokens* (from `budget_hint.py` totals at signing) on the fleet tier — token-share, not agent-count. Each Opus/GPT-5.5 slot is justified individually in the contract's review section. Promotion records via `dispatch_ledger.py record --tier --verdict`.

Why: precautionary top-tier dispatch is the cost-side sibling of AP-COORD-4 (over-orchestration) — paying for capability a bounded subtask does not need, multiplied across a fan-out. The escalate-on-signal direction is symmetric: keeping a genuinely hard subtask on fleet *after* it already produced bad output wastes the round-trip. Both are mis-sizing; the default is cheap, the correction is per-agent and evidence-gated.

Runtime mapping: Codex mirrors Claude's three-tier structure directly: GPT-5.4 corresponds to Sonnet/fleet, while GPT-5.5 corresponds to both Opus/escalation and Fable/conductor. The *rule* — fleet default, escalate-one-on-signal, conductor outside fan-out — is runtime-agnostic; only the concrete model names differ. Downstream skills cite this section rather than restating the rule.

### Tier is two axes (model × effort)

A tier is not just the model — it is the pair **(model level, thinking effort)**:

- **Model level** — Sonnet/GPT-5.4 fleet (default) → Opus/GPT-5.5 escalation → Fable/GPT-5.5 conductor; a trivial extraction may sit at CLI (no model).
- **Thinking effort** — low → medium → high → max, the reasoning-depth dial on a *given* model.

The default dispatched tier is the *cheapest viable point* — fleet at low–medium effort, **not** fleet at max. Promotion (below) climbs this two-axis space, and the **cheap lever moves before the expensive one**: raising effort on the same model costs less than a model jump, so try it first unless the failure is clearly a capability ceiling rather than a depth shortfall.

### Retro-inspect promotion (cross-run, per task-type)

The escalate-on-signal rule above is *within-run* and *per-agent*: one agent fails now, you retry that agent higher this run. It does not persist — the next run re-dispatches the same kind of task at the default and re-pays the identical failed first trial. Close the loop with a **retro-inspection keyed by task-type** (the role + the kind of subtask), not by agent instance:

1. **Record the failure as durable harness state.** When a dispatched agent of a given task-type fails or returns low-quality output at its tier, the Lead writes a *promotion record* to **repo memory** (via the Memory Contract — cite [`repo-memory-crud.md#memory-contract`](repo-memory-crud.md#memory-contract), do not restate it): the task-type, the tier attempted `(model, effort)`, the failure signal, and the date. The **dispatch ledger** (`.harness/dispatch-log.jsonl`, `scripts/dispatch_ledger.py`) is the *evidence* — it records `task_type` + `tier` + `verdict` per dispatch so retro-inspect reads structured history, not recalled vibes. **Ledger = transient evidence; repo memory = the durable learned policy** (the same split as "ledger is audit, `AGENTS.md` is canon"). Distilling evidence → durable record is Lead judgement (Roles: the Lead owns write-back), so a fresh agent cannot self-certify a promotion.

2. **Promote on the next dispatch.** Before dispatching a task-type, the Lead consults its promotion record and *starts* at the recorded tier instead of the default — converting a repeated first-trial failure into a one-time cost.

3. **Match the lever to the failure mode** (climb the cheap axis first):
   - *shallow / truncated / ran out of reasoning depth* → bump **effort** (same model);
   - *wrong approach / capability ceiling / effort already at max* → bump **model**.

4. **Still evidence-gated, bounded, and not a one-way ratchet.** A promotion requires a *recorded* failure, never a hunch — the precautionary ban from the within-run rule still holds. Cap at (Opus/GPT-5.5, max). The record carries its *cause* so a later run can demote back toward the default once the cause is gone (the task changed, the fixture got fixed); a tier that only ever climbs is the cost-side AP-COORD-5 mis-sizing — paying for capability the task no longer needs. This is the same `record → predict → adjust` active-learning shape project-meta uses for preferences, specialized to tier selection. Amnesiac re-payment of the same failed first trial every run is **AP-COORD-6**.

## Mandatory Subagent Dispatch

The complexity trigger is judgement-based; the rule below is mechanical.

**MUST dispatch via subagents** (per-file Worker + Reviewer between subtasks) when a `/project-meta` editing recipe (`init`, or any future editing verb — `deliver` is read-only delivery assembly and never edits; see `recipes/deliver.md`) touches **two or more** of:

- `AGENTS.md` (or the canonical equivalent for the active host)
- any `agents/*.md` topical file
- any mirror file (`CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/agents.md`, `.opencode/instructions.md`, `gemini-extension.json`, `.gemini/instructions.md`)
- any template under `templates/`
- any script under `scripts/`
- any hook script under `<target>/.claude/hooks/`

**The trigger is a 3-way tier selector, not a binary:**

1. **Single-file change** → stay in the conductor's context.
2. **Trivial change** (typo fixes, docs-only edits ≤10 lines) → stay single-context with explicit acknowledgement in the delivery summary.
3. **Two-or-more of the file set above** → dispatch.

**Two distinct bars — do not conflate them.** The ≥2-file rule selects *subagent dispatch* (the cheap Task-loop tier: a fresh Worker + Reviewer per file). Escalating to a *scripted orchestration engine* (Claude Code Workflow, Codex Agents-SDK) is a **separate, higher bar**: explicit user opt-in (keyword `workflow` / ultracode / explicit ask, or a recipe that names the tool and its cost surface) **or** a heavy-scope signal beyond raw count. File count alone does not justify the engine — see `execution-policy.md` "Soft Budgets" ("File count alone is not a risk signal") and `anti-patterns.md` AP-COORD-4 (over-orchestration). The 2-file case defaults to cheap subagent dispatch.

**Runtime resolution of the dispatch action:**

- Claude Code: dispatch via the Agent tool; *may* escalate to the editing Workflow (owned by `init` / a future editing verb — never `deliver`, which is read-only) when the higher bar is met.
- Codex: dispatch via native subagents (`worker` edits, `explorer` read-only) or an Agents-SDK script.
- Any runtime lacking both: execute the prose per-subtask loop below. The mechanical guarantee survives on every leg.

**Why mechanical**: AP-COORD-1 (conductor edits + orchestrates simultaneously) and AP-COORD-2 (no review between subtasks) are the dominant failure modes for project-meta editing work. Judgement-based triggers under-fire when the conductor is already engaged. The file-count rule fires deterministically — on every runtime, via that runtime's backing.

**Bypass requires explicit acknowledgement.** When the conductor judges the rule does not apply (e.g. all touched files form one logically atomic change), it MUST state the bypass in the delivery summary, name the AP-COORD-* rule it is bypassing, and justify why. A delivery that silently skips dispatch is itself an AP-COORD-1 violation.

The recipe owns *when* to dispatch; this reference owns *how* (Roles, Context Package, Reviewer-Between-Subtasks Protocol below).

## Roles

- Lead: owns task framing, decomposition, context packages, ownership boundaries, review criteria, integration, and final memory writeback.
- Planner: explores the problem space and produces the task breakdown. In small teams, the lead agent may also be the planner.
- Explorer: answers narrow read-only questions and does not edit files.
- Worker: edits an explicitly assigned file set or produces a bounded artifact.
- Reviewer: checks consistency, drift, duplicate guidance, missing validation, and whether the output matches the protocol.

## Context Mapping Phase

**Optional, and only for the `context-mapping` read-pattern** (derived in [`execution-policy.md`](execution-policy.md) "Read-Pattern Derivation"; the default `minimal` skips this phase entirely). When a task needs a coherent global model *before* decomposition — complex design, cross-subsystem work, an investigative `audit` — run a read-only Explorer fan-out to build that model before planning, not during execution.

Four constraints make this a net win instead of a drift source:

1. **Explorers return pointers, not opaque conclusions.** Each Explorer digest carries `file:line` anchors + key excerpts + its judgement, so the Lead can re-expand any claim on demand. Treat it as lossy compression *with a decompression key*, never "I read it for you". A digest of bare conclusions is unauditable and propagates silent loss the Lead cannot detect.
2. **The map feeds the Lead/Planner, not the Workers.** The digest informs decomposition and design. Workers still read minimal and just-in-time per their Context Package "Read first" — they do NOT inherit the shared map. Inheriting it reintroduces exactly the cross-file drift the minimal discipline exists to prevent.
3. **Mapping never replaces per-worker minimal reads.** The phase accelerates *the Lead's* understanding; it adds nothing to the worker tier. If the map tempts you to let a worker skip its own narrow read, that is the failure, not the shortcut.
4. **Write-back judgement stays with the Lead.** Distilling durable vs transient needs the whole session's accumulated judgement (Roles: Lead owns "final memory writeback"). A fresh agent cannot do this without being re-fed the very context it is meant to compress — self-defeating. Only the *mechanical* half of write-back (mirror render, formatting, validation) is delegable, and only after the canonical→barrier→mirror barrier (Ownership Rules).

Running this phase for a `minimal`-class task, or collapsing a `context-mapping`-class task into bare minimal worker reads, is AP-COORD-5 — the read-volume sibling of AP-COORD-4 (over-orchestration), in either direction.

## Context Package

Every delegated task must include:

- Goal: the exact question or artifact the agent must produce.
- Read first: the smallest file list needed for the task.
- Ownership: read-only status or the exact files the agent may edit.
- Constraints: relevant rules from `AGENTS.md`, `SKILL.md`, and loaded references.
- Output format: findings, patch summary, review notes, or structured decision.
- Review criteria: what must be true for the subtask to pass.
- Memory policy: whether the agent may suggest memory updates, edit canonical memory, or only report durable lessons.

The capsule (`goal`, `constraints`, `decisions`, `out_of_scope`) is the mechanically recordable subset of this package. Record it via `dispatch_ledger.py record --schema-version 2 --capsule-goal … --capsule-constraints … --capsule-decisions … --capsule-out-of-scope …` (or `--capsule <JSON>`). This makes the context handed to each worker auditable alongside the verdict and touch-set in `.harness/dispatch-log.jsonl`. See [Mechanical Enforcement](#mechanical-enforcement) for the full v2 schema.

## Delegation Template

```text
Role: <Explorer | Worker | Reviewer>
Goal: <exact question or artifact>
Read first:
- <path>
- <path>
Ownership: <read-only | may edit exact files>
Constraints:
- <relevant AGENTS.md, SKILL.md, or reference rule>
Output format: <findings | patch summary | review notes | decision>
Review criteria:
- <pass/fail condition>
Memory policy: <may suggest updates | may edit canonical memory | report only>
```

## Ownership Rules

- Do not assign overlapping write sets unless the lead agent explicitly owns reconciliation.
- Keep `SKILL.md` as the entrypoint; move detailed protocol guidance into `references/`.
- Treat canonical memory as the source of truth and mirrors as secondary.
- Do not let workers update mirrors before canonical memory changes are integrated.
- Do not write speculative, transient, or session-only notes into repo memory.

### Ordering barriers (mandatory for any automated backing)

Parallelism is safe only across **disjoint write-sets**. Some write-sets have a data dependency that a naive `parallel()`/`pipeline()` over a flat file list would violate — so the barrier must be structural, not prose:

- **Canonical → barrier → mirror.** Mirror files (`CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/agents.md`, etc.) are *generated from integrated canonical state* (`scripts/render_host_manifests.py`). A mirror render MUST NOT run in the same unbarriered stage as canonical edits. Phase it: (1) canonical edits, each with a per-file review gate → (2) barrier + integrate canonical → (3) mirror render. Worktree isolation makes this **worse**, not better: an isolated worker renders mirrors from stale pre-integration canonical with no merge conflict to signal the violation.
- **Disjoint canonical edits** within phase 1 may run in parallel only if their write-sets do not overlap.

## Fleet Delivery Workflow

The default end-to-end shape for executing **≥2 file/section-disjoint slices** (validated 2026-06: ≈2–2.5× cheaper and 1.9–3.6× faster than single-context serial work, with net accuracy at least equal — the safety comes from the three layers below, not from any single agent):

1. **Fan out** — one fleet-tier agent per slice, **worktree-isolated**, each committing to a named branch. Briefs are self-contained: a spec *pointer* by absolute path (untracked files are invisible inside worktrees — point, don't paraphrase), scoped-edit constraints that name what sibling branches touch ("edit only section X of this file"), the validator commands to run, and **no version bumps on branches** (bumps on N branches guarantee an N-way manifest conflict; bump once at merge).
2. **Lead review** — the Lead reads every diff, reruns validators/lint/smoke, and prechecks merges pairwise with `git merge-tree --write-tree` before anything lands.
3. **Optional fresh re-review** — dispatch a clean-context reviewer (review-tier L1/L2) for canon, MUST-rule, or security surfaces; skip for mechanical slices.
4. **Auto-merge on green gates** — squash-merge (matching linear history) without further approval only when *all* hold: per-branch validators pass, every pairwise merge-tree is CLEAN, and the post-merge validation rerun is green. Any red gate returns that slice to its worker instead of merging.

Below the threshold — a single slice, tightly coupled edits, or under ~10 minutes of work — stay single-context (AP-COORD-4): the worktree/brief/report overhead exceeds the parallel gain. The ordering barriers above still bind: canonical→mirror dependencies never fan out in one unbarriered stage.

## Review Mechanism

For complex changes, run at least one of these review passes before final integration:

- Consistency review: checks that `README.md`, `SKILL.md`, `agents/openai.yaml`, and relevant `references/*.md` agree.
- Drift review: checks stale, duplicated, or contradictory guidance.
- Routing review: checks that the entrypoint points to the right reference without becoming a manual.
- Enforcement review: identifies rules that should become a script, checklist, template, or recurring cleanup routine.

## Reviewer-Between-Subtasks Protocol

Once mandatory dispatch is triggered (or when the lead agent invokes it for judgement reasons), the per-subtask loop is:

1. **Brief**: lead packages a context package per the Delegation Template above. Brief contains only what the worker needs — typically ≤1 page including the diff target, the rule motivating the change, the success criterion, and ≤3 surrounding-context references.

2. **Worker dispatch**: fresh subagent. Worker edits the assigned file, produces a patch summary, and reports back. Worker does NOT see the lead conductor's broader context; this is the AP-COORD-1 fix.

3. **Reviewer dispatch**: fresh subagent, separate from worker. Reviewer receives:
   - the original brief
   - the worker's diff
   - the success criterion
   Reviewer reports verdict: **PASS** / **BLOCKER** / **SUGGEST**.
   - PASS: lead proceeds to the next subtask.
   - BLOCKER: lead halts the chain, surfaces the blocker to the user. No further dispatch until the user decides (re-brief worker / re-scope / abort). **This is a synchronous, run-terminating gate under *any* backing.** A background/batched runner (Claude Code Workflow, Codex Agents-SDK) MUST stop forward dispatch on the first BLOCKER and return — batch-collecting BLOCKERs to surface at end-of-run is NOT an acceptable substitute, because it reopens the exact AP-COORD-2 "flaw in subtask N discovered at N+5" window the gate exists to close. `resumeFromRunId` (or a Codex re-entry) is the mechanism to *resume after the user decides*, never a license to run past the blocker.
   - SUGGEST: lead may incorporate, queue for follow-up, or accept-as-is depending on the suggestion's weight; either way, the suggestion is logged in the delivery.

4. **Logging**: every dispatch records (worker subagent id, reviewer subagent id, brief hash, verdict, comment) so the chain is auditable. The delivery summary includes the chain.

5. **Reviewer rotation**: do not reuse the same reviewer subagent for consecutive subtasks. A reviewer that has been part of one subtask's context will pattern-match against it; rotation keeps reviewers naïve to prior work, which is the point.

6. **Lead never edits**. Once dispatch triggers, the lead's role is brief / review verdicts / integration. Lead writing files inside a dispatched chain is AP-COORD-1.

## Synchronous Gates Under Orchestration

A scripted backing runs to completion in the background; it cannot pause mid-run for input. Four boundaries are therefore **hard STOP-and-return** points: the runner must terminate forward progress and hand back to a human, never run past them. Encode each as a structural gate, not an aggregated end-of-run annotation.

| Gate | Trigger | Rule | AP |
|---|---|---|---|
| **BLOCKER verdict** | a reviewer returns BLOCKER | stop dispatch, return, await user decision; resume is re-entry only | AP-COORD-2 |
| **Read-only write attempt** | a write is proposed under a read-only verb (`status`/`validate`/`deliver`/`audit`) | a read-only verb's runner MUST contain **zero edit-capable stages by construction** | (execution-policy MUST-STOP) |
| **Pre-commit commit** | a commit would be created | the runner assembles the pre-commit delivery and STOPS; `git commit` is never inside the runner; the commit boundary is the user's | (execution-policy SHOULD-ASK) |
| **Init questionnaire** | first-time `init` needs preset/checklist selection | the questionnaire is a synchronous human gate that MUST precede or hard-stop any editing run; a background init that defaults the preset is forbidden | AP-LIFE-1 |

`resumeFromRunId` (Claude Code) or a Codex re-entry is the mechanism for continuing *after* the user resolves a gate — it is never a way to defer past one.

## Mechanical Enforcement

The dispatch *engine* is the Workflow tool / Codex Agents-SDK / the prose loop (Orchestration Backings). But two halves of this protocol are deterministic and are mechanically backed by **hooks + a CLI** — an enforcement/audit layer, not a second engine. This is the Claude Code backing; Codex enforces the same via sandbox/approval config + Agents-SDK gating (per "Relationship To Runtime Enforcement"). The CLI (`scripts/dispatch_ledger.py`) is portable and resolved, not vendored (`shared-cli-delegation.md`).

**Audit ledger** (the "Logging" requirement, line ~191). Each dispatch is recorded to `.harness/dispatch-log.jsonl`:

```bash
# v1 (all fields)
dispatch_ledger.py record --worker <id> --reviewer <id> --role worker \
  --verdict PASS --brief-hash <h> --comment "<what>"

# v2 (adds capsule, touch-set, budget, checkpoint; --schema-version 2 required)
dispatch_ledger.py record --worker <id> --role worker --verdict PASS \
  --touch-set "a.py,b.py" \
  --capsule-goal "implement X" --capsule-constraints "stdlib only" \
  --capsule-decisions "used approach Y" --capsule-out-of-scope "Z" \
  --budget-tokens 10000 --spent-tokens 8000 \
  --checkpoint '{"completed":["step1"],"touched_files":["a.py"],"open_decisions":[]}' \
  --schema-version 2
# Alternatively, pass the full capsule as one --capsule '{"goal":…}' JSON arg.

dispatch_ledger.py validate    # schema + verdict-domain check;
                               # v2 rows: capsule/checkpoint completeness + budget advisory
dispatch_ledger.py query       # chain summary, BLOCKER count

# Atomic task claim — refuses a second claim on the same task id (exit 1)
dispatch_ledger.py claim --task DASH-046 --worker w1   # exit 0 first time
dispatch_ledger.py claim --task DASH-046 --worker w2   # exit 1 "duplicate claim"

# Pairwise touch-set overlap report — exit 1 + report if any overlap exists
dispatch_ledger.py overlap     # exit 0 when all touch-sets are disjoint
```

**v2 schema fields** (enforced by `validate` only for rows with `schema_version >= 2`; v1 rows keep the `worker`/`role`/`verdict` floor):

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | `2` for v2 rows; absent on v1 rows |
| `touch_set` | list[str] | files this dispatch record touches; used by `overlap` |
| `capsule` | object | context package: `goal`, `constraints`, `decisions`, `out_of_scope` (all required for v2) |
| `budget_tokens` | int | optional token budget |
| `spent_tokens` | int | optional tokens actually spent; `validate` reports exceedance as advisory (exit 0) |
| `checkpoint` | object | `completed`, `touched_files`, `open_decisions` (all required for v2) |

The capsule is the mechanical form of the [Context Package](#context-package) — it records the package that was handed to the worker and is now auditable via the ledger. See "Context Package" below for the prose definition of each field.

**Mandatory-dispatch gate** (the file-count rule). The `Stop` hook runs `dispatch_ledger.py gate`: if the turn left **≥2 harness files** changed in the working tree (the Mandatory Subagent Dispatch file set) with no `.harness/dispatch-ack` marker, it flags the AP-COORD-1 pattern. Profile-gated (`minimal` off, `standard` warns, `strict` blocks). The ack is **one-shot** (consumed when honored) — so it cannot silently disable the gate — and is the mechanical form of the "Bypass requires explicit acknowledgement" rule. **This is a post-hoc detector/deterrent, not structural isolation**: it catches the violation at turn-end but cannot un-edit the files. Structural prevention (a conductor that *cannot* edit while orchestrating) still requires the engine (separate Worker agents) — the gate is the floor for runtimes/turns that skip the engine.

**Partially shipped — the [Synchronous Gates](#synchronous-gates-under-orchestration) as `PreToolUse` hooks:**

The destructive-command guard is **now shipped** (v0.6, DASH-051): `PreToolUse(Bash)` blocks a closed list of destructive shell patterns (`rm -rf /`, `git reset --hard`, `DROP TABLE`, etc.) with a profile ladder (`minimal` off / `standard` warn / `strict` block, exit 2). The following two gates remain **designed but not yet shipped**:

- *Read-only-verb write* → `PreToolUse(Edit|Write)` blocking edits under a read-only verb.
- *Pre-commit* → `PreToolUse(Bash)` blocking `git commit` inside a runner.

Both of the unshipped gates require turn/verb **state** a recipe must set (e.g. `.harness/current-verb`, `.harness/runner-active`). Until that plumbing exists, shipping these as hooks would make them silent-pass = AP-VAL-1 dead code. They are specced here as the next enforcement step, not shipped inert.

## Integration Checklist

Before finalizing multi-agent work:

1. Reconcile duplicate or conflicting recommendations.
2. Verify links, paths, and file ownership assumptions.
3. Check that workers did not exceed their write scope.
4. Keep durable lessons in canonical memory, not in mirrors first.
5. Sync mirrors only when canonical structure or high-priority guidance changed.
6. Run available diff, formatting, or validation checks.
7. Record any recurring coordination failure as a protocol improvement.

## Failure Signals

Improve the protocol when agents:

- ask each other vague questions instead of producing artifacts
- claim work was done without verifiable file changes or evidence
- edit outside their ownership boundary
- duplicate guidance across canonical files and mirrors
- skip review criteria or leave the lead agent to infer pass/fail state
