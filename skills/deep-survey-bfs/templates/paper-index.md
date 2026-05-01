# Paper Index — <survey-id>

| ID | ArXiv | Title (short) | First author | Inst | Year | Venue | Sub-questions | Dimensions | Stars | Round | Status | One-line note |
|----|-------|---------------|--------------|------|------|-------|---------------|------------|-------|-------|--------|---------------|
| P001 | 2101.12037 | <title> | <Last F.> | <inst> | 2021 | Frontiers 2022 | SQ1, SQ3 | theory, experiment | ★★★ | R1 | confirmed | <note> |

> Conventions:
> - **ID**: assigned in append order; never renumbered.
> - **ArXiv**: ID only (no version suffix); empty if not on arXiv.
> - **Title**: shortened to fit; full title in the deep-dive section.
> - **Inst**: shortened lab/institution; "MIT", "Shanghai Jiao Tong", etc.
>   Use `inst-pending` when extraction is deferred.
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
> - **One-line note**: a single distinguishing fact (e.g., "first 1B+
>   parameter EEG FM").
