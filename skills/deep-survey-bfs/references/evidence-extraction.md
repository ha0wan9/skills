# Evidence Extraction

## Contents

- [Why Extraction is a Phase, Not a Script](#why-extraction-is-a-phase-not-a-script)
- [Source Hierarchy](#source-hierarchy) — paper PDF / paperswithcode / OpenReview / repo README
- [What to Extract](#what-to-extract) — fields per claim type
- [Extraction Recipes](#extraction-recipes)
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

## Source Hierarchy

For a paper P00X, in this priority order:

1. **Paper PDF** (arXiv abs page → "Download PDF"). The authoritative
   numbers are in the paper's tables. Quote directly.
2. **paperswithcode.com page** for the paper. Aggregates KITTI 2015 /
   SceneFlow / ETH3D / Middlebury rankings with citations to the paper's
   table. Useful when the paper has multiple versions and PWC indexes
   the canonical one.
3. **OpenReview** (if a venue submission exists). Includes
   supplementary material, reviewer-asked clarifications, and
   sometimes additional ablations the camera-ready paper omits.
4. **GitHub repo README + checkpoints page**. Often has the exact
   numbers the README author tested, including the latency tables that
   the camera-ready paper compressed.
5. **Author's project page** (linked from the paper's first page).

Use the highest-priority source that has the specific number you need.
Always record which source you used in the claim row.

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

### R5. Latency on a specific HW

This is the hardest: most papers don't publish HW-specific latency.
Where to check:

1. The paper's "deployment" / "speed" section if it has one.
2. The repo's `inference_*.py` or `benchmark.py` scripts (sometimes
   include reference numbers).
3. Issues / discussions on GitHub: search for "Jetson", "TensorRT",
   "FPS", "latency".
4. Vendor whitepapers (NVIDIA, Qualcomm) sometimes benchmark public
   models on their HW.
5. If a paper claims "real-time on Jetson" without numbers, treat the
   claim as `confidence: low` and quote the unsupported claim
   verbatim, do not infer a number.

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
