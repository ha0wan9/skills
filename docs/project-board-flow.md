---
artifact_name: project-board-flow
kind: usage-guide
project_scope: hw-skills — Project Board System
owner: user-reviewed
status: current
source_reference: docs/backlog/project-board-system.md
last_reviewed: 2026-06-06
---

# Project Board Flow — Usage & Evolution Guide

The Project Board System is a CLI-managed, repo-canonical project surface that moves work from fuzzy capture through a versioned roadmap, into a falsifiable build plan, and finally into a negotiated orchestration contract that an engine executes — with a static `dashboard.html` as the living user-facing artifact at every stage.

---

## Architecture recap

Four cross-cutting planes govern every stage; the value spine crosses three skill boundaries.

```
  CROSS-CUTTING PLANES (apply to every stage below)
   · Review-tier   L0..L3          → review-tier SKILL (DASH-19–21; shared dep)
   · Exec-tier     CLI | Sonnet | Opus   (DASH-15: conductor delegates by cost)
   · Budget-hint   coarse, non-predictive    (DASH-22; orchestration skill)
   · Source-of-truth  store=canonical → dashboard=derived → Linear=mirror

  VALUE SPINE

   any session
      └─ autonomous capture (headless-Sonnet hook · DASH-02 · atomic append) ─┐
                                                                             ▼
   ① BACKLOG / ISSUES   append-only inbox · docs/backlog/          [project-meta]
       maturity: fuzzy ──refine(DASH-23)──► refined
                     │ joint co-review TX (DASH-08 · L2)
                     ▼
   ② ROADMAP   versioned milestones                                [project-meta]
                     │ pick milestone
                     ▼
   ③ PLAN   falsifiable build-plan = task × acceptance  (SHIPPED)  [project-meta]
   ─────────────────skill boundary────────────────────────────────────────────
                     ▼
   ④ ORCHESTRATE   contract: tier·parallel·effort·human·review·budget-hint
                             (signed ahead)                    [orchestration SKILL]
   ════════════════engine boundary (AP-COORD-7: contract=policy / engine=mechanism)
                     ▼
      /workflows · Codex Agents-SDK · Agent/Task loop (floor)
                     ▼ run outcomes feed back to ①

   DASHBOARD   static dashboard.html   derived view over ①②③④    [project-meta]
```

**Skill split (locked):**
- `project-meta` — Backlog, Roadmap, Dashboard, cross-cutting (A/B/D/E streams)
- `orchestration` skill — the contract + engine handoff (C stream, DASH-09/10/11/22)
- `review-tier` skill — L0–L3 levels, shared dependency (F stream, DASH-19–21)

---

## Stage 1 — Backlog reading & refinement

*Moving items from `fuzzy` → `refined` so they become roadmap-eligible.*

| | |
|---|---|
| **Operator does** | Invokes `/project-meta` with a refinement intent, or reviews captured items in `docs/backlog/`. Answers the agent's clarifying questions on scope, acceptance shape, and rough size. Confirms or rejects the promotion. |
| **Agent does** | A **Sonnet sub-agent** drafts the concrete requirement for each fuzzy item: scope + acceptance-shape + rough size. It reads `.refine-guidance.md` (distilled lessons from prior co-reviews — not `repo_memory`) to sharpen the draft. It **asks the operator** wherever ambiguous before promoting. |
| **Execution tier** | Judgment work → **Sonnet sub-agent**. Deterministic CRUD (add/move/edit) → **CLI** (`scripts/board.py`). No engine call. |
| **Artifact produced** | The backlog item's `maturity` field advances from `fuzzy` → `refined` in the JSONL store. |
| **DASH entries** | DASH-01 (store format + maturity ladder), DASH-02 (autonomous capture via headless Sonnet), DASH-23 (refinement sub-agent + promotion gate), DASH-24 (async-capture / deliberate-promote contract) |

**Key mechanics:**
- Capture is **append-only and multi-instance-safe** (atomic `O_APPEND` single-line JSONL). Dedup is never done at capture time — that is a write-mutation and belongs at the single-writer gate (Stage 2).
- A `Stop`/`SessionEnd` command hook runs a cheap shell pre-filter → headless Sonnet agent → atomic append. This flow **never calls a Workflow engine** — it uses a `claude -p --model sonnet` subprocess (the AP-VAL-1 floor for autonomous capture).
- Only `refined` items are roadmap-eligible. `fuzzy` items cannot be scheduled.
- Optional L1 review (is this well-formed/testable?) can run on promoted items before Stage 2.

---

## Stage 2 — Backlog ↔ roadmap docking

*One joint co-review transaction that reads both surfaces and writes both back atomically.*

| | |
|---|---|
| **Operator does** | Opens a `/project-meta roadmap` session (collaborative, proposed). Reviews the joint snapshot — backlog `refined` pool + roadmap draft. Makes version-assignment decisions, trims stale items, deduplicates duplicate captures, and resolves any co-review findings before the transaction closes. |
| **Agent does** | Reads both the backlog snapshot and the roadmap draft simultaneously. Proposes version assignments for `refined` items; flags over-heavy milestones for deferral; identifies off-direction items for trimming; spawns new backlog items when a new milestone goal implies missing work. Resolves capture-time dedup (the single-writer gate). Emits refinement-guidance feedback to `.refine-guidance.md` for Stage 1. |
| **Execution tier** | Interactive, collaborative session → **Opus / main session** (DASH-05). The L2 review panel → **3–4 parallel Sonnet reviewers** with distinct lenses (feasibility · robustness · usefulness · usability) synthesized, per the review-tier skill. |
| **Artifact produced** | Updated backlog store (items now carry `maturity: scheduled` at `@vX`) + updated roadmap (versioned milestones with assigned items). Both written atomically — a `refined` item is in one version XOR still in the pool, never both. Guidance feedback written to `.refine-guidance.md`. |
| **DASH entries** | DASH-05 (roadmap mode), DASH-06 (version-milestone model), DASH-08 (joint co-review + L2, absorbs DASH-07), DASH-24 (async coupling / single-writer dedup gate), DASH-19–21 (review-tier skill: L2 instance) |

**Key mechanics:**
- This is the **only** place where capture-time dedup is resolved — the single-writer gate.
- Decisions flow **both ways**: refined pool → milestone, and overloaded milestone → back to pool or trim.
- Reviewed at **L2** (multi-expert panel, review-tier skill): roadmap lenses + backlog lenses run in parallel for speed (AP-COORD-4 respected — L2 is substantive design work, not overkill here).
- The `roadmap` verb starts as a Reserved-Command and is promoted on demonstrated demand (DASH-17).

---

## Stage 3 — Roadmap → plan task-splitting

*Pick a milestone, produce a falsifiable build-plan artifact. This stage is **shipped**.*

| | |
|---|---|
| **Operator does** | Invokes `/project-meta plan` (optionally with `goal`, `autopilot`, or `unattended` keyword to escalate readiness to `strict`). Names the target milestone (e.g. v0.2). Reviews the produced build-plan and runs `/project-meta audit` to get a GO / NO-GO verdict before signing off. |
| **Agent does** | Instantiates `templates/building-plan.md` at `docs/plans/<goal>-build-plan.md`. Fills the §6 per-item verification matrix (mandatory at both tiers): test target (exact command) + data (real fixture path or mock) + threshold (objective, self-checkable). Under `strict`, also completes §1 non-goals fence, §3 tiers, §4 committed fixtures, §7 checkpoints. Registers the artifact in `agents/project-artifacts.md`. Does **not** self-certify readiness. |
| **Execution tier** | Plan production → **main session / Opus** (primary). The `audit` readiness gate (Goal-readiness dimension) → **Sonnet reviewer** on clean context (diff + brief). Deterministic checks (validate_target_harness, gate command) → **CLI**. |
| **Artifact produced** | `docs/plans/<goal>-build-plan.md` with provenance frontmatter + `readiness` field + §6 verification matrix. Manifest entry in `agents/project-artifacts.md`. `audit`'s Goal-readiness dimension emits GO / NO-GO + the four requirement-gap categories (no numeric score). |
| **DASH entries** | DASH-09 (orchestrate reuses the shipped plan), plus `recipes/plan.md` + `templates/building-plan.md` + `recipes/audit.md` (all shipped) |

**Key mechanics:**
- The §6 matrix is mandatory at the `floor` tier — forgetting the `goal`/`autopilot` keyword never drops the plan below falsifiable (AP-SKL-2, AP-PLAN-1).
- `plan` writes; `audit` judges. Never self-certify.
- `strict` plans get `audit`'s GO / NO-GO gate before they are considered run-ready. NO-GO until every §6 row is verifiable.
- Delivery before commit: the plan is a shared-user-facing artifact, shown before any `git commit`.

---

## Stage 4 — Orchestrate → negotiate → execute

*Build the orchestration contract, operator negotiates it, engine runs it. Proposed (not yet built).*

| | |
|---|---|
| **Operator does** | Invokes the **`orchestration` skill** (separate from `project-meta`) with the signed build-plan as input. Reviews the drafted contract: per-task model tier (Opus vs Sonnet), parallelization, effort level, human-in-loop checkpoint positions, review level (L0–L3 from the review-tier skill), and the budget hint (coarse ranges). **Negotiates** — adjusts tiers, checkpoint placement, or parallelism before signing. Signs by explicit confirmation. |
| **Agent does** | Decomposes the build-plan into an orchestration contract (per-task schema). Assigns each task a model tier (Sonnet default; Opus for hard/milestone tasks per DASH-15 conductor/worker doctrine), parallelization flag, orchestrator effort, human-in-loop checkpoints, review level, and a budget hint (DASH-22). Presents the full contract for operator review before emitting. |
| **Execution tier (contract production)** | Contract authoring → **Opus / main** (DASH-09). Budget hint computation → **CLI** (`scripts/context_cost_estimate.py` style: model-tier × fan-out × per-class token band, labeled "estimate, not a guarantee"). |
| **Execution tier (after signing)** | Signed contract → emitted to **Claude Code Workflow** or **Codex Agents-SDK** when the operator's invocation of the orchestration skill names the tool (the sanctioned opt-in per DASH-11). Degrades to **Agent/Task subagent dispatch loop** when no scripted engine is available (AP-VAL-1 floor — always available). |
| **Artifact produced** | The orchestration contract (committed, reviewable artifact) per DASH-10. On execution: run outcomes feed back to the backlog (Stage 1) as new items or status updates. |
| **DASH entries** | DASH-09 (orchestrate mode), DASH-10 (contract artifact), DASH-11 (contract → engine handoff), DASH-22 (budget hint), DASH-19–21 (review-tier: contract references levels) |

**Key mechanics — workflow opt-in posture (do not get this wrong):**

The only legitimate `/workflows` caller is the **orchestration skill when user-invoked**, because its instructions name the tool and its cost surface — the two-bar rule's sanctioned opt-in. Everything else is prohibited:
- A skill **cannot enable `ultracode` session-mode** (user-only setting).
- A skill **cannot call Workflow autonomously, from a hook, or when the user didn't invoke orchestrate**.
- The Stage 1 capture hook (DASH-02) **never calls Workflow** — it uses a headless subprocess.
- **Default everywhere:** Agent/Task subagent dispatch (always available). `/workflows` is opt-in escalation only, not the default path.

**Budget hint (DASH-22) is non-predictive.** It is a coarse expectation-setter (wide low/expected/high ranges, labeled "estimate, not a guarantee") computed from model-tier × fan-out × heuristic token bands. It does not drive the engine's `budget` parameter. It does not calibrate against actuals until a cost corpus exists (prereq: add token/runtime fields to `dispatch_ledger.py`). Its purpose is to let the operator eyeball "this contract is Opus-heavy or unusually wide" and adjust before signing.

**Conductor/worker tiering (DASH-15):** inside an executing contract, the main session is the conductor; deterministic side-work routes to CLI (no model); judgment side-work to Sonnet sub-agents; hard or milestone tasks to Opus per the contract. AP-COORD-7: the contract owns policy; the engine owns mechanism — the orchestration skill does not hand-roll its own run-loop.

---

## Review tiers (cross-cutting)

All four stages draw from the **review-tier skill** (DASH-19–21; proposed). Right-sized review sits between AP-COORD-2 (must review) and AP-COORD-4 (don't over-orchestrate).

| Level | Used in this flow | Cost |
|---|---|---|
| **L0 self-check** | Trivial backlog edits, tiny CLI mutations | ~free |
| **L1 single reviewer** | Ordinary `refined` promotion (optional), small plan items | 1× Sonnet |
| **L2 multi-expert panel** | Stage 2 co-review (DASH-08), plan `audit` under `strict`, design-scope roadmap | 3–4× Sonnet (+opt Opus synth) |
| **L3 adversarial + pressure** | New skill ships, MUST-rule changes, irreversible decisions | Most expensive; reserved |

The `review_tier.py` scorer is a **heuristic pre-filter**, not a deterministic classifier. It keys off mechanical signals (diff size, file count, harness-path match) to suggest a floor. Judgment inputs (blast radius, reversibility) are not computable from a diff — the conductor escalates, never silently de-escalates for high stakes.

---

## How it evolves

### Versioned milestones drive iteration

The roadmap itself is the mechanism: each v0.x milestone is a concrete set of DASH entries, assigned in Stage 2 grooming, tracked in the dashboard. Feedback from a completed milestone (forecast vs actuals, trim reasons, refinement patterns) feeds back to Stage 1 as refinement guidance.

**Rough build order:**

| Milestone | What ships |
|---|---|
| **v0.1** | DASH-01 (store format + maturity ladder), DASH-04 (board CLI + render), DASH-12 (dashboard.html), DASH-15 (conductor/worker doctrine), DASH-16 (dashboard as user-facing doc), DASH-18 (supersede piecemeal proposals) |
| **v0.2** | DASH-02 (autonomous capture hook), DASH-05 (roadmap mode), DASH-06 (version-milestone model), DASH-08 (joint co-review + L2), DASH-17 (harness integration + verb policy), DASH-19–21 (review-tier skill), DASH-23 (refinement sub-agent), DASH-24 (async coupling contract) |
| **v0.3** | DASH-03 (Linear mirror), DASH-09 (orchestrate mode), DASH-10 (contract artifact), DASH-11 (engine handoff), DASH-13 (in-browser edit via File System Access API), DASH-22 (budget hint) |

### Dashboard as living user-facing documentation

The `dashboard.html` is a derived view — it re-renders from the store on every mutation (`board.py render` runs automatically). It is not hand-edited. It is the *iterated form* of user-facing documentation: it shows roadmap-by-version timeline + backlog kanban, and in v0.3 supports in-browser edits via the File System Access API with a download-patched-store fallback (zero server, static, cross-runtime).

### Feedback loops

- **Co-review → refinement guidance:** each Stage 2 session distills lessons (roadmap direction, accepted acceptance shapes, trim/staleness patterns) into `.refine-guidance.md`, sharpening Stage 1 Sonnet sub-agents over time. This is the only durable guidance path — it is not stored in `repo_memory` (a capped 30-item entry-point CLI, not a queryable index).
- **Forecast vs actuals calibration:** budget-hint calibration against real outcomes requires adding `token_count` and `runtime_s` fields to `dispatch_ledger.py` and collecting actuals across several runs. Until that corpus exists, the hint remains explicitly non-predictive. This is a named prerequisite before DASH-22 can improve.

---

*This is a usage guide over a partially proposed system. Only the `plan` verb (`recipes/plan.md` + `templates/building-plan.md`) and the `audit` Goal-readiness dimension are shipped. Everything else — backlog store, capture hook, roadmap mode, orchestration skill, review-tier skill, and dashboard — is proposed and assigned to v0.1–v0.3 above.*
