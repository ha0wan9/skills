# Phase: audit

Use after Round 1 (or after every Round N) to verify coverage completeness
across sub-questions and evidence dimensions before allowing synthesis.

## Steps

1. Read `paper_index.md`, `index.md`, and `coverage_matrix.md`. Load
   `references/coverage-matrix.md` for the matrix protocol and
   `references/bias-audit.md` for the bias rules.

2. Build the coverage matrix:
   - Rows: every sub-question from `index.md`.
   - Columns: evidence dimensions (theory / experiment / survey /
     critical-review / dataset). Some sub-questions activate only a subset
     of dimensions — this is recorded in `index.md` at frame time.
   - Cells: list of `P00X` paper IDs that are ★★★ for that
     sub-question + dimension.

3. Mark gaps:
   - **Empty cell on an active dimension** → `gap` status with reason.
   - **One ★★★ paper from a single lab** in a cell → `weak` status (single
     source bias).
   - **All ★★★ papers from same year ±1** in a cell → `weak` status (recency
     bias).

4. Run the bias audit:
   - Count ★★★ papers by institution / country / year / method-route.
   - If any single bucket > 60% of ★★★ total, flag as `bias-trigger`
     and add a Round N entry naming the under-represented bucket as
     the search target.

5. Update `coverage_matrix.md` with status flags. Each gap row carries:
   `(sub_question, dimension, current_state, target, search_strategy)`.

6. Decide hand-off:
   - All cells `closed` and bias audit clean → next phase is `synthesize`.
   - Any cell `gap` or `weak` → next phase is `roundn`.
   - Note: "weak" cells can pass to synthesis if the user explicitly
     accepts the limitation. Record the acceptance in `index.md`.

## Common Audit Failures

- **All papers from same lab** when surveying a niche topic. Force a Round N
  targeted at adjacent labs / different geographic clusters.
- **No critical-review dimension covered** because all papers are
  enthusiast preprints. Force a Round N targeted at limitations / negative
  results / failure modes.
- **No dataset dimension** — happens when a topic spans methods but the
  surveyor never indexed dataset papers separately. Often a real gap, since
  benchmarks change conclusions.
- **Sub-questions phrased too broadly** — if a sub-question fills with 10
  papers but no two answer the same precise sub-claim, the sub-question
  needs splitting before audit can pass. This is the rare case where
  `index.md` is amended, with explicit changelog.

## Hand Off

Output the coverage matrix summary table (sub-question count, cells closed,
cells gap, cells weak, bias triggers) and the explicit Round N task list
for the next phase. Set status to `audit-passed` or `audit-needs-roundN`.
