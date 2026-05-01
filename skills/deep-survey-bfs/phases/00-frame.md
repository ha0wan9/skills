# Phase: frame

Use when a survey is first articulated or when a survey lacks a stable
research question, sub-question decomposition, or scope boundary.

## Steps

1. Resolve `survey-id`. If absent, propose 2-3 kebab-case names and ask the
   user to choose. The ID is permanent — every paper ID, claim, and
   cross-reference will be tied to it.

2. Confirm the study root. Default `.research/surveys/<survey-id>/`; respect
   project adapter overrides if one exists.

3. Scaffold `index.md` from `templates/survey-index.md`. Required fields:
   - research question (one paragraph; what the user actually asked)
   - scope boundary table (in-scope / out-of-scope across signal type, model
     scale, time range, language, deployment)
   - sub-question list (6-12 items, each phrased as a discrete answerable
     question, not a topic)
   - decision criteria for star ratings (link to rubric reference)
   - target Round 1 sources (arXiv keywords, OpenReview venues, DBLP
     queries, Semantic Scholar topics)
   - expected evidence dimensions per sub-question (theory / experiment /
     survey / critical-review / dataset)

4. Scaffold empty `paper_index.md` from `templates/paper-index.md` with
   header row only.

5. Scaffold empty `claims.jsonl` (one row per claim once synthesis runs).

6. Scaffold `coverage_matrix.md` skeleton with sub-questions × dimensions,
   all cells empty.

7. Decide the survey's bias-audit thresholds (defaults: any single
   institution/country/year/method-route exceeding 60% of ★★★ papers
   triggers re-search). Record in `index.md`.

## Sub-Question Decomposition Rules

- Each sub-question must be answerable by 3+ papers, not by a single citation.
- Avoid sub-questions that overlap by more than 30% — they should partition
  the topic, not duplicate it.
- Include at least one critical/limitations sub-question (e.g., "what does
  the field still get wrong?") to force coverage of negative results.
- Include at least one engineering/deployment sub-question if the topic has
  any production angle.

## Hand Off

Set status to `framed`. Next phase is `round1`. Output the resolved
`survey-id`, study root, and the sub-question list before handoff so the
user can correct the decomposition before search begins.
