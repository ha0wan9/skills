# Proposal: plan/roadmap intake hardening (v0.4) — lessons from `fullstack-dev-skills`

> **Status:** Proposed (design). Backs the v0.4 milestone "Plan/roadmap intake hardening"
> (board items DASH-026…030); this doc is the `source` those items point to.
> **Scope:** strengthen the *front* of `/project-meta plan` and `/project-meta roadmap` with
> intake rigor mined from `jeffallan/claude-skills` (`fullstack-dev-skills`) workflow commands.
> **Grounding:** direct read of `fullstack-dev-skills` commands (`common-ground`,
> `approve-synthesis`, `create-epic-plan`, `execute-ticket`) against the current
> `recipes/plan.md`, `recipes/roadmap.md`, `recipes/refine.md` (this session, 2026-06).
> Aligns with memory `cli-toolkit-doctrine` (CLI-ify deterministic prose),
> `prefer-lightweight-derived-design` (reuse review-tier / board.py / multi-agent-protocols,
> don't build new machinery), and `capture-decisions-as-preferences` (the assumption tiers).

## 0. Framing — substrate vs mechanics

`fullstack-dev-skills`' lifecycle is **Jira/Confluence-coupled** (epics → tickets → story
points → JQL); `plan`/`roadmap` are **repo-local, CLI-first, falsifiability-obsessed**. So what
transfers is the **mechanics**, not the substrate — implemented in board.py / recipe idiom, not
by adopting Jira. `plan`/`roadmap` already out-do `fullstack` on the falsifiability floor (§6
matrix, AP-PLAN-1), atomic writes (`items_sha256`), write/judge separation (`plan` writes,
`audit` judges), and the single co-review transaction (DASH-08). The gap is purely **intake**.

## 1. Assumption surfacing + two-axis classification (DASH-026)

`common-ground` surfaces the assumptions Claude is about to build on and classifies each on two
independent axes: **type** = `stated | inferred | assumed | uncertain` (*immutable* — audit
trail of derivation) × **tier** = `ESTABLISHED | WORKING | OPEN` (*mutable* confidence, with
transition rules). High-impact assumptions **start OPEN unless strongly evidenced**, and OPEN
ones gate action.

- **Today:** `plan` step 1 captures the Goal + (strict) non-goals; `roadmap` "asks meaningful
  questions" — neither keeps a *classified* assumption ledger.
- **Delta:** an unsurfaced OPEN assumption is the roadmap/plan analog of an unfalsifiable §6 row
  — a clean **AP-PLAN-2** ("building a plan/version on unsurfaced OPEN assumptions"). `roadmap`
  needs it most: version assignment hinges on direction/feasibility assumptions.
- **Idiom:** a `board.py assumptions` ledger or a §0 in `building-plan.md`; gate OPEN before
  scheduling/finalizing. An ESTABLISHED assumption is the `capture-decisions-as-preferences`
  ladder at repo scope.

## 2. Blocking-decision ledger (DASH-027)

`approve-synthesis` treats blocking decisions as structured objects —
`{question, options, recommendation, rationale, blocks: [ids]}` — that **must resolve before**
downstream artifacts are created, recording the resolution (option + resolver + timestamp).

- **Today:** `plan` surfaces gaps; `roadmap` co-decides — but decisions aren't tracked objects
  that gate progression and persist their resolution.
- **Delta:** a named decision ledger that blocks a milestone from being scheduled until
  resolved, and records *why*. Pairs with #1 (a high-impact OPEN assumption *becomes* a blocking
  decision).
- **Idiom:** `board.py` decision rows or a `decisions:` frontmatter block; deliver-before-commit
  already surfaces it.

## 3. Risk rubric that *derives* the review tier + sequencing (DASH-028)

`create-epic-plan` scores each change across **7 dimensions** (scope, dependencies, blocking,
stability, UX, testing, **reversibility**; 1–3 each) → 7–11 proceed / 12–16 incremental + review
/ 17–21 spike-first.

- **Today:** `refine` has a rough `S/M/L`; `plan` has floor/strict; review-tier `L0–L3` exists —
  but the tier is *chosen, not derived*.
- **Delta:** the missing *deriving function* — a score that auto-selects plan floor-vs-strict,
  the `L0–L3` review tier, and roadmap sequencing (high reversibility/blast-radius → spike-first
  or earlier). Reuses the existing tiers: **derived, not new machinery**.
- **Idiom:** a `risk_score.py` (`score → tier`) CLI per `cli-toolkit-doctrine`, not a prose
  table. Reversibility maps onto the repo's blast-radius posture.

## 4. Plan-time codebase discovery sweep (DASH-029)

`create-epic-plan` Phase 1 launches parallel read-only `Explore` agents (affected modules · API
patterns · component patterns · **test locations + fixtures** · reference implementations) and
synthesizes them into the plan.

- **Today:** `plan` instantiates the template and fills §6 with no prescribed discovery.
- **Delta:** this *directly serves falsifiability* — §6 demands a **real fixture path** and an
  **exact command** per row, which you can only fill honestly after locating the test
  dirs/fixtures/reference impls. A read-only Explorer sweep turns §6 from hand-waved into
  fillable. Reuses `multi-agent-protocols` (read-only Explorers, Sonnet tier) — no new infra.

## 5. Proposal→approved diff + follow-up routing (DASH-030)

`approve-synthesis` writes a "Changes from Original Proposal" delta (added/removed/modified) on
approval; `execute-ticket` drafts discovered follow-ups + recommends a placement and waits.

- **Today:** `roadmap` emits `.refine-guidance.md` (free-text lessons); `refine`
  operator-confirms.
- **Delta:** capture the **delta between the AI's proposal and the operator's decision** in the
  DASH-08 co-review (defer-back / trim / spawn) as *structured* input to `.refine-guidance.md`
  — "operator keeps trimming X-shaped items" sharpens `refine` far faster than free text. Route
  execution-time follow-ups into `board.py` inbox with a recommended disposition.

## What NOT to copy

- The 66 personas, decision trees, and `MODELCLAUDE.md`'s TDD/debugging mandates — the
  arbitration table **defers** intra-task methodology to the methodology plugin (AP-COORD-7).
- `the-fool`'s adversarial machinery — already covered by `claims-adversary`,
  `methodology-critic`, `pressure_test_skill.py`. Borrow only its *mode taxonomy* (Socratic /
  pre-mortem / red-team / falsification) as pressure-test vocabulary.
- The checkpoint *saturation* (`MANDATORY CHECKPOINT … DO NOT PROCEED` at every phase) — take
  the gate *structure* (classified assumption, blocking-decision object, risk score), not the
  *quantity* of human stops. `fullstack`'s own `MODELCLAUDE.md` says "one question at a time."

## Sequencing note

DASH-028 (risk→tier deriver) is the smallest and most reused; DASH-026/027 (assumption gate +
decision ledger) interlock and both land in `roadmap`. A natural build order is 028 → 026 →
027 → 029 → 030, but that is a `roadmap`/co-review call, not fixed here.
