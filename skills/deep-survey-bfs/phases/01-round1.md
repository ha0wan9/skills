# Phase: round1

Use after `frame` to do the broad multi-source search that populates the
initial paper index.

## Steps

1. Read `index.md`. Keep the research question and sub-question list visible
   while searching.

2. Load `references/source-coverage.md`. Decide the search budget per source
   (default: 30-50 candidate hits per source, ~20 reaching the index).

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

7. Apply a hard cap: Round 1 ends at 25-35 papers. Going beyond delays
   the gap audit; better papers can come in Round N once gaps are known.

8. Run `python3 skill/scripts/coverage_check.py paper_index.md
   index.md` to print a preview coverage matrix (this is informational
   for Round 1; the formal audit is Phase 2).

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
