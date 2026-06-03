# Phase: roundn

Use whenever the gap audit returns `audit-needs-roundN`. Each Round N is
gap-driven, not curiosity-driven.

## Steps

1. Read `coverage_matrix.md`. Identify the open `gap` and `weak` rows plus
   any `bias-trigger` flags from the bias audit.

2. For each gap, the row already names a `search_strategy`. If it is empty
   or stale, design a fresh strategy. Load
   `references/arxiv-query-patterns.md` if rewriting an arXiv query.
   - Different keyword set than Round 1 (synonyms, sub-domain terms).
   - Different source (e.g., switch to OpenReview if arXiv saturated).
   - Different time window (e.g., cite-trace older seminal works that
     keyword-search missed).
   - Different geographic / institutional cluster if bias trigger.
   - **Numeric-claim gaps** (latency tables, accuracy on specific
     val sets, parameter counts) are not solved by additional keyword
     search; they are extraction tasks. Load
     `references/evidence-extraction.md` and walk the source hierarchy
     for each affected paper.

3. Execute targeted searches. Constrain Round N to gap-relevant additions
   only — do not re-run broad search. Cap at 5-15 new papers per Round N.

4. For each new paper:
   - Append to `paper_index.md` with the next sequential `P00N` ID.
   - Score and bin per the rubric.
   - Note in the row's "round" column that this came from Round N.

5. After all gap searches:
   - Re-run the coverage matrix build.
   - Re-run the bias audit.
   - Load `references/taxonomy-revision.md` if Round N added ≥3 papers.
     A new Route or sub-route may need to be added to the taxonomy.

6. Hand back to `audit`. Phase chain: roundn → audit → roundn → audit
   until audit passes.

## Round N Discipline

- **Do not silently expand scope.** If a gap cannot be filled within the
  framed scope, escalate to the user: either accept the gap as a limitation
  (record in `index.md`), or amend the scope (record changelog in `index.md`
  and re-run audit on the amended scope).
- **Cap rounds at 4 total — but only *audit-gated gap rounds* count.** The cap
  exists so a survey that can't close its gaps doesn't loop forever. It does
  **not** limit post-audit additions: once the audit passes, folding in new
  evidence (a just-published paper), a user-directed addition, or a
  bias/weak-cell correction is a `version` update (see `05-version.md`), is
  **unbounded**, and does **not** reopen the gap audit. If after 4 gap rounds
  gaps still remain, the topic may not yet support the framed scope — record it
  and ship a smaller-scope survey or wait.
- **Weak-cell hardening is its own pass, distinct from gap-filling.** A gap
  round fills *empty* active cells; a weak-cell pass strengthens cells that are
  closed but concentrated (single lab / single year — `coverage_check.py` now
  flags these). Run it as a targeted `version` pass naming each weak cell, or
  accept+document the concentration in `coverage_matrix.md`. Don't conflate the
  two: a survey can be gap-free yet have weak cells.
- **Round N can also fan out, but always dedup against the existing index.**
  When a Round N spawns multiple search agents, follow the same ordering barrier
  as Round 1 (`references/multi-agent-dispatch.md`): agents return before any
  index write, then merge their hits into existing paper IDs (union the
  SQ/dimension tags) — never append a second row for a paper already indexed
  under a different sub-question.
- **One paper per gap is suspicious.** If a Round N adds exactly the
  minimum needed to close cells, audit those papers extra carefully — the
  search may have stopped at the first hit rather than the best hit.

## Hand Off

Set status to `roundN-done` and immediately hand to `audit`. Do not let
Round N flow directly into `synthesize`; the audit is the gate.
