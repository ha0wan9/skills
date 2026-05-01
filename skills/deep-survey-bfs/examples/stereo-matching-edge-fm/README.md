# Stereo Matching for Edge & Foundation Models (2020-2026)

> **Skill**: [`deep-survey-bfs`](../../) · **Survey version**: v1.2 · **Survey date**: 2026-05-01
> **Coverage**: 26 papers indexed · 18 ★★★ · 67 grounded claims · 9 sub-questions (8 closed)
> **Render**: [`artifacts/survey.html`](artifacts/survey.html) — single-file interactive HTML (~99 KB)

Reference example produced end-to-end by the `deep-survey-bfs` skill.

Research question: *How do edge-deployable and foundation-model stereo
matching approaches compare in 2020-2026, and which works best on which
data type?*

## Layout

| File | Role |
|---|---|
| `index.md` | Frame: research question, sub-questions, scope table |
| `paper_index.md` | 26 indexed papers (18 ★★★, 7 ★★, 1 survey); Round 2-A confirmed |
| `claims.jsonl` | 67 verbatim-quoted claims with section/page anchors |
| `coverage_matrix.md` | Sub-question × evidence-dimension gap audit |
| `survey.md` | v1.2 synthesised survey (14 sections incl. §3.5 Datasets, §11 Key Research Teams, §14 Reproducibility tier) |
| `citations.tsv` | Within-survey citation edges (~40 edges, 7 relation types) |
| `clusters.tsv` | Paper → architecture cluster for the lineage view |
| `loop_state.json` | `/loop` self-pacing state across 8+4 iterations |
| `audits/r3-progress.jsonl` | Per-iteration progress log |
| `artifacts/survey.html` | Single-file interactive HTML render (TOC, tooltips, search, Plotly, Mermaid, dark mode) |
| `artifacts/0[123]_*.png` | Static chart fallbacks |
| `artifacts/chart_data.csv` | Plotly-bound chart data |
| `artifacts/generate_charts.py` | Static chart regeneration script |

## Reproducing

```
# (Re)render the HTML
python3 ~/.claude/skills/deep-survey-bfs/scripts/render_html.py . artifacts/survey.html \
    --title "Stereo Matching for Edge & Foundation Models (2020-2026)" \
    --include-citation-graphs lineage,critique,temporal

# Validate claims
python3 ~/.claude/skills/deep-survey-bfs/scripts/claims_validate.py claims.jsonl survey.md

# Bias audit (auto-promotes confirmed institutions)
python3 ~/.claude/skills/deep-survey-bfs/scripts/bias_audit.py paper_index.md

# Render citation graph (any of: lineage, cites, critique, temporal, all)
python3 ~/.claude/skills/deep-survey-bfs/scripts/citation_graph.py \
    citations.tsv paper_index.md --clusters clusters.tsv --view lineage
```

## Open frontier

- SQ6 TensorRT latency closure requires reaching out to repo authors
  (RAFT-Stereo, IGEV-Stereo, FoundationStereo, Stereo-Anywhere) — the
  numbers are not in publication norm for this field
- 12 of 18 ★★★ papers' reproducibility tier annotations remain `pending`
  in `paper_index.md` (v1.2 covers 6 flagships; full extension is the
  v1.3 task)
