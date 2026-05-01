---
name: deep-survey-bfs
description: >-
  Conduct rigorous breadth-first literature surveys on technical topics: frame
  the research question with a sub-question decomposition, run a broad
  multi-source search (arXiv, OpenReview, DBLP, Semantic Scholar), score papers
  on a 4-dimension rubric, audit coverage with a sub-question x dimension
  matrix, fill gaps via targeted rounds, synthesize multi-axis taxonomies and
  timelines with per-paper deep-dives, audit for source/institution/year bias,
  and version reports incrementally as new evidence (papers, datasets, weights,
  experiments) arrives. Use when the user asks for a literature review,
  comprehensive survey, "research X for me", or wants to expand/audit an
  existing survey.
---

# Deep Survey (BFS)

Thin router for breadth-first literature surveys. Resolve the phase, resolve
`survey-id`, then load only the procedure file you need. Survey artifacts live
under `.research/surveys/<survey-id>/` by default; a project adapter may
override the root.

`survey-id` rules: kebab-case, 2-5 tokens, no dates, no version suffixes,
explicit about the topic. Good: `eeg-foundation-models`,
`stereo-matching-edge`, `mamba-vs-transformer-vision`. Bad: `survey1`,
`my-research-v2`, `stuff`.

## Core Mechanism: BFS with Coverage Gates

The skill enforces breadth-first exploration with hard completeness gates,
inspired by PRISMA scoping reviews adapted for LLM workflows:

1. **Frame** decomposes the research question into 6-12 sub-questions.
2. **Round 1** does a broad multi-source search; every paper gets a 4-dimension
   score → star rating.
3. **Gap Audit** builds a sub-question × dimension coverage matrix. The skill
   does not proceed to synthesis until every active cell has ≥1 ★★★ paper.
4. **Round N** runs targeted searches against gaps; loops back to audit.
5. **Synthesize** produces multi-axis taxonomy, timeline, per-paper deep-dives,
   challenges, frontiers, direct Q&A, and a multi-tier reading list.
6. **Version** adds new evidence (papers, datasets, model weights, experiments)
   as delta sections without rewriting prior content.

## Phases

| Phase | Question answered | Procedure |
|---|---|---|
| `frame` | What are we surveying, what are the sub-questions, what is in/out of scope? | `phases/00-frame.md` |
| `round1` | What does a broad multi-source search reveal? | `phases/01-round1.md` |
| `audit` | Is coverage complete across sub-questions and evidence dimensions? | `phases/02-gap-audit.md` |
| `roundn` | How do we fill the named coverage gaps? | `phases/03-roundN.md` |
| `synthesize` | What is the answer, the taxonomy, and the reading list? | `phases/04-synthesize.md` |
| `version` | How do we add new evidence without rewriting? | `phases/05-version.md` |

## Auto-detect

If arguments do not start with a phase keyword:

1. No survey directory exists → `frame`.
2. `index.md` exists but no `paper_index.md` rows → `round1`.
3. `paper_index.md` has rows but no `coverage_matrix.md` → `audit`.
4. `coverage_matrix.md` has gaps with `status: open` → `roundn`.
5. Coverage matrix is closed but no `survey.md` → `synthesize`.
6. `survey.md` exists and the user asks to add new evidence → `version`.

State the detected phase, `survey-id`, study root, and reason before loading.

## Loading Rules

1. Read exactly one phase file after resolution.
2. Load `references/source-coverage.md` during `round1` and `roundn` whenever
   you need to recall how to query each source.
3. Load `references/arxiv-query-patterns.md` before composing any arXiv
   query. The default `all:` query returns recency-sorted noise; the
   reference defines six template intents and their field specifiers.
4. Load `references/paper-rating-rubric.md` whenever you score papers.
5. Load `references/coverage-matrix.md` during `audit` and at every `roundn`
   re-audit.
6. Load `references/evidence-extraction.md` whenever a phase needs to
   extract numeric claims from a paper PDF, paperswithcode, OpenReview
   supplementary, or a repo README. Required reading before populating
   `chart_data.csv`-style structured tables.
7. Load `references/claims-discipline.md` before writing any synthesis section.
8. Load `references/taxonomy-revision.md` during `synthesize` and after every
   `roundn` that adds ≥3 papers.
9. Load `references/bias-audit.md` during `audit`.
10. Load templates only when scaffolding the matching artifact.

## Cross-Cutting Invariants

- Never skip `frame`; without sub-questions the gap audit cannot run.
- Sub-question decomposition is fixed at frame time; new sub-questions trigger
  a new survey, not a silent edit.
- Every paper has a stable ID (`P001`, `P002`, ...) that all later sections
  reference. Renumbering invalidates every cross-reference.
- Every claim in `survey.md` resolves to a row in `claims.jsonl` that names the
  paper ID, the section/page, and a verbatim quote or table reference. No
  speculation, no "I think", no implicit synthesis without a backing claim.
- Mark unknown values explicitly (e.g., "未披露", "not disclosed", "N/A") in
  comparison tables. Never guess.
- Round N is gap-driven, not curiosity-driven. Each Round N entry must name
  the gap it addresses.
- Taxonomies are revisable. After Round N adds ≥3 papers, re-evaluate whether
  existing buckets still partition cleanly.
- Bias audit must run before synthesis. If institution / country / year /
  method-route distribution is over-concentrated (any one bucket > 60% of
  ★★★ papers), trigger an additional Round N targeted at the under-represented
  bucket.
- Version updates must preserve prior section anchors so cross-references
  survive.
- Do not change secrets, credentials, or external accounts as part of survey
  work.

## Gotchas

- **arXiv-only is not enough.** arXiv preprints get out of date when the
  paper is accepted at a venue; OpenReview tells you peer-review status,
  DBLP tells you canonical venue, Semantic Scholar gives citation count.
  The four sources together prevent the "preprint label" trap (see
  `references/source-coverage.md`).
- **Star rating ≠ relevance.** A 5-citation 2025 preprint can be ★★★ if
  it answers a sub-question precisely; a 200-citation 2018 paper can be ★★
  if it predates the field's reframing. Score on the 4 dimensions
  independently before binning.
- **Gap audit on counts is weaker than on dimensions.** "≥3 papers per
  sub-question" lets you accumulate three papers from the same lab/year.
  The dimension matrix (theory / experiment / survey / critical-review)
  catches this — see `references/coverage-matrix.md`.
- **claims.jsonl is the anti-hallucination contract.** Build it before
  writing the synthesis prose. Every line in `survey.md` that asserts a
  fact must point to a claim row. The validator script checks this.
- **Versioning is delta-only.** v2 does not rewrite v1 sections. It adds
  new sections with `(vN added)` markers and updates prior sections with
  minimal in-place edits when a v1 claim is now superseded by new evidence.

## Running Under /loop Dynamic Mode

When the survey is being progressed asynchronously via `/loop` (no
fixed interval; ScheduleWakeup self-pacing), maintain a
`loop_state.json` artifact at the survey root scaffolded from
`templates/loop_state.json`. Read it at the start of every fired
iteration so the agent immediately knows iteration number, current
task, target paper IDs, blockers, and completed targets without
re-deriving from `paper_index.md` and `claims.jsonl`.

Per-iteration loop hygiene:

1. Read `loop_state.json`. If missing, scaffold from the template.
2. Use `current_task.target_paper_ids` and `target_metric_keywords` to
   plan the next 60-180 seconds of work. Prefer
   `scripts/extract_paper_metrics.py` for PDF table surfacing.
3. After completing the work, append a one-line entry to
   `audits/r<N>-progress.jsonl` summarizing what landed.
4. Update `loop_state.json`: increment `iteration`, set
   `last_updated_utc`, move the just-finished task into
   `completed_targets`, pop the next target from `next_targets` into
   `current_task`. Add to `blockers` if a target failed.
5. If any `stop_conditions` flip true, omit `ScheduleWakeup` and
   write a final summary instead.

## Output Footer

End each invocation with:

```md
**Phase**: <phase>  **Survey**: <survey-id>  **Status**: <status>  **Next**: <phase|done>
```
