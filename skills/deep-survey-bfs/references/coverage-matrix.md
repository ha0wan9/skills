# Coverage Matrix

## Contents

- [Matrix Shape](#matrix-shape) — sub-question rows × dimension columns
- [Active Cells vs N/A](#active-cells-vs-na) — not every cell needs coverage
- [Cell States](#cell-states) — closed / weak / gap
- [Round N Targeting](#round-n-targeting) — gap-driven, not curiosity-driven
- [Closure Rules](#closure-rules) — when audit passes

## Matrix Shape

Rows: sub-questions from `index.md` (6-12 typically).
Columns: evidence dimensions:
- **theory** — frameworks, formulations, novel methods proposed
- **experiment** — empirical results, benchmarks, ablations
- **survey** — review articles aggregating prior work
- **critical-review** — limitations, negative results, failure modes
- **dataset** — benchmarks, data releases, evaluation protocols

Cells contain the list of `P00X` paper IDs that are ★★★ for that
sub-question on that dimension.

## Active Cells vs N/A

Not every (sub-question, dimension) cell needs coverage. The frame phase
records which dimensions activate per sub-question:

- A sub-question about historical evolution may need only `survey` and
  `theory`, not `dataset`.
- A sub-question about deployment realities needs `experiment` and
  `critical-review`, not necessarily `theory`.
- A sub-question about benchmarks needs `dataset` and `experiment`.

Inactive cells are marked `N/A` in the matrix and do not block audit.

## Cell States

Each active cell has one of:

- **closed**: ≥1 ★★★ paper, distinct enough to support the claim.
- **weak**: covered, but with concerning concentration (single lab, single
  year ±1, single benchmark, single language). Audit can pass with weak
  cells if the user explicitly accepts the limitation.
- **gap**: 0 ★★★ papers. Round N must address before audit passes.

## Round N Targeting

For every `gap` and `weak` cell, the matrix row records:

```
| sub_question | dimension | state | target | search_strategy |
```

`target` is the concrete description of what's missing (not "find more
papers"). Examples:
- "Recent (2025+) critical-review of FM scaling on EEG"
- "Independent reproduction of LaBraM on a non-Chinese institution
  benchmark"
- "Dataset paper for high-density EEG (>128ch) public release"

`search_strategy` is the concrete plan:
- "Citation BFS from REVE 2510.21585 forward citations on Semantic Scholar"
- "OpenReview ICLR 2026 review-stage papers tagged 'EEG foundation'"
- "DBLP query for Mayo Clinic / Cleveland Clinic EEG ML output 2024-2026"

If a Round N closes a `weak` cell into `closed`, update the state. If a
Round N adds a paper that opens a new sub-route in the taxonomy, flag
that and load `references/taxonomy-revision.md`.

## Closure Rules

Audit passes when:

1. Every active cell is `closed`, or
2. Remaining `weak` cells have explicit user acceptance recorded in
   `index.md`, AND
3. The bias audit passes (see `bias-audit.md`), AND
4. Every cell's ★★★ papers come from at least 2 distinct labs (else flip
   the cell to `weak`).

If after 4 Round Ns gaps remain, audit fails. Options:
- Narrow the survey scope (record changelog in `index.md`)
- Ship with documented limitations (record in `index.md` and
  `survey.md` §10)
- Pause the survey until literature catches up
