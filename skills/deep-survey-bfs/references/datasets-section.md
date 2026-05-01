# Datasets Section

## Contents

- [Why Datasets Come Before Method Comparison](#why-datasets-come-before-method-comparison)
- [Canonical vs Emergent Classification](#canonical-vs-emergent-classification)
- [What To Include Per Dataset](#what-to-include-per-dataset)
- [The Adoption Heatmap](#the-adoption-heatmap) — visualizing dataset × paper coverage
- [Dataset Gaps](#dataset-gaps) — what evaluation regimes lack a benchmark
- [Anti-Patterns](#anti-patterns)

## Why Datasets Come Before Method Comparison

A survey that compares model accuracy without first establishing the
evaluation instrumentation is comparing on undefined ground. Two
papers reporting "1.59% D1-all on KITTI 2015" may have used different
splits, different preprocessing, or different metric definitions.
Two papers using "ETH3D" may mean the training split, the test split,
the leaderboard, or the Bad-1 vs Bad-0.5 metric. Without grounding
the dataset landscape first, the method-comparison table in §5 reads
the same numbers as if they were comparable when they may not be.

Empirically, surveys that defer datasets to a back section (e.g.,
"§6 Benchmarks") force the reader to context-switch repeatedly: read
a method's claim in §4, jump to §6 to understand the dataset, jump
back. Putting the datasets section at §4 (right after taxonomy and
timeline) primes the reader's evaluation lens before they encounter
any model-by-model claim.

This section is **mandatory** when the survey's research question
involves performance comparison. It can be light or skipped only when
the survey is purely conceptual (e.g., a taxonomy of methods without
empirical claims).

## Canonical vs Emergent Classification

The datasets section partitions the field's evaluation surface along
two axes:

### Canonical datasets

Datasets the field has converged on as the standard evaluation. A
dataset becomes canonical when:

- **adoption** ≥ 60% of ★★★ papers in the survey use it
- **age** ≥ 3 years since introduction (so the field has had time to
  standardize splits and metrics)
- **leaderboard maturity** — public leaderboard exists, accepts
  submissions, and has multiple top-rank changes over time

Canonical datasets often define what "this field" is — they're the
common benchmark substrate. For stereo matching, KITTI 2012/2015,
SceneFlow, Middlebury, and ETH3D fit this definition. For NLP
foundation models, GLUE/SuperGLUE/MMLU. For object detection, COCO
and LVIS.

### Emergent datasets

Datasets introduced more recently (≤2 years) that signal new
evaluation directions, fill capability gaps, or test new failure
modes. A dataset is emergent when:

- **adoption** is non-zero (≥1 ★★★ paper uses it) but below the
  canonical threshold
- **purpose** is articulated as filling a specific gap — e.g.,
  robustness, dynamic scenes, foundation-model zero-shot, edge
  deployment
- **time signal** — introduced in the last 1-2 years of the survey's
  time range

Emergent datasets are often more important for forward-looking
analysis than canonical ones, because they show **where the field is
moving**. For a 2026 stereo survey, RobustSpring (2025), Mono2Stereo
(2025), MonoTrap (2024), and Booster (2023+) are emergent — they
specifically target failure modes the canonical datasets miss.

### Borderline cases

Datasets older than 3 years but with low adoption are usually
**deprecated** — note them only if the survey explicitly addresses
historical evolution. Datasets newer than 2 years with already-high
adoption are an interesting signal — fast field transition; flag in
the survey's Frontiers section.

## What To Include Per Dataset

For every dataset that appears in the survey's evaluation tables,
record at minimum:

| Field | Example | Source |
|---|---|---|
| Name + canonical citation | "KITTI 2015 (Menze & Geiger, 2015)" | dataset paper |
| Year of release | 2015 | paper / project page |
| Class | canonical / emergent / deprecated | survey author judgment + adoption count |
| Size | "200 train / 200 test, 1242×375" | paper |
| Modality / characteristics | "real outdoor driving, sparse LiDAR GT" | paper |
| Standard splits | "official train / test; train usually subdivided 160/40 for val" | paper + community |
| Standard metrics | "D1-all (% pixels with disp error >3px); EPE" | paper |
| Adoption count in survey | "12 of 18 ★★★ papers in this survey" | claims/coverage matrix |
| First emergent paper that used it | (only for emergent class) "P022 PPMStereo, NeurIPS 2025" | paper_index.md |
| Known issues | "test labels not public; submission required for D1-all" | community knowledge |

For a typical survey with 8-15 distinct datasets, this section runs
60-150 lines. Use a table for canonical (familiar to all readers) and
prose with a one-line headline per emergent dataset.

## The Adoption Heatmap

Across the ★★★ paper set, build a coverage table:

| Paper \\ Dataset | KITTI-12 | KITTI-15 | SF | ETH3D | Middlebury | RobustSpring | Booster | DR | Sintel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P001 RAFT-Stereo | ✓ | ✓ | ✓ | ✓ | ✓ | (in P025 only) | — | — | — |
| P005 FoundationStereo | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| P022 PPMStereo | — | — | ✓ | — | — | — | — | ✓ | ✓ |
| P025 RobustSpring | (eval target) | (eval target) | (eval target) | (eval target) | (eval target) | ✓ (intro) | — | — | — |

The heatmap immediately reveals:

1. **Which datasets are universal**: rows that fill nearly every
   column. This identifies the canonical set with no further argument.
2. **Which papers evaluate narrowly**: a paper testing only one or
   two datasets has weaker generalization claims.
3. **Where the emergent datasets cluster**: usually a small number of
   papers use them, often the introducing paper itself plus 1-2
   follow-ups. This is a leading indicator for what next year's
   canonical might be.

Place the heatmap as the first artifact in the datasets section.
A typo / missing checkmark in the heatmap is a frequent cause of
spurious "this paper doesn't generalize" claims downstream.

## Dataset Gaps

End the datasets section by naming what the field does NOT yet have a
dedicated benchmark for. This is open-frontier evidence that the
Frontiers section (§12) can build on. Common gap categories:

- **Distance-disaggregated**: per-depth-bin error breakdown
- **Frequency-disaggregated**: per-spatial-frequency or per-texture
  error
- **Robustness-by-corruption-class**: covered by RobustSpring (P025)
  for stereo as of 2025, was a gap before
- **Edge-deployment evaluation**: most "real-time" claims have no
  shared edge benchmark
- **Open-set / out-of-distribution**: no standard split for stereo
  on previously unseen domains

If the field has a dedicated dataset for one of these gaps within the
survey time range, it's an emergent dataset that should be promoted in
the section. If it lacks one, name the gap explicitly and reference
which papers attempt the evaluation ad-hoc.

## Anti-Patterns

- **Listing every dataset that appears in any indexed paper**: the
  section becomes a directory rather than a structured comparison.
  Cap canonical at 3-7 datasets and emergent at 3-5.
- **No metric grounding**: "KITTI 2015" alone is ambiguous (D1-all?
  EPE? Bad-3?). Always pair name with the standard metric.
- **Treating dataset paper as a method paper**: a dataset-introducing
  paper is dataset-class evidence; do not rate it on the same star
  rubric as method papers without distinguishing.
- **Omitting deprecated datasets that current papers still cite**:
  if 2024 papers still report PSMNet on FlyingThings3D, the survey
  needs to acknowledge it as legacy — silently dropping it makes
  numbers in §5 unparseable.
- **No adoption count**: without "X of N papers use this", the
  canonical/emergent split is just claim, not measurement.
