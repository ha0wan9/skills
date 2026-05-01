# Phase: synthesize

Use only after `audit` has returned `audit-passed`. Synthesis is the only
phase that produces user-facing prose; everything earlier is structured
artifacts.

## Steps

1. Read `index.md`, `paper_index.md`, `coverage_matrix.md`. Load
   `references/claims-discipline.md`, `references/evidence-extraction.md`,
   and `references/taxonomy-revision.md`.

2. Build `claims.jsonl` first. For every fact you intend to assert in
   prose, write a row. The evidence-extraction reference defines the
   source hierarchy (paper PDF → paperswithcode → OpenReview supp →
   repo README → project page) and per-field extraction recipes for
   metric / latency / parameter-count claims.
   ```json
   {"claim_id": "C001", "paper_id": "P004",
    "section": "Table 2", "quote": "...verbatim...",
    "kind": "metric|architecture|dataset|finding"}
   ```
   The validator script enforces that every claim row has
   non-empty paper_id, section, and quote (or table/figure reference).

3. Scaffold `survey.md` from `templates/survey-skeleton.md`. Required
   sections (the skeleton enforces them):
   - §1 Research question + scope (re-quote from `index.md`)
   - §2 Domain background (only if the topic needs it; otherwise inline)
   - §3 Taxonomy + timeline (multi-axis if applicable; see taxonomy-revision)
   - **§4 Datasets and benchmarks** — load
     `references/datasets-section.md`. Build the canonical-vs-emergent
     classification, the adoption heatmap, and the dataset-gaps list
     BEFORE writing the method-route comparison. This is mandatory for
     any survey involving performance comparison; placing it before
     §5 grounds the reader's evaluation lens.
   - §5 Method-route comparison table (rows: papers; columns: critical
     attributes; mark unknowns explicitly)
   - §6 Per-paper deep-dives (one subsection per ★★★ paper, optional for
     ★★; annotate with reproducibility Tier per
     `references/reproducibility-assessment.md`)
   - §7 Downstream applications (if applicable)
   - §8 Cross-cutting analysis (multimodal, scaling, deployment)
   - §9 Key research teams (clusters from the index)
   - §10 Open challenges (must reference the critical-review dimension)
   - §11 Frontiers / future directions
   - §12 Direct Q&A back to original research question
   - §13 Multi-tier reading list (entry / deep / critical / overview)
   - §14 Reproducibility tier (when ★★★ papers vary in code release)

4. Write each section by pulling from claims.jsonl. Do not write a
   sentence whose key fact is not in claims.jsonl. Reference paper IDs
   inline: `(P004)`, `(P004, Liu et al. 2026)`.

5. Build the multi-axis taxonomy: at least one primary axis (usually
   method route) and one secondary axis (output modality / deployment
   target / scale tier — pick whichever orthogonally cuts the field).

6. Build the timeline. Group by year; mark milestone papers with `★`
   inline. The timeline should make the field's reframing moments
   visible (when did the dominant approach shift?).

7. **Run reproducibility assessment** on every ★★★ paper before
   writing per-paper deep-dives. Load
   `references/reproducibility-assessment.md` and apply the 5-question
   rubric (release / recipe / issues / quality / 3p reproduction).
   Populate the `Repro` column in `paper_index.md` and map each paper
   to a Tier R1-R4. The deep-dive subsections in §5 must annotate the
   tier (e.g., "IGEV-Stereo (P002) [R1]"). When citing accuracy /
   latency / param numbers in §4 / §6 / §8, papers in Tier R3 / R4
   require an explicit reproducibility caveat in the surrounding prose.

8. Build the multi-tier reading list:
   - Entry tier (3-5 papers, suggested reading order, time estimate)
   - Deep tier (per route)
   - Critical tier (limitations, negative results)
   - Overview tier (other surveys; for cross-checking)

8. Run `python3 skill/scripts/claims_validate.py claims.jsonl
   survey.md` to confirm every assertion in `survey.md` traces to a
   claim row.

9. Run `python3 skill/scripts/synthesize_self_check.py survey.md
   paper_index.md` to confirm the skeleton's structural requirements
   are met:
   - §4 Datasets exists and comes before §5 method comparison
   - §13 Reading list contains all four tiers (Entry / Deep /
     Critical / Overview)
   - §14 Reproducibility tier is present when ★★★ papers have varied
     code-release status (some 'pending', some described)
   - Section IDs are monotonic (no v1.x supplements appended out of
     order; if out-of-order, run a renumber pass per `05-version.md`)
   Self-check failure means the survey is not ready to ship — fix
   structure before handing off.

10. **(Optional) Render citation graph(s) into the survey.** Load
    `references/citation-graph.md`. Populate `citations.tsv` (edge
    list with `from / to / relation / evidence`) and optionally
    `clusters.tsv` (paper → architecture/route cluster). Then render
    one to three Mermaid figures via:
    ```
    python3 skill/scripts/citation_graph.py citations.tsv \
        paper_index.md --clusters clusters.tsv \
        --view {lineage|cites|critique|temporal|all} \
        [--filter-stars 3]
    ```
    Recommended placements: `lineage` figure in §3 (route inheritance),
    `critique` figure in §10 (open-challenges attack graph), and a
    second `lineage` in §11 if same-team clustering is the dominant
    finding. Skip this step when the survey is conceptual / non-
    comparative.

## Synthesis Discipline

- **Do not introduce new facts during synthesis.** If a claim is needed
  but not in claims.jsonl, that means the underlying paper is missing —
  trigger Round N, do not invent.
- **Mark unknowns visibly.** "Not disclosed" / "未披露" / "N/A" cells in
  comparison tables are required when authoritative info is unavailable.
  Never speculate to fill a cell.
- **Per-paper deep-dives must include a "why it matters" line** that
  ties to a sub-question, not just a method description.
- **Open challenges must cite critical-review papers.** Authors'
  enthusiasm in their own paper is not a challenge source.

## Hand Off

Set status to `synthesized`. Output the path to `survey.md`. Recommend
running `version` if new evidence is expected to arrive (long-running
topics). Run `audit` instead if the user reports a missing perspective.
