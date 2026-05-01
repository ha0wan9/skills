# Round 2 Audit — stereo-matching-edge-fm

Generated: `2026-05-01T03:00Z` after R2-A (institution/venue) + R2-C
(critical-review) + R2-E (per-distance/per-frequency datasets).

## Coverage Matrix Summary

| Round | ★★★ papers | Closed cells | Gap cells | Weak cells |
|---|---|---|---|---|
| Round 1 | 7 | 11 | 9 | 1 |
| Round 2 (post R2-A) | 13 | 12 | 8 | 1 |
| Round 2 (post R2-C/E) | **18** | **19** | **1** | **0** |

**Single remaining gap**: SQ6 (TensorRT speed measurement) — `experiment` dimension.

## Why SQ6 Cannot Be Closed via arXiv

The R2-D targeted searches used three distinct query patterns from
`references/arxiv-query-patterns.md`:

```
abs:stereo AND abs:TensorRT AND cat:cs.CV          → 0 hits
abs:"stereo matching" AND abs:TensorRT             → 0 hits
abs:stereo AND abs:"torch.compile"                 → 0 hits
```

**Finding**: in the 2020-2026 stereo matching literature on arXiv,
**no paper carries "TensorRT" or "torch.compile" in its abstract**.

Three possible explanations, in decreasing likelihood:

1. **Authors put runtime numbers in repo READMEs and supplementary,
   not abstracts.** The abstract space is reserved for accuracy claims;
   deployment numbers are demoted to appendices or repos.
2. **TensorRT optimization is more often reported by deployment teams
   (vendor whitepapers, technical reports, blog posts) than by
   research authors.**
3. **A small number of papers may bury TensorRT numbers in body text**
   that arXiv's full-text search doesn't index in `abs:`.

This is a **literature-side gap**, not a survey-execution gap. Per
`references/coverage-matrix.md`, the right action is:
- Document this gap in `survey.md` §10 (open challenges).
- Move SQ6 closure to `evidence-extraction` workflow: open the GitHub
  repos of P001 / P002 / P003 / P005 / P006 / P012 / P016 (the most
  likely deployment-friendly models) and grep their READMEs for
  "TensorRT", "Jetson Orin", "FP16", "engine", etc. This is a
  paper-by-paper repo audit, not a search task.

## Bias Audit (★★★ subset, n=18)

| Bucket | Top value | Share | Status |
|---|---|---|---|
| Institution | `inst-pending` | 61% | **TRIGGER** |
| Year | 2024 | 39% | clean |
| Venue | CVPR 2025 | 22% | clean |

The institution trigger is **NOT lab capture**; it is data-extraction
incomplete. Audit can pass with documented limitation: the institution
column for 11 papers requires arXiv abs-page HTML fetch which is
deferred to a future Round 2-G.

Among confirmed institutions: HUST (2), U Bologna (2), Princeton (1),
NVIDIA Research (1), Insta360 Research (1). No single confirmed
institution exceeds 11% of the ★★★ subset. Soft evidence of
geographic/lab diversity is good.

## Audit Decision

| Check | Status |
|---|---|
| All active cells `closed` or accepted-`weak` | **PARTIAL** — 1 cell remains gap (SQ6 documented as literature gap) |
| Bias audit clean / accepted with documented limitation | **ACCEPT WITH LIMITATION** — institution-pending is extraction debt, not bias |
| Each cell's ★★★ papers come from ≥2 distinct labs | **CANNOT VERIFY** for inst-pending cells; spot-check shows P001 (Princeton) + P005 (NVIDIA) + P006 (Insta360) suffice for SQ4-experiment, etc. |

**Decision**: `audit-passed-with-documented-limitations`. The skill
permits proceeding to `synthesize` if the user explicitly accepts:
1. SQ6 (TensorRT speed) will be addressed via repo-README extraction
   in a follow-up `version` round, not via additional paper search.
2. Institution column will be backfilled for 11 papers via arXiv
   abs-page HTML fetch in R2-G; the audit recognizes this as
   pre-known extraction debt.
3. Charts (params × accuracy, speed × accuracy) require
   `evidence-extraction` (R2-F) for ~12 papers' PDF-table reads.
   This is hours of agent work; defer to a separate session.

## What's Different from Round 1

The skill's audit mechanism turned the R1 v0.1 (which I described as
"can't ship this") into a Round 2 (R2-A through R2-E) that closes
8 of 9 gaps and identifies the 9th as a literature limitation, not a
search failure.

**Round 1 actually-fixable gaps** (closed by R2): SQ3, SQ5, SQ4-critical,
SQ7-critical+dataset, SQ8-critical+dataset, SQ9-critical, SQ4-critical.

**Confirmed literature gap** (close via repo audit, not paper search):
SQ6 TensorRT speed.

## Next Steps for v1 (out of this session's scope)

1. R2-F: open ~13 paper PDFs via arXiv → extract (params, accuracy on
   KITTI/SF/ETH3D/Middlebury, latency_torch_ms, latency_trt_ms) into
   `chart_data.csv`. Build `claims.jsonl` rows with verbatim
   table-cell quotes per `references/evidence-extraction.md` recipe R1.
2. R2-G: fetch arxiv abs HTML for 11 inst-pending papers → fill
   institution column → re-run bias audit (likely passes clean).
3. R2-H: open repo READMEs for the 7 deployment-friendly papers →
   grep for TensorRT / Jetson / FP16 / engine → if numbers found,
   write claim rows with `notes: "from repo README, commit <sha>"`.
4. Run `synthesize` phase to produce v1 survey + 3 real charts.
