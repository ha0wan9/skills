# Paper Index — <survey-id>

| ID | ArXiv | Title (short) | First author | Inst | Year | Venue | Sub-questions | Dimensions | Stars | Round | Status | Repro | One-line note |
|----|-------|---------------|--------------|------|------|-------|---------------|------------|-------|-------|--------|-------|---------------|
| P001 | 2101.12037 | <title> | <Last F.> | <inst> | 2021 | Frontiers 2022 | SQ1, SQ3 | theory, experiment | ★★★ | R1 | confirmed | oss/recipe:complete/issues:clean/quality:strong/3p:confirmed | <note> |

> Conventions:
> - **ID**: assigned in append order; never renumbered.
> - **ArXiv**: ID only (no version suffix); empty if not on arXiv.
> - **Title**: shortened to fit; full title in the deep-dive section.
> - **Inst**: shortened lab/institution; "MIT", "Shanghai Jiao Tong", etc.
>   Use `inst-pending` when extraction is deferred. To enable the **country
>   bias audit** without adding a column, append a country tag in parentheses,
>   e.g. `Tsinghua (CN)`, `Meta AI Paris (FR)`; `scripts/bias_audit.py` reads
>   it (and falls back to a small known-institution map). Codes: US/UK/FR/DE/
>   CN/JP/CH/NL/CA/IL/KR/IT/AU/ES.
> - **(optional) Country / Method route columns**: add a `Country` column for
>   explicit country auditing, and/or a `Method route` column (e.g.
>   `goal-driven`, `spiking`, `predictive-coding`, `dynamical`) to enable the
>   method-route bias audit. Both are read by `bias_audit.py` when present;
>   absent, the audit reports them as data gaps rather than guessing.
> - **Year**: arXiv first-submitted year if not yet at venue; venue year
>   once accepted. Both are acceptable; the cell records what's known.
> - **Venue**: "preprint" until accepted; otherwise venue and year. Update
>   on every Round N if status changes.
> - **Sub-questions**: comma-separated SQ IDs from `index.md`.
> - **Dimensions**: comma-separated from {theory, experiment, survey,
>   critical-review, dataset}.
> - **Stars**: ★ / ★★ / ★★★ per `paper-rating-rubric.md`.
> - **Round**: R1 / R2 / R3 ... — when this paper entered the index.
> - **Status**: `confirmed` (all author/venue/inst fields verified
>   from arxiv API or HTML), `partial` (some fields verified, others
>   are extraction-pending such as `inst-pending`), or `pending` (only
>   title + arxiv ID populated). The bias audit only counts
>   `confirmed` rows by default — see `bias-audit.md`.
> - **Repro**: 5-tag reproducibility summary per
>   `references/reproducibility-assessment.md`, format
>   `<release>/<recipe>/<issues>/<quality>/<3p>` with values:
>   - release: `oss` (open-source) | `ow` (open-weights) |
>     `io` (inference-only) | `cl` (closed)
>   - recipe: `complete` | `partial` | `absent`
>   - issues: `clean` | `mixed` | `stale` | `unmaintained`
>   - quality: `strong` | `adequate` | `weak` | `unverified`
>   - 3p: `confirmed` | `partial` | `failed` | `unverified`
>   Use `pending` as a placeholder until the assessment runs. The
>   synthesis prose maps the row to a Tier R1-R4 (see reference).
> - **One-line note**: a single distinguishing fact (e.g., "first 1B+
>   parameter EEG FM").
