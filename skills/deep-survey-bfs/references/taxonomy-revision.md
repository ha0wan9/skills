# Taxonomy Revision

## Contents

- [Why Taxonomies Drift](#why-taxonomies-drift)
- [Two-Axis Default](#two-axis-default)
- [Revision Triggers](#revision-triggers)
- [Bucket Hygiene](#bucket-hygiene)

## Why Taxonomies Drift

A taxonomy framed at Round 1 reflects the papers in Round 1. After Round N
adds new papers, the partition can become stale:

- A new paper introduces a method that doesn't fit any existing bucket
- Two existing buckets collapse into one because the field has converged
- A bucket subdivides because new papers reveal an internal distinction

Taxonomies that don't revise drift toward over-fitting Round 1 papers and
mis-classifying later additions. The skill enforces taxonomy review after
every Round N that adds ≥3 papers.

## Two-Axis Default

A single-axis taxonomy is fragile. Use two orthogonal axes by default:

- **Primary axis**: usually method route (architecture / training
  objective / pretraining paradigm). This is the axis the field uses to
  organize itself.
- **Secondary axis**: orthogonal cut. Common choices:
  - Output modality (what the model produces — labels, language,
    images, multi-modal)
  - Deployment target (cloud / edge / embedded)
  - Scale tier (small / medium / large parameter counts)
  - Data regime (fully supervised / self-supervised / few-shot /
    zero-shot)

The two axes should be roughly independent. If the secondary axis ends
up nearly identical to the primary axis, pick a different secondary.

When papers cluster differently on the two axes, that's the value of
the second axis: it makes design-space sparsity visible (e.g., "no one
has tried autoregressive pretraining for the edge deployment tier yet").

## Revision Triggers

After every Round N that adds ≥3 papers, ask:

1. **Does any new paper not fit any existing bucket?**
   → Add a new bucket. Document the boundary in the taxonomy section.

2. **Are two buckets now drawing on the same papers?**
   → Either merge them, or sharpen the boundary (define what's actually
   different). If the boundary cannot be sharpened, merge.

3. **Has the field's vocabulary changed?**
   → Update bucket names. Older names can persist as aliases.

4. **Did Round N add a paper that should have caused you to find prior
   work in a different bucket?**
   → That earlier work was likely missed in Round 1. Trigger another
   targeted Round N.

5. **Is a bucket now empty or near-empty?**
   → Either drop it, or annotate as "future direction observed in
   isolated work" with the single paper as a forecast signal.

## Bucket Hygiene

- **Buckets must partition, not duplicate.** A paper belongs in at most
  one primary-axis bucket. Cross-listing a paper means you have a poorly
  drawn boundary.
- **Bucket names should describe the discriminating feature**, not the
  topic. "Masked Autoencoding" is a good name (says what's distinct);
  "Self-supervised Models" is a poor name (most modern work falls in it).
- **2-7 top-level buckets** is the typical range. Beyond 7, the
  taxonomy stops reducing complexity for the reader.
- **Sub-buckets are allowed** for buckets that grow large, but at most
  one level of nesting before the survey becomes a directory listing.

## Output

Record the revision in the timeline section of `survey.md`. A v2 taxonomy
revision typical line:

```markdown
*v2 taxonomy revision: split Route A into A1 (MAE) and A2 (BERT-style
masked spectral prediction) after P022 and P023 made the methodological
distinction load-bearing for the comparative analysis in §4.2.*
```
