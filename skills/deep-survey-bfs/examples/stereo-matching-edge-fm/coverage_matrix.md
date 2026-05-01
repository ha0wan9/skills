# Coverage Matrix — stereo-matching-edge-fm

Generated: `2026-05-01T00:50Z` after Round 1.

## Cell Map (★★★ papers only)

| Sub-question | theory | experiment | survey | critical-review | dataset |
|---|---|---|---|---|---|
| SQ1 (CNN models) | P001, P002 | P001, P002 | N/A | N/A | N/A |
| SQ2 (Transformer models) | P001, P004 | P001, P004 | N/A | N/A | N/A |
| SQ3 (hybrid / SSM) | — | — | N/A | N/A | N/A |
| SQ4 (foundation-style) | P005, P006, P007 | P005, P006, P007 | N/A | — | N/A |
| SQ5 (Torch Compile speed) | N/A | — | N/A | N/A | N/A |
| SQ6 (TensorRT speed) | N/A | — | N/A | N/A | N/A |
| SQ7 (per-distance accuracy) | N/A | — | N/A | — | — |
| SQ8 (per-frequency accuracy) | N/A | P004 | N/A | — | — |
| SQ9 (failure modes) | N/A | — | P017 | — | N/A |

## Status Per Cell

| Sub-question | Dimension | State | Target | Search strategy |
|---|---|---|---|---|
| SQ3 | theory + experiment | **gap** | hybrid CNN+Transformer / SSM-based stereo papers | Cite-trace from P001/P002 forward citations on Semantic Scholar; targeted query "stereo+transformer+hybrid" |
| SQ4 | critical-review | **gap** | failure analysis of foundation stereo models | Search "stereo foundation model limitations" + reviews; check Stereo Anything paper for self-criticism section |
| SQ5 | experiment | **gap** | papers reporting Torch Compile latency | Targeted query `abs:"torch.compile"+stereo`; manually check IGEV/RAFT-Stereo repos for benchmarks |
| SQ6 | experiment | **gap** | papers reporting TensorRT-engine latency | Targeted query `abs:TensorRT+stereo`; check StereoVoxelNet (P016) for Jetson numbers; vendor whitepapers |
| SQ7 | experiment + critical-review + dataset | **gap** | per-distance / per-depth-bin accuracy breakdowns | Booster Dataset, FoundationStereo's reported zero-shot tables; reviews of KITTI 2015 D1-bg vs D1-fg |
| SQ8 | experiment + critical-review + dataset | **weak** | only P004 covers the dimension; need ≥1 more lab | Cite-trace from P004 forward; query `abs:"low-texture"+stereo` |
| SQ9 | critical-review + experiment | **gap** | systematic failure-mode papers / negative-result studies | Query Mayo-Clinic-style critical reviews; check P017 survey's limitation section |

## Bias Audit (★★★ subset, n=7)

Architecture family (rubric override threshold 50%):
  - Foundation-style: 3/7 (43%)  ✓ ok
  - Recurrent (RAFT-style): 2/7 (29%)
  - CNN+freq-attention: 1/7 (14%)
  - Survey: 1/7 (14%)

Year (threshold 60%):
  - 2024: 2/7 (29%)
  - 2025: 2/7 (29%)
  - 2023: 1/7 (14%)
  - 2021: 1/7 (14%)
  - 2024 (survey): 1/7 (14%)
  ✓ Distribution clean.

Country / Institution / Venue type:
  - **Cannot audit** until institution column is populated in
    paper_index.md. Round 2 must complete this before audit can pass.

## Round 2 Task List

```
- [ ] R2-A: Fill institution / venue confirmation for all 20 papers via
  OpenReview + DBLP lookup (audit precondition)
- [ ] R2-B: Find ≥3 hybrid (CNN+Transformer) and ≥1 SSM-based stereo
  papers (currently SQ3 is empty in cell map; only P020 is SSM and it's
  not stereo-primary)
- [ ] R2-C: Find ≥1 critical-review paper for SQ4 (foundation stereo
  limitations); also resolve SQ9 (failure-modes systematic study)
- [ ] R2-D: Find ≥3 papers reporting Torch Compile and/or TensorRT
  latency on common HW (Jetson Orin / RTX 3090). This is the chart-data
  bottleneck — without it, SQ5/SQ6 cannot close
- [ ] R2-E: Find ≥1 per-depth-bin accuracy breakdown paper (SQ7) and
  ≥1 more per-frequency paper (SQ8 weak)
- [ ] R2-F: Open the abstracts of all 20 papers to extract reported
  parameter counts and accuracy figures (currently the index has rough
  stars only; chart generation needs concrete (param, accuracy, latency)
  triples)
```

## Audit Decision

- [ ] All active cells `closed` or accepted-`weak`         → **NO**
- [ ] Bias audit clean / accepted with documented limitation  → **PARTIAL** (institution unaudited)
- [ ] Each cell's ★★★ papers come from ≥2 distinct labs       → **CANNOT VERIFY** (institutions not extracted)

→ **audit-needs-roundN** (5 distinct gaps, 1 weak cell, 1 audit precondition)
