# <survey-id>

> Master record for this BFS literature survey. Phase artifacts cross-reference
> this file. Sub-questions and scope are fixed at frame time.

## Identity

- Survey ID: `<survey-id>`
- Created UTC: `<YYYY-MM-DDThh:mmZ>`
- Owner: `<owner>`
- Status: `framed | round1-done | audit-needs-roundN | audit-passed | synthesized | vN-shipped`
- Survey root: `<path>`
- Parent / superseded: `<none or survey-id>`

## Research Question

<One paragraph. State the question the user actually asked, not your
re-statement.>

## Scope

| Dimension | In scope | Out of scope |
|---|---|---|
| <e.g. signal type> | | |
| <e.g. model scale> | | |
| <e.g. time range> | | |
| <e.g. language / region> | | |
| <e.g. deployment target> | | |

## Sub-Questions

Decomposition of the research question into 6-12 discrete answerable
sub-questions:

1. SQ1: <...>
2. SQ2: <...>
3. ...

## Active Evidence Dimensions

Per sub-question, mark which dimensions are required for closure:

| Sub-question | theory | experiment | survey | critical-review | dataset |
|---|---|---|---|---|---|
| SQ1 | ✓ | ✓ | | | |
| SQ2 | | ✓ | ✓ | ✓ | |

## Star Rating Rubric

Reference: `references/paper-rating-rubric.md`. Project-specific weights
or threshold overrides go here.

## Bias Audit Thresholds

Defaults: 60% for institution / country / year / method-route / venue.

| Bucket | Threshold | Notes |
|---|---|---|
| Institution | 60% | |
| Country | 60% | |
| Year | 60% | |
| Method route | 60% | |
| Deployment regime | 60% | |
| Venue type (preprint) | 60% | |

## Round 1 Source Plan

| Source | Keywords / queries | Cap |
|---|---|---|
| arXiv | `<query>` | 30-50 candidates |
| OpenReview | `<venues>` | 10-20 candidates |
| DBLP | `<authors / venues>` | 5-15 confirmations |
| Semantic Scholar | citation BFS from <seed> | as needed |

## Pointers

- `paper_index.md` — paper rows (P001, P002, ...)
- `claims.jsonl` — anti-hallucination claim contract
- `coverage_matrix.md` — sub-question × dimension matrix
- `survey.md` — synthesized prose (built only after audit-passed)
- `audits/` — round-by-round audit reports

## Changelog

| UTC | Change | Reason |
|---|---|---|
