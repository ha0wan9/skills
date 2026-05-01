# Bias Audit

## Contents

- [Why Audit Bias](#why-audit-bias)
- [Buckets Audited](#buckets-audited)
- [Threshold Rules](#threshold-rules)
- [Trigger Action](#trigger-action)
- [Documenting Accepted Bias](#documenting-accepted-bias)

## Why Audit Bias

A coverage matrix can pass the gap audit while silently encoding source
bias. Common patterns:

- All ★★★ papers from one institution (the lab that publishes most
  often on the topic)
- All ★★★ papers from one country (mirrors funding cluster, not
  technical landscape)
- All ★★★ papers from a 2-year window (recency bias)
- All ★★★ papers using one method route (because the surveyor's keyword
  set matched that route's vocabulary)

The bias audit makes these patterns visible before synthesis bakes them
in.

## Buckets Audited

Among the ★★★ papers, count distribution along:

| Bucket | Threshold trigger | Why |
|---|---|---|
| Institution | any single > 60% | indicates lab capture |
| Country / region | any single > 60% | funding/cluster bias |
| Year | any single > 60% | recency/staleness bias |
| Method route | any single > 60% | keyword-set bias |
| Deployment regime | any single > 60% | scope assumption bias |
| Venue type | preprint > 60% | unsettled-claims bias |

The 60% threshold is a default. The user can record alternative thresholds
in `index.md` at frame time (e.g., a survey *of* a single lab's output
should set institution threshold to 100%).

## Threshold Rules

Compute per bucket from the ★★★ subset only:

```python
ratings_count = len(starstar_papers)
for bucket in buckets:
    largest_share = max(distribution.values()) / ratings_count
    if largest_share > threshold:
        flag_bias_trigger(bucket, dominant_value, largest_share)
```

Multiple triggers can fire from the same Round N output. They each become
separate Round N+1 entries in the matrix.

## Trigger Action

A bias trigger creates a Round N entry with:

- **Target**: the under-represented bucket value (e.g., "non-Chinese
  institutions", "2022-2023 papers", "CNN-based approaches")
- **Search strategy**: tailored to find work in that bucket. Examples:
  - Country bias → search non-English-language venue archives
  - Year bias → cite-trace older seminal works that keyword search
    skipped
  - Method bias → reformulate keywords using the under-represented
    method's vocabulary
  - Venue bias → query DBLP for top conferences in the time range,
    cross-reference titles

If the bucket cannot be filled (the under-represented value really has
no work) — record this in `index.md` and `survey.md` §10 (open
challenges). The absence is itself a finding.

## Documenting Accepted Bias

If the survey concludes with a known bias the user accepts, document it
explicitly:

```markdown
**Scope limitation (v1)**: This survey's ★★★ paper set is 78% from
Chinese research groups, reflecting the field's geographic concentration
since 2024. Round 2 search at non-Chinese institutions found 4 papers,
all rated ★★ on the rubric due to less direct engagement with the
sub-questions. The survey's conclusions reflect this concentration; cross-
referencing with the Mayo Clinic critical review (P005) is recommended
for a counterweight.
```

Documented bias is acceptable; silent bias is not.
