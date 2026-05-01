# stereo-matching-edge-fm

> Master record for this BFS literature survey.

## Identity

- Survey ID: `stereo-matching-edge-fm`
- Created UTC: `2026-05-01T00:30Z`
- Owner: Haoran Wang
- Status: `framed`
- Survey root: `/home/user/Projects/skills-test/stereo-matching-edge-fm/`
- Parent / superseded: none

## Research Question

How do edge-deployable and foundation-model approaches to stereo matching
compare in 2020-2026 in terms of (a) accuracy on standard validation sets,
(b) parameter count by architecture family, (c) inference latency under
Torch Compile and TensorRT runtimes, and (d) what data characteristics —
near vs far depth, low vs high spatial frequency, distance robustness —
favor each model family? The answer should yield three comparison charts
(parameters × accuracy with architecture coloring; speed × accuracy under
two runtime baselines) and a model-vs-data-type analysis grounded in
reported per-condition results.

## Scope

| Dimension | In scope | Out of scope |
|---|---|---|
| Task | Two-view passive stereo matching producing dense disparity | Monocular depth, MVS (multi-view), active depth (LiDAR/ToF), event-based stereo |
| Time range | 2020-01 onwards | Pre-2020 work (referenced only as baselines) |
| Architecture | Transformer / CNN / hybrid / SSM-based / foundation-style | Pure classical (BM, SGBM) except as accuracy floor |
| Deployment | Edge (Jetson / mobile SoC / embedded) AND server-class with explicit speed reporting | Cloud-only models with no latency disclosure |
| Runtimes | Torch Compile baseline + TensorRT baseline (when reported) | Other runtimes (TVM, OpenVINO) considered only if Torch/TRT absent |
| Foundation-style | Models trained on multi-dataset pretraining or claiming general-purpose stereo (Stereo Anything / DepthAnything-stereo / FoundationStereo etc.) | Single-dataset specialized models |
| Hardware tier | Try to keep one consistent edge tier (e.g. Jetson Orin) and one server tier (e.g. RTX 3090 / A100) | Mixed-hardware claims accepted only with explicit hardware noted |
| Language | English papers | — |

## Sub-Questions

The decomposition is **9** sub-questions:

1. **SQ1** — What CNN-architecture stereo matching models from 2020+ are
   competitive on KITTI / SceneFlow / ETH3D / Middlebury, and what are
   their parameter counts and reported speeds?
2. **SQ2** — What Transformer-based stereo matching models exist (STTR,
   GMStereo, IGEV-style, etc.), and how do their accuracy / parameters /
   speeds compare to CNN baselines?
3. **SQ3** — What hybrid (CNN+Transformer) and SSM-based (Mamba, etc.)
   architectures have been published, and where do they sit on the
   accuracy-cost frontier?
4. **SQ4** — What foundation-style stereo matching models (multi-dataset
   pretraining, large-scale, "Stereo Anything" / "FoundationStereo" /
   "DepthAnything"-derived) have been published and what's their
   accuracy/cost profile?
5. **SQ5** — Which models report Torch Compile speed measurements, and on
   what hardware? What's the typical compile speedup over eager?
6. **SQ6** — Which models report TensorRT engine speed measurements, on
   what hardware (Jetson Orin, RTX 3090, A100, etc.), and at what
   precision (FP32 / FP16 / INT8)?
7. **SQ7** — Which models report per-distance or per-depth-bin accuracy
   breakdowns (near 0-5m / mid 5-20m / far 20m+) and what patterns
   emerge?
8. **SQ8** — Which models report per-frequency / per-texture conditioning
   accuracy (low-texture surfaces, high-frequency repetitive patterns,
   thin structures)?
9. **SQ9** — What are the dominant failure modes and known limitations
   of edge / foundation stereo models per critical reviews and
   benchmark papers?

## Active Evidence Dimensions

| Sub-question | theory | experiment | survey | critical-review | dataset |
|---|---|---|---|---|---|
| SQ1 | ✓ | ✓ | | | |
| SQ2 | ✓ | ✓ | | | |
| SQ3 | ✓ | ✓ | | | |
| SQ4 | ✓ | ✓ | | ✓ | |
| SQ5 | | ✓ | | | |
| SQ6 | | ✓ | | | |
| SQ7 | | ✓ | | ✓ | ✓ |
| SQ8 | | ✓ | | ✓ | ✓ |
| SQ9 | | ✓ | ✓ | ✓ | |

## Star Rating Rubric

Per `references/paper-rating-rubric.md`. Project-specific note: papers
that report **both** Torch Compile **and** TensorRT speed on a single
common hardware (e.g., Jetson Orin) get an evidence_strength bonus
(treat such papers as evidence_strength=3 even if other dimensions are
weaker), because they directly answer SQ5+SQ6 jointly.

## Bias Audit Thresholds

Defaults all 60%. One project-specific override:

| Bucket | Threshold | Notes |
|---|---|---|
| Architecture family | 50% | (stricter) — to ensure CNN / Transformer / hybrid all represented |
| Country | 60% | |
| Year | 60% | |
| Institution | 60% | |
| Venue type (preprint) | 60% | |
| Hardware tier | 60% | — to ensure both edge and server reported |

## Round 1 Source Plan

| Source | Keywords / queries | Cap |
|---|---|---|
| arXiv | `cat:cs.CV AND ti:"stereo matching"`, `cat:cs.CV AND abs:"stereo" AND abs:"foundation"`, `cat:cs.CV AND abs:"stereo" AND abs:"TensorRT"`, `cat:cs.CV AND ti:"foundation stereo"` | 30-50 candidates |
| OpenReview | CVPR/ICCV/ECCV stereo accepted papers 2023-2026 (peer-review status check) | 10-20 |
| DBLP | First-author stereo work for known authors (Lipson, Tonioni, Yang, Xu) | 5-15 |
| Semantic Scholar | Citation BFS from RAFT-Stereo, GMStereo, IGEV-Stereo, FoundationStereo | as needed |

## Pointers

- `paper_index.md` — paper rows
- `claims.jsonl` — claim contract
- `coverage_matrix.md` — sub-question × dimension
- `survey.md` — built only after audit-passed
- `audits/` — audit reports per round

## Changelog

| UTC | Change | Reason |
|---|---|---|
| 2026-05-01T00:30Z | Initial frame | Survey kickoff |
