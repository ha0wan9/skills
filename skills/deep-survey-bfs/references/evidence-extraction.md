# Evidence Extraction

## Contents

- [Why Extraction is a Phase, Not a Script](#why-extraction-is-a-phase-not-a-script)
- [Source Hierarchy By Claim Type](#source-hierarchy-by-claim-type) — different claims have different best sources
- [What to Extract](#what-to-extract) — fields per claim type
- [Extraction Recipes](#extraction-recipes) — six recipes, R1-R6
- [The `extract_paper_metrics.py` Helper](#the-extract_paper_metricspy-helper) — semi-automate PDF table surfacing
- [Verbatim Quote Discipline](#verbatim-quote-discipline)
- [Common Pitfalls](#common-pitfalls)

## Why Extraction is a Phase, Not a Script

The skill ships `arxiv_search.py` for keyword discovery and
`coverage_check.py` for matrix building, but **does not** ship a "parse
the paper PDF and extract the metric table" script. Reasons:

1. PDF tables are heterogeneous: one paper's KITTI 2015 column is named
   `D1-all`, another `D1`, another `Bad pixel rate`. A heuristic parser
   fails on edge cases that matter most.
2. Sub-claims need context: "59.6 EPE on SceneFlow" is meaningless
   without knowing whether it's clean / final / cleanpass / disparity at
   what max-disp setting.
3. The claims-discipline contract requires a verbatim quote or specific
   table reference. An auto-extractor that drops context invalidates the
   contract.

So extraction is an **agent task** in Round N, guided by this reference.
The extractor (you) reads each paper and writes claim rows.

## Source Hierarchy By Claim Type

The right primary source depends on what you're extracting. Picking the
wrong one causes wasted lookups: paper PDFs rarely contain TensorRT
latency, repo READMEs rarely contain ETH3D Bad-1 numbers.

### A. Accuracy / benchmark metrics (KITTI / Scene Flow / Middlebury / ETH3D)

Primary order:
1. **Paper PDF** (arXiv abs page → "Download PDF"). Authoritative
   for benchmark numbers; reported in tables.
2. **OpenReview** supplementary if available — sometimes contains
   ablations the camera-ready dropped.
3. **paperswithcode.com** if reachable (often redirects now); cross-
   checks paper number vs leaderboard ranking.
4. **GitHub repo README** as last fallback — sometimes the README
   reports newer numbers than the paper after author revisions.

### B. Parameter counts / model size

Primary order:
1. **Paper PDF**, but only if there's a comparison table with a
   `Params (M)` column. Many papers omit param counts entirely.
2. **GitHub repo README** — sometimes the README includes a model-zoo
   table with param counts per checkpoint.
3. **`print(model)` from the repo's load-checkpoint snippet** — last
   resort; record as confidence:medium since it's the user's own
   computation, not author-stated.

### C. Latency / FPS / TensorRT / Jetson / FP16 deployment

**Primary source is the GitHub repo README, NOT the paper.** Most
papers do not publish latency on common HW; deployment numbers live in
repo READMEs, supplementary docs, or vendor/project blog posts.

Primary order:
1. **GitHub repo README + repo `inference_*.py` / `benchmark.py`**
2. **Repo `readme_jetson.md` / `readme_deployment.md`** if present.
3. **Vendor whitepapers** (NVIDIA developer blog, Qualcomm AI hub)
   for canonical TRT timings of public models.
4. **Project page** (paper.first_page link → home page) sometimes
   has a "speed" section.
5. **Paper supplementary** as fallback.
6. **arXiv abstracts and main paper body** — almost never have these
   numbers; do not search here first.

### D. Architecture / pretraining / dataset claims

Primary order:
1. **Paper PDF** (Methods section, Implementation Details, Tables 1-2).
2. **Project page**.
3. **GitHub repo README**.

### E. Failure modes / limitations / negative results

Primary order:
1. **Paper PDF** Discussion / Limitations section.
2. **Paper supplementary** if present.
3. **OpenReview review thread** — reviewers often surface limitations
   the authors downplayed.
4. **Critical-review papers** that cite the model and discuss its
   weaknesses.

Always record which source you used in the claim row's `section` field.

## What to Extract

Per the chart-data CSV schema for stereo (similar shape applies to other
domains):

| Field | Source likely | Quote shape |
|---|---|---|
| `params_M` | paper Table 1 / repo `print(model)` summary | "12.3M parameters" |
| accuracy on a val set | paper Table 4 / paperswithcode | "D1-all 1.50%" or "EPE 0.74 on SceneFlow clean" |
| `latency_torch_ms` | paper Table 5 latency column / repo benchmark | "12 ms / frame on RTX 3090, 832×448" |
| `latency_trt_ms` | rare; check repo's `inference_trt.py` results | "8 ms / frame on Jetson Orin, FP16" |
| `hardware`, `precision` | paper experimental setup / repo README | "Jetson Orin Nano, FP16, batch 1" |

For each numeric field you write into `chart_data.csv`, write a matching
row in `claims.jsonl`:

```json
{"claim_id": "C015", "kind": "metric", "paper_id": "P005",
 "section": "Table 4, row 'FoundationStereo-base', column 'D1-all (KITTI 2015)'",
 "quote": "1.45",
 "notes": "test split, default settings",
 "confidence": "high"}
```

## Extraction Recipes

### R1. arXiv PDF metric extraction

1. Download `https://arxiv.org/pdf/<arxiv-id>` (use the latest version
   if the paper has been revised).
2. Open the PDF; search for the relevant val set name (KITTI 2015,
   SceneFlow, ETH3D, Middlebury) — usually a section heading or a table
   caption.
3. Read the relevant column **and** its caption to confirm metric name
   and split (test vs val, clean vs final, etc.).
4. Copy the cell value as a verbatim quote into the claim row;
   reference the table number and row in `section`.

### R2. paperswithcode benchmark lookup

1. Visit `https://paperswithcode.com/paper/<paper-slug>`.
2. Locate the benchmark you need (e.g., "Stereo Disparity Estimation on
   KITTI 2015 (Test)").
3. Find the row matching this paper's reported model.
4. The PWC entry cites which Table the number came from in the paper.
   Record both: PWC URL **and** the underlying paper Table reference.

### R3. OpenReview supplementary data

1. Visit `https://openreview.net/forum?id=<openreview-id>`.
2. Read accepted-version PDF and any supplementary file (often there's
   an appendix with full results).
3. Capture reviewer-asked clarifications from the discussion thread —
   sometimes authors disclose numbers there that didn't make the
   camera-ready.

### R4. Repo README + benchmark scripts

1. Open the GitHub repo (typically linked from the paper).
2. Look for `README.md` table of results, `benchmark/` or `scripts/`
   directory, and `evaluate.py` defaults.
3. Authors' README numbers often differ from the paper (revised after
   submission). Use the most recent README and record the commit hash
   you saw.

### R5. Latency on a specific HW (server class — RTX / A100)

For server-class latency where the paper itself reported a number:

1. The paper's Implementation Details / Experiments section.
2. The repo's `inference_*.py` or `benchmark.py` scripts.
3. The paper's comparison table's "Run-time" / "FPS" column.

If the paper does not specify hardware for a runtime number, mark the
quote `confidence: medium` and add a note "HW unspecified in source".
Cross-paper runtime comparisons require same HW; otherwise note the
mismatch.

### R6. Edge / TensorRT / Jetson / Mobile latency hunt

**Most adversarial extraction case** — most papers do not publish edge
or TRT latency. The right pivot order:

1. **Repo README first.** Search for `TensorRT`, `TRT`, `ONNX`,
   `Jetson`, `Orin`, `Nano`, `FP16`, `INT8`, `engine`, `trtexec`.
   Authors often add deployment notes after camera-ready and document
   them only in the repo. Quote the README verbatim with the commit
   SHA.
2. **Repo dedicated deployment doc** (e.g. `readme_jetson.md`,
   `deployment.md`, `docs/deploy.md`).
3. **Project page** (linked from paper's first page) — sometimes
   carries a "Speed" or "Runtime" panel.
4. **Vendor whitepaper / developer blog** (NVIDIA developer blog,
   Qualcomm AI Hub, Intel OpenVINO model zoo) — they sometimes
   publish canonical TRT timings of academic models.
5. **GitHub Issues** in the repo: search for "Jetson", "TensorRT",
   "FPS", "latency", "speed". Authors sometimes answer with numbers
   they didn't publish.
6. **Paper supplementary** — last resort; rarely has it.

If the claim is "X% faster" or "real-time" without an absolute number,
quote it verbatim with `confidence: low` and `notes: "relative claim,
no absolute ms"`. **Do not derive an absolute number** by combining
the relative claim with a paper-side latency unless the two are on the
same hardware tier.

If after this pivot a model has no TRT/edge data, that is a real
finding — record it in the survey's open-challenges section as
"deployment data not disclosed" rather than fabricating.

## The `extract_paper_metrics.py` Helper

For Recipes R1, R2, R5 the agent needs to download a paper PDF, run
`pdftotext -layout`, then locate candidate metric tables. The skill
ships `scripts/extract_paper_metrics.py` to compress this into one
command.

```bash
# By arXiv ID — auto-downloads, caches under /tmp/deep-survey-pdf-cache/
python3 skills/deep-survey-bfs/scripts/extract_paper_metrics.py 2303.06615

# Narrow to a specific metric domain
python3 .../extract_paper_metrics.py 2303.06615 --metric "KITTI|EPE|Bad" --max-hits 4

# Filter to candidates near table-header lines only
python3 .../extract_paper_metrics.py 2303.06615 --tables-only

# Direct PDF path
python3 .../extract_paper_metrics.py /tmp/foundation.pdf
```

The script:
- Caches downloaded PDFs and their `pdftotext` output under
  `/tmp/deep-survey-pdf-cache/` (override with `DEEP_SURVEY_PDF_CACHE`
  env var).
- Prefers candidates that are within 5 lines of a Table header
  signature.
- Outputs windowed line-numbered context around each candidate so the
  agent can quote-verify before writing the claim row.
- Does not decide which number is "the" answer; the agent must read
  each window and select the right table cell.

Use it for Recipes R1 (paper PDF), R2 (paperswithcode redirect to PDF
fallback), and R5 (paper-side runtime). For Recipe R6 (edge / TRT) the
helper does not apply — pivot to repo README via WebFetch instead.

Time savings: extraction that previously took 90-180 seconds per
paper (download + pdftotext + manual grep + table reading) drops to
20-40 seconds per paper.

## Verbatim Quote Discipline

The `quote` field in `claims.jsonl` must be the literal text from the
source, not a paraphrase. Acceptable transformations:

- Trim surrounding whitespace.
- Replace LaTeX math markers (`$1.50\%$`) with the numeric value plus a
  unit (`"1.50%"`).
- Concatenate split lines (PDF copy/paste artifacts).

Not acceptable:

- Rounding the number ("1.5%" when the paper says "1.50%").
- Combining two cells into one number.
- Translating units without recording the original.

If the original quote is awkward (a long table caption), put the cell
identifier in `section` and the cell value in `quote`. The
`section` field is for the locator; the `quote` is for the value.

## Common Pitfalls

- **KITTI 2015 has multiple metrics**: D1-all, D1-bg, D1-fg, EPE.
  Record which one. The cell label in the paper's Table is usually the
  cleanest source.
- **SceneFlow has two splits**: cleanpass / finalpass, and disparity at
  multiple max-disp settings. Always note which.
- **Middlebury**: bad-2 vs bad-1 vs avgerr. Different papers report
  different ones. Record exactly which.
- **Latency without batch size or resolution** is meaningless. Always
  capture both. "12 ms" alone is uninformative.
- **TensorRT precision matters**: FP32 vs FP16 vs INT8 give factor-2 to
  factor-4 differences. Record precision.
- **Published version vs README mismatch**: when in doubt, prefer the
  published paper number with `notes: 'paper Table N'`, but flag if the
  repo README has a higher number — this often indicates an unpublished
  improvement that may show up in the next paper version.
