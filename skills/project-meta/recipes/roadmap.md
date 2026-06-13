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
**main session (conductor tier — the active session model, per `references/multi-agent-protocols.md#model-tier`)**.
The L2 review panel below delegates to the fleet tier (Claude: Sonnet; Codex: GPT-5.4).

## Required references

**Base** — loaded when the verb runs:

- [`references/review-tier.md`](../references/review-tier.md) — the co-review is an **L2** instance (multi-expert panel).
- [`references/dispatch-card.md`](../references/dispatch-card.md) — dispatch trigger + bypass quick-reference for deciding when to dispatch the L2 panel.
- [`references/cli-command-patterns.md`](../references/cli-command-patterns.md) — shared command rules, including **deliver before commit** for editing recipes.
- [`recipes/refine.md`](refine.md) — the item-prep sub-workflow (`fuzzy → refined`) this session calls when a candidate item is not yet concrete.

**Lazy-load** — only when the named step needs it:

- [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md) — step 4: deeper mechanics for dispatching the parallel L2 panel (roles, context package, reviewer loop, L2 panel, context-mapping); load only when dispatching the panel.

## Workflow — one co-review transaction (DASH-08), not two phases

Grooming is **not** "clean the backlog, then make the roadmap." It is a **single transaction**
that reads both surfaces, decides jointly, and writes both back atomically.

1. **Snapshot both.** Read the refined+active pool
   (`board.py list --maturity refined --disposition active`) and `roadmap.json`. Note the
   `roadmap._meta.items_sha256` — the optimistic-concurrency token.
2. **Surface and classify assumptions (DASH-026).** Before assigning anything to a version,
   enumerate the assumptions the proposed milestone direction rests on. For each, record:
   - **type** ∈ {stated, inferred, assumed, uncertain}
   - **tier** ∈ {ESTABLISHED, WORKING, OPEN}
   - **impact** ∈ {high, low}

   Every **high-impact OPEN** assumption MUST be resolved in one of two ways before any item is
   scheduled into that milestone:
   - **Resolve in-session**: operator answers it → tier becomes ESTABLISHED or WORKING; record
     the resolution in co-review notes; or
   - **Become a blocking decision row**: `board.py decision-add <version> --question Q
     --options "a | b" --recommendation R --blocks DASH-x,DASH-y`

   Do not schedule items under an unresolved high-impact OPEN assumption — this is the assumption
   gate (see AP-PLAN-2). Low-impact or ESTABLISHED/WORKING assumptions are noted but do not block.
3. **Co-build the versioned timeline (DASH-06).** Each milestone ↔ a version (`v0.1`, `v0.2`, …);
   the roadmap is the versioned ROAD (done / now / todo). Propose milestones, **ask meaningful
   questions, co-decide with the operator** — do not unilaterally assign. Add milestone metadata
   with `board.py milestone-add <version> --title T [--detail D] [--status todo]`.
4. **Joint co-review at L2 (DASH-08).** Dispatch a parallel panel (review-tier L2) reading *both*
   surfaces with distinct lenses: **roadmap lenses** (feasibility · robustness · usefulness ·
   usability) + **backlog lenses** (still-relevant · refined-enough · right-version · staleness).
   Decisions flow **both ways**: refined → versions; over-heavy version → defer back to the pool;
   off-direction → trim; a new milestone goal → spawn backlog items (then `refine` them).

   Blocking decisions discovered during co-review are recorded immediately via
   `board.py decision-add` (DASH-027). The scheduling gate enforces them mechanically — see step 6.
5. **Resolve dedup here.** This is the **single-writer gate** where capture-time duplicates
   (multiple sessions captured the same idea) are merged — never at capture.
6. **Write back atomically (DASH-027).** Assign versions with
   `board.py move <id> scheduled --version <vX>`. The scheduling gate **refuses** if the target
   version has an unresolved decision blocking that item (empty `--blocks` blocks the whole
   milestone). `board.py` rewrites `items.jsonl` + `roadmap.json` under a lock with an
   `items_sha256` check; a **stale snapshot aborts** ("stale board snapshot") — re-snapshot
   (step 1) and redo. Invariant: a `refined` item is in **exactly one version XOR** the pool,
   never both. Resolved decisions are recorded via `board.py decision-resolve <version> <DEC-id>
   --option CHOSEN --resolver WHO`; `done` milestones are exempt from the gate.
7. **In-flight on a version cut — gate-compatible carry-over.** When a version closes with
   `scheduled`/`in_progress` items unfinished, carry them over to the next open version (vNext) —
   never silent-drop. **Carry requires vNext to be decision-clean first**: resolve or record
   blocking decisions for vNext before moving items into it. If vNext has an unresolved decision
   blocking a carried item, return that item to the pool (`board.py move <id> unscheduled`) rather
   than bypassing the gate — no `--force` flag exists. Log every carry and every pool-return as a
   co-review note. *(Pre-decided default; see project-board-system.md Open questions.)*
8. **Emit refinement guidance (DASH-030).** After co-review, produce a structured
   **proposal-diff** — one row per divergence between the AI proposal and the operator decision:

   `{item, ai_proposal, operator_decision, delta, reason}`

   where `delta` ∈ {accepted-as-is, modified, defer-back, trim, spawn, reject}.

   Fold the *pattern* (not the raw log) into `docs/backlog/.refine-guidance.md` under
   "Operator deltas (structured)": bounded to **≤10 rows**, merge-by-pattern, evict oldest.
   Execution follow-ups discovered mid-session route to
   `board.py inbox-add --body "suggest: defer to pool"` (or appropriate disposition); use
   `inbox-add` specifically — not `add`. No new CLI; dashboard rendering of the diff is out of
   scope. Then distill the session's broader lessons (current direction, acceptance shapes that
   passed, recurring trim/staleness reasons) into `.refine-guidance.md` per the Memory Contract —
   small and current.

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
- **Scheduling on unsurfaced OPEN assumptions** (AP-PLAN-2). Versioning a milestone without
  surfacing high-impact OPEN assumptions is the roadmap-level mirror of the unfalsifiable plan:
  the work is built on unacknowledged bets that aren't visible until they fail mid-execution.
  Step 2's assumption pass is the fix.
