# Paper Rating Rubric

## Contents

- [Four Dimensions](#four-dimensions) — independent scores
- [Star Binning](#star-binning) — combining the four into ★/★★/★★★
- [Worked Examples](#worked-examples) — calibration cases

## Four Dimensions

Score each paper on these four dimensions independently. Do not let one
dimension contaminate another (e.g., a high-citation paper is not
automatically high relevance for your specific sub-question).

| Dimension | Score 0 | Score 1 | Score 2 | Score 3 |
|---|---|---|---|---|
| **Relevance** | wrong topic | adjacent topic | answers ≥1 sub-question loosely | answers ≥1 sub-question precisely |
| **Authority** | unknown authors / no venue | preprint, no track record | recognized lab or accepted at workshop | accepted at top venue (NeurIPS/ICLR/ICML/CVPR/ICCV/ECCV/AAAI/TMLR/NEJM/etc.) or seminal author |
| **Recency** | obsoleted by later work | older but unsuperseded | current generation | leading edge, drives the next generation |
| **Evidence Strength** | claims without experiments | small-scale experiments | reproducible mid-scale evidence | large-scale + multiple datasets + ablations + open-source |

The four dimensions sum to 0-12. The star binning compresses the sum,
weighted by relevance.

## Star Binning

```
weighted_score = relevance * 1.5 + authority + recency + evidence_strength
                              (max = 4.5 + 3 + 3 + 3 = 13.5)

★★★ : weighted_score >= 10  AND  relevance >= 2
★★  : weighted_score >= 6
★   : weighted_score >= 3
(unrated, drop) : weighted_score < 3
```

**Why relevance is weighted 1.5×**: a highly authoritative paper that
doesn't actually answer the sub-question is noise in this survey, even if
it's a great paper. The whole point of the survey is to answer the framed
question.

**Why the relevance gate at >= 2**: a paper can be a technical masterpiece
but only loosely answer the sub-question. ★★★ is reserved for papers that
answer something precisely.

## Worked Examples

(For an EEG foundation models survey)

| Paper | Relevance | Authority | Recency | Evidence | Sum | Weighted | Star |
|---|---|---|---|---|---|---|---|
| LaBraM (ICLR 2024, EEG FM) | 3 | 3 | 3 | 3 | 12 | 13.5 | **★★★** |
| BENDR (Frontiers 2022, EEG SSL) | 3 | 2 | 1 | 2 | 8 | 9.5 | **★★** |
| Generic SSL paper (no EEG) | 1 | 3 | 3 | 3 | 10 | 10.5 | **★★** (relevance gate) |
| Withdrawn arXiv preprint | 2 | 0 | 2 | 1 | 5 | 6.0 | **★★** |
| Tutorial blog post | 2 | 0 | 2 | 0 | 4 | 5.0 | **★** |

The third row shows the relevance gate in action: a strong general SSL
paper gets ★★ not ★★★ because its relevance to "EEG foundation models" is
loose. It should still go in the index as background, not as core
evidence.

## Notes

- Re-score after every Round N. New papers can shift recency (a 2024 paper
  may become "older but unsuperseded" once 2026 work appears).
- Authority is dimension-neutral: a clinical EEG paper from a medical
  journal can be Authority=3 even if the venue is not ML-canonical.
- Evidence strength includes data + ablations + open-source. A paper with
  no released code or weights caps at evidence=2 unless the experimental
  protocol is fully specified and reproducible from the description.
