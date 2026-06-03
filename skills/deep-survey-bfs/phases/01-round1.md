# Phase: round1

Use after `frame` to do the broad multi-source search that populates the
initial paper index.

## Steps

1. Read `index.md`. Keep the research question and sub-question list visible
   while searching.

2. Load `references/source-coverage.md` and
   `references/arxiv-query-patterns.md`. Decide the search budget per
   source (default: 30-50 candidate hits per source, ~20 reaching the
   index). For arXiv queries, prefer `ti:`-anchored templates over
   `all:`; the patterns reference shows six concrete query intents
   with worked examples.

3. Search each source in this order:
   - **arXiv** — keyword + category filter. Primary breadth source.
   - **OpenReview** — same keywords, recent venues. Tells you peer-review
     status and reviewer scores.
   - **DBLP** — author / venue lookup for confirmed publications.
   - **Semantic Scholar** — citation count, influential-paper signals.

4. For each candidate paper, decide whether to include in `paper_index.md`:
   - the paper plausibly answers at least one sub-question, AND
   - the paper is within the scope boundary (signal type, time range, etc.).

5. For each included paper, score on the 4 dimensions defined in
   `references/paper-rating-rubric.md` and bin into ★ / ★★ / ★★★.

6. Append a row to `paper_index.md` with: paper ID (`P001` ascending),
   arXiv ID, title, first author + institution, year, venue (or "preprint"),
   sub-questions covered, evidence dimensions covered, star rating,
   one-line note.

7. Apply a cap that **scales with sub-question count**. The 25-35 default is
   calibrated for ~6-9 sub-questions (≈3-4 papers/SQ); a 12-13 SQ survey needs
   proportionally more or every cell starts under-covered. Use
   `cap ≈ max(30, 3 × N_SQ)` as the target, and if you exceed it, say so and
   why (a one-line note in `paper_index.md`). The cap's purpose is to reach the
   gap audit quickly with enough breadth to make the audit meaningful — not to
   starve a wide survey. Better papers can still come in Round N once gaps are
   known.

8. Run `python3 skill/scripts/coverage_check.py paper_index.md
   index.md` to print a preview coverage matrix (this is informational
   for Round 1; the formal audit is Phase 2).

## Execution Pattern: Fan Out by Sub-Question Cluster

For surveys with many sub-questions, a single sequential search is slow and
loses breadth. Load `references/multi-agent-dispatch.md` — the survey
specialization of project-meta's Task Dispatch paradigm — for the full
delegation template, runtime backings, and the mandatory ordering barrier. The
survey-specific shape (validated on a 13-SQ run):

1. **Partition the SQs into 3-5 clusters** by theme (e.g. one agent per
   direction-of-influence, or per level-of-analysis group). Dispatch one
   read-only search subagent (Explorer/Worker) per cluster, in parallel, each
   owning its SQs and returning candidate rows with proposed 4-dimension scores
   against the **same** rubric so scores are comparable.
2. **Barrier, then dedup/merge centrally — mandatory.** All agents return
   *before* any `paper_index.md` write (the ordering barrier). Independent
   agents will surface the same paper under different clusters (a paper that
   answers SQ1 and SQ5 comes back from both); merge duplicates into one
   lead-owned row with the **union** of sub-questions and dimensions before
   assigning a paper ID. Skipping the barrier double-counts papers and silently
   inflates the bias audit.
3. **Score once, centrally**, after dedup, so a paper has a single star rating
   regardless of how many agents found it.

Each agent verifies metadata (venue/year/author) against a primary source and
resolves the preprint trap before returning — no title-only hits.

## Source-Specific Notes

- arXiv abstract reads must be deep enough to confirm scope-fit. Title-only
  decisions cause false positives.
- For each paper, record whether it has been peer-reviewed. A 2024 arXiv
  preprint marked "to appear at NeurIPS 2024" should reflect that, not
  stay labeled "preprint".
- When the same work has multiple venues (workshop → main conference,
  arXiv v1 → v3), index the most authoritative version and note other
  versions in the row.

## Hand Off

Set status to `round1-done`. Next phase is `audit`. Report the paper count
by year and by sub-question; flag any sub-questions with zero ★★★ matches
as predicted gaps.
