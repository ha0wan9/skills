# Reproducibility Assessment

## Contents

- [Why Reproducibility Is a Survey Dimension](#why-reproducibility-is-a-survey-dimension)
- [The 5-Question Rubric](#the-5-question-rubric)
- [`repro_status` Column](#repro_status-column)
- [Extraction Recipe](#extraction-recipe)
- [Reproducibility Tier](#reproducibility-tier)
- [Common Pitfalls](#common-pitfalls)

## Why Reproducibility Is a Survey Dimension

A paper's accuracy or latency claim is only as load-bearing as its
reproducibility. A SOTA number in a paper that never released code, or
released only weights without training recipes, or whose GitHub Issues
are full of "I cannot match these numbers" reports, **is not the same
strength of evidence** as a number from a paper with full open-source,
documented recipes, and active maintenance.

Surveys that treat all paper claims as equal provenance overweight
under-reproduced work and underweight engineering-strong work. The
reproducibility check forces the surveyor to grade each paper's
provenance and surface this grade in `paper_index.md` and the survey
prose.

## The 5-Question Rubric

For every ★★★ paper, answer these five questions:

1. **Code release status**: open-source / open-weights / closed?
   - **open-source**: full training + inference + eval code on GitHub
     (or equivalent), permissively licensed
   - **open-weights**: pretrained checkpoints released; training code
     missing or incomplete
   - **inference-only**: inference code + weights, no training code
   - **closed**: no code or weights, paper-only or technical report
2. **Recipe completeness**: are training recipes provided?
   - **complete**: full config (hparams, data preprocessing,
     augmentation, schedule, hardware, seed) sufficient to reproduce
   - **partial**: enough to fine-tune but not pretrain, or some
     hparams omitted
   - **absent**: no recipe; reproduction requires reverse-engineering
3. **Issue health**: any unresolved GitHub Issues that affect
   reproduction or numerical results?
   - **clean**: ≤2 stale repro-related issues, or all addressed
   - **mixed**: several open issues but actively triaged
   - **stale**: many unresolved issues, last response > 6 months ago
   - **unmaintained**: repo abandoned (no commits in >12 months)
4. **Code quality**: is this code worth checking out as a baseline /
   engineering reference?
   - **strong**: type hints, tests, CI, modular architecture, good
     READMEs, idiomatic patterns
   - **adequate**: works, follows reasonable conventions, no major
     anti-patterns
   - **weak**: monolithic scripts, hardcoded paths, missing tests,
     hard to modify
   - **unverified**: not yet inspected
5. **Third-party reproduction**: have independent reproductions
   matched, missed, or invalidated the headline numbers?
   - **confirmed**: ≥1 independent re-implementation or evaluation
     reports matching numbers (within stat. error)
   - **partial**: some metrics reproduced, others off
   - **failed**: third-party reports significantly worse numbers (e.g.,
     paperswithcode reproduction column / community benchmarks /
     OpenStereo-style aggregator finding deltas)
   - **unverified**: no third-party numbers found

## `repro_status` Column

The `paper_index.md` template carries a column `repro_status` whose
value is a compact summary like:

```
oss/recipe:complete/issues:clean/quality:strong/3p:confirmed
```

with `oss` = open-source, `ow` = open-weights, `io` = inference-only,
`cl` = closed; one tag per question, separated by slashes.

The bias audit and the synthesis prose can now read this column to
weight evidence appropriately.

## Extraction Recipe

For each ★★★ paper:

1. **Locate the repo URL**: from the arXiv abstract page, paper PDF
   first page, or the project page.
2. **Open the repo's README**: check for `code/`, `train.py`,
   `inference.py`, `configs/`, `docs/` structure.
3. **Open the Issues tab**: scan the top 10-20 open issues. Look for
   "cannot reproduce", "different from paper", "training instability",
   "hyperparameter mismatch". Sort by oldest unresolved.
4. **Look at recent commits**: when was the last code change? Is the
   default branch active or stale?
5. **Look at the model zoo / weights**: are pretrained checkpoints
   released? Training logs?
6. **Check for third-party validation**:
   - paperswithcode entry (when reachable) sometimes flags "matched"
     vs "claimed"
   - aggregator repos (e.g., OpenStereo, mmdetection model zoo) often
     re-evaluate baselines and report deltas
   - Twitter/X posts and Reddit threads from researchers reporting
     reproductions
7. **Score each of the 5 questions and write the `repro_status` row**.

The check is a **WebFetch + GitHub Issues read** task per paper,
~60-120 seconds. For a survey with 18 ★★★ papers, budget ~30 minutes
total.

## Reproducibility Tier

After populating `repro_status`, group papers into tiers for the
synthesis prose:

- **Tier R1 (gold-standard)**: open-source + complete recipes + clean
  issues + strong code + confirmed 3p reproduction
- **Tier R2 (solid)**: ≥4 of the 5 dimensions positive
- **Tier R3 (caveat)**: open-weights or partial recipes; numbers
  citable but flag in prose
- **Tier R4 (evidence-weak)**: closed code, or stale repo, or
  third-party reproduction failed; cite numbers only with explicit
  reproducibility caveat in the surrounding prose

In the survey's "Method-route comparison" table (§4) and per-paper
deep-dives (§5), include the tier as a small annotation:
`(P002) [R1]` or `(P008) [R3 — open-weights only]`.

## Common Pitfalls

- **Star-count is not reproducibility**. A 5k-star repo can have
  unresolved repro issues; a 50-star repo can be the only working
  reproduction of a popular paper.
- **"License: MIT" alone does not mean reproducible**. Check
  recipes and weights, not just the LICENSE file.
- **Fork count is not third-party reproduction**. Forks often clone
  for personal experiments without reporting deltas. Look for
  signed-off reports.
- **Closed-code SOTA papers**: when a foundation-model paper publishes
  numbers but no code/weights (rare but happens, e.g., NDA-protected
  industry work), record the tier R4 caveat explicitly. Do not silently
  treat the numbers as comparable.
- **Author-confirmed reproduction failures**: when authors themselves
  acknowledge in Issues that "v1 numbers are not reproducible with
  current code, see PR #N" — this is critical evidence, capture it as
  a claim with `confidence: medium` and `notes: 'author-confirmed
  repro gap'`.
