# HTML Export

A finished `survey.md` is durable but not browseable. The `render_html.py`
pipeline produces a single self-contained HTML file with the affordances
of a small static-site app — sticky TOC, scroll-spy, in-line citation
tooltips, search across papers/claims/sections, sortable tables, and
client-side renders for both Mermaid graphs and the Plotly charts that
replace the static PNG outputs.

The output is **one file**. It mails, archives, and uploads as a single
attachment. That property is intentional: surveys are read by people who
won't run a web server.

## Contents

- [Requirements](#requirements)
- [What the viewer does](#what-the-viewer-does)
- [How to invoke](#how-to-invoke)
- [Inputs read](#inputs-read)
- [What gets transformed in the markdown](#what-gets-transformed)
- [Chart specs](#chart-specs)
- [CDN vs fully-offline](#cdn-vs-fully-offline)
- [Customisation](#customisation)
- [Anti-patterns](#anti-patterns)

## Requirements

`render_html.py` is the only script in this skill with a non-stdlib runtime
dependency. Verify before invocation:

```bash
python3 -c "import markdown; print(markdown.__version__)"
```

If this fails, install:

```bash
pip install --user markdown
# or, in a project venv:
python3 -m pip install markdown
```

Tested with `markdown >= 3.4`. The script `sys.exit(2)` on ImportError with
this exact remediation in the error message; if you see that, install and
re-run.

Three browser-side libraries load at runtime: `mermaid`, `plotly.js`,
`flexsearch`. By default they CDN-load (~1.5 MB over the wire). For
fully-offline use:

```bash
mkdir -p libs
curl -L -o libs/mermaid.min.js     https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js
curl -L -o libs/plotly.min.js      https://cdn.plot.ly/plotly-2.35.2.min.js
curl -L -o libs/flexsearch.min.js  https://cdn.jsdelivr.net/npm/flexsearch@0.7.43/dist/flexsearch.bundle.min.js
python3 skill/scripts/render_html.py SURVEY_DIR survey.html --fully-offline --libs-dir libs
```

This inlines the libs and produces a ~5 MB self-contained file.

## What the viewer does

| Feature | Mechanism |
|---|---|
| Sticky TOC + scroll-spy | rendered from `[TOC]` extension; client JS toggles `.active` on the nearest anchor |
| `(P###)` tooltip | `paper_index.md` row → JSON; tooltip card on hover |
| `(C###)` tooltip | `claims.jsonl` row → JSON; shows verbatim quote, paper, section, kind, confidence |
| Search box | FlexSearch index over paper titles + claim quotes + section headings; regex fallback when CDN blocked |
| Sortable tables | every `<th>` becomes click-sortable (numeric or string sort) |
| Plotly charts | `<img>` tags or `<code>NN_*.png</code>` mentions become `<div class="plotly-chart" data-chart="NN">`; spec injected from `chart_specs.json` (or the renderer's defaults) |
| Mermaid diagrams | fenced ``` ```mermaid ``` blocks in `survey.md` AND auto-injected citation graphs |
| Dark / light mode | persisted in `localStorage`; Plotly + Mermaid re-themed on toggle |
| Print stylesheet | TOC and tooltip suppressed; chart blocks page-break-avoid |

## How to invoke

```
python3 skill/scripts/render_html.py SURVEY_DIR OUT_HTML \\
    [--title "<title>"] \\
    [--include-citation-graphs lineage,critique,temporal] \\
    [--fully-offline --libs-dir <dir>]
```

`SURVEY_DIR` must contain at minimum `survey.md` and `paper_index.md`.

The renderer is idempotent — re-running overwrites the output without
side effects on the source.

## Inputs read

| File | Required | Used for |
|---|---|---|
| `survey.md` | yes | body content; H2/H3 → TOC |
| `paper_index.md` | yes | paper tooltips; expects standard schema with `ID / Title / Year / Venue / Stars / Repro` columns |
| `claims.jsonl` | optional | claim tooltips; missing `quote` falls back to `(no quote)` |
| `artifacts/chart_data.csv` | optional | Plotly trace data; expected columns include `paper_id`, `model`, plus any axis fields named in `chart_specs` |
| `chart_specs.json` | optional | per-chart axis bindings + labels; absent → default specs for `01/02/03` |
| `citations.tsv` + `clusters.tsv` | optional | only when `--include-citation-graphs` is set |

## What gets transformed in the markdown

| Source markdown | Rendered HTML | Why |
|---|---|---|
| `(P002)` | `<span class="paper-ref" data-id="P002">P002</span>` | tooltip target |
| `(C015)` | `<span class="claim-ref" data-id="C015">C015</span>` | tooltip target |
| ``` ```mermaid ... ``` ``` | `<div class="mermaid">...</div>` | client-side rendering |
| `<img src="artifacts/01_*.png">` | `<div class="plotly-chart" data-chart="01">` | interactive chart |
| paragraph mentioning `<code>artifacts/01_*.png</code>` | the whole paragraph is replaced by the chart placeholder; the next paragraph in the source serves as the caption | accommodates surveys that name chart files in prose without `![](path)` |

References to unknown paper or claim IDs are left as plain text — the
renderer never invents tooltips for nonexistent rows.

## Chart specs

`chart_specs.json` (in the survey directory) overrides the defaults:

```json
{
  "01": {
    "title": "Params (M) vs zero-shot Mean ↓",
    "x": "params_M", "y": "accuracy_inv",
    "x_label": "Params (M)", "y_label": "Mean (lower is better)",
    "x_type": "log",
    "filter": "val_set=zero-shot Mean (P007 Tab II)"
  }
}
```

Fields:
- `x`, `y` are CSV column names parsed as floats; rows with non-numeric
  values for either are dropped silently
- `x_type` / `y_type` accept `linear` or `log`
- `filter` is a comma-list of `key=value` constraints; only matching
  rows are plotted (lets one CSV feed multiple charts)
- `color` overrides the default accent

The defaults assume the stereo-matching layout (`params_M`,
`latency_torch_ms`, `latency_trt_ms`). For other domains supply
`chart_specs.json`.

## CDN vs fully-offline

The default loads three libraries from CDN: Mermaid, Plotly, FlexSearch.
Total over-the-wire weight is ~1.5 MB. Without the CDN libraries the
viewer still renders prose, tables, tooltips, and TOC — only the chart
and graph + search-as-you-type features degrade.

`--fully-offline --libs-dir <dir>` inlines the libraries from local
copies; the resulting HTML is ~5 MB and works without network.

## Customisation

- **Theme**: edit `templates/html/styles.css`. Only CSS variables in
  `:root` and `[data-theme="dark"]` need changing for a colour rebrand.
- **Layout**: `templates/html/survey.html.tpl` is the shell. Topbar,
  sidebar, content column, tooltip overlay are explicit slots.
- **JS hooks**: `templates/html/app.js` is one IIFE; functions for
  tooltip, search, scroll-spy, table sort, Plotly, Mermaid are
  separable. Replace any one without touching the others.
- **Skip a feature**: pass `--no-search` / `--no-charts` (not implemented
  yet — open issue if needed).

## Anti-patterns

- **Treating the HTML as primary source**. The HTML is a render. All
  edits go to `survey.md` + `claims.jsonl`. Re-render to update.
- **Adding interactivity in `survey.md`**. Don't embed `<script>` /
  `<iframe>` / form elements in the markdown — the renderer doesn't
  sanitize HTML pass-through, but the resulting file becomes
  un-archivable and forks brittle.
- **Putting paper-specific facts in `chart_specs.json`**. Charts read
  data; specs read which columns to show. Putting "FoundationStereo
  used A100" in a spec is the wrong layer — it belongs in `paper_index`
  or `claims.jsonl`.
- **Generating multiple HTML files for "different audiences"**. The
  TOC is the segmentation tool. One `survey.html` with all sections
  scales further than three files that drift out of sync.
