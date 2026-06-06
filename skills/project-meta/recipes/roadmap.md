# Recipe: roadmap

Collaborative, versioned **roadmap mode** (DASH-05) built around the **joint backlog↔roadmap
co-review transaction** (DASH-08). Distinct from `plan`: `roadmap` decides *which refined items
go in which version*; `plan` turns *one chosen milestone* into a falsifiable build plan.

> **Stability: provisional.** Promoted from the Reserved list as the headline capability of
> Project Board v0.2. Treat the workflow shape as still settling.

## When to load

- User invokes `/project-meta roadmap`.
- User asks to "groom the backlog", "plan the next version", "what goes in v0.x", or to
  reconcile the backlog against the roadmap.

## Mode

**editing** — co-builds the roadmap *with* the operator and writes `items.jsonl` +
`roadmap.json` **atomically** via `scripts/board.py`. Interactive, judgment-heavy → runs on the
**main session / Opus** (DASH-15 conductor tier). The L2 review panel below delegates to Sonnet.

## Required references

- [`references/review-tier.md`](../references/review-tier.md) — the co-review is an **L2** instance (multi-expert panel).
- [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md) — how to dispatch the parallel L2 panel on clean context.
- [`recipes/refine.md`](refine.md) — the item-prep sub-workflow (`fuzzy → refined`) this session calls when a candidate item is not yet concrete.

## Workflow — one co-review transaction (DASH-08), not two phases

Grooming is **not** "clean the backlog, then make the roadmap." It is a **single transaction**
that reads both surfaces, decides jointly, and writes both back atomically.

1. **Snapshot both.** Read the refined+active pool
   (`board.py list --maturity refined --disposition active`) and `roadmap.json`. Note the
   `roadmap._meta.items_sha256` — the optimistic-concurrency token.
2. **Co-build the versioned timeline (DASH-06).** Each milestone ↔ a version (`v0.1`, `v0.2`, …);
   the roadmap is the versioned ROAD (done / now / todo). Propose milestones, **ask meaningful
   questions, co-decide with the operator** — do not unilaterally assign.
3. **Joint co-review at L2 (DASH-08).** Dispatch a parallel panel (review-tier L2) reading *both*
   surfaces with distinct lenses: **roadmap lenses** (feasibility · robustness · usefulness ·
   usability) + **backlog lenses** (still-relevant · refined-enough · right-version · staleness).
   Decisions flow **both ways**: refined → versions; over-heavy version → defer back to the pool;
   off-direction → trim; a new milestone goal → spawn backlog items (then `refine` them).
4. **Resolve dedup here.** This is the **single-writer gate** where capture-time duplicates
   (multiple sessions captured the same idea) are merged — never at capture.
5. **Write back atomically.** Assign versions with
   `board.py move <id> scheduled --version <vX>`. `board.py` rewrites `items.jsonl` +
   `roadmap.json` under a lock with an `items_sha256` check; a **stale snapshot aborts**
   ("stale board snapshot") — re-snapshot (step 1) and redo. Invariant: a `refined` item is in
   **exactly one version XOR** the pool, never both.
6. **In-flight on a version cut.** When a version closes with `scheduled`/`in_progress` items
   unfinished: **carry them over** to the next open version (keep `status`, re-tag `version`) —
   never silent-drop. Log it as a co-review note. *(Pre-decided default; see project-board-system.md
   Open questions.)*
7. **Emit refinement guidance.** Distill this session's lessons (current direction, acceptance
   shapes that passed, recurring trim/staleness reasons) into `docs/backlog/.refine-guidance.md`
   so the `refine` recipe sharpens over time. Promote per the Memory Contract — small and current.

## Output contract

Updated `roadmap.json` (versioned milestones) + `items.jsonl` (refined items now
`scheduled@vX`), written atomically; `.refine-guidance.md` updated; dashboard re-rendered. The
result is a **shared, user-facing artifact** — deliver it for operator review **before any
`git commit`** (pre-commit delivery), like every editing recipe.

## Anti-patterns

- **Two-phase grooming** ("clean backlog, then build roadmap"). DASH-08 is **one** transaction;
  splitting it lets the two surfaces diverge.
- **Non-atomic writes** to items/roadmap (divergence: an item in a version *and* the pool).
- **Skipping the L2 panel** for a roadmap change (AP-COORD-2). A roadmap is design-scope work.
- **Unilateral version assignment.** `roadmap` is collaborative — co-decide, don't dictate.
- **Capture-time dedup.** Dedup is resolved here (single writer), never at append-only capture.
