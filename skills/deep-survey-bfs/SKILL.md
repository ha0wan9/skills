---
name: deep-survey-bfs
description: >-
  Conduct rigorous breadth-first literature surveys: decompose the question
  into sub-questions, run a broad multi-source search (arXiv, OpenReview, DBLP,
  Semantic Scholar), score papers on a 4-dimension rubric, gate completeness
  with a sub-question x dimension coverage matrix, fill gaps via targeted
  rounds, synthesize multi-axis taxonomies, timelines, and per-paper
  deep-dives, audit source/institution/year bias, render Mermaid citation
  graphs, and export a single self-contained interactive HTML report,
  versioned incrementally as new evidence arrives. Use when the user asks for
  a literature review, comprehensive survey, "research X for me", or to
  expand/audit an existing survey.
metadata: {version: 1.2.0, compat: [claude-code, codex], published: [claude-marketplace]}
---

# Deep Survey (BFS)

> **Runtimes:** Claude Code · Codex · OpenClaw &nbsp;|&nbsp; **Published:** Claude Marketplace

Thin router for breadth-first literature surveys. Resolve the phase, resolve
`survey-id`, then load only the procedure file you need. Survey artifacts live
under `.research/surveys/<survey-id>/` by default; a project adapter may
override the root.

**Depends on `project-meta`** (the upstream/root skill) for the canonical Task
Dispatch paradigm. This skill's `references/multi-agent-dispatch.md` is a domain
specialization with a self-contained floor, so it still runs if project-meta is
not installed; when both are present, project-meta is canonical.

`survey-id` rules: kebab-case, 2-5 tokens, no dates, no version suffixes,
explicit about the topic. Good: `eeg-foundation-models`,
`stereo-matching-edge`, `mamba-vs-transformer-vision`. Bad: `survey1`,
`my-research-v2`, `stuff`.

## Core Mechanism: BFS with Coverage Gates

The skill enforces breadth-first exploration with hard completeness gates,
inspired by PRISMA scoping reviews adapted for LLM workflows:

1. **Frame** decomposes the research question into 6-12 sub-questions.
2. **Round 1** does a broad multi-source search; every paper gets a 4-dimension
   score → star rating.
3. **Gap Audit** builds a sub-question × dimension coverage matrix. The skill
   does not proceed to synthesis until every active cell has ≥1 ★★★ paper.
4. **Round N** runs targeted searches against gaps; loops back to audit.
5. **Synthesize** produces multi-axis taxonomy, timeline, per-paper deep-dives,
   challenges, frontiers, direct Q&A, multi-tier reading list, and (optionally)
   Mermaid citation graphs + a single-file interactive HTML render of the
   completed survey.
6. **Version** adds new evidence (papers, datasets, model weights, experiments)
   as delta sections without rewriting prior content.

## Phases

| Phase | Question answered | Procedure |
|---|---|---|
| `frame` | What are we surveying, what are the sub-questions, what is in/out of scope? | `phases/00-frame.md` |
| `round1` | What does a broad multi-source search reveal? | `phases/01-round1.md` |
| `audit` | Is coverage complete across sub-questions and evidence dimensions? | `phases/02-gap-audit.md` |
| `roundn` | How do we fill the named coverage gaps? | `phases/03-roundN.md` |
| `synthesize` | What is the answer, the taxonomy, and the reading list? | `phases/04-synthesize.md` |
| `version` | How do we add new evidence without rewriting? | `phases/05-version.md` |

## Auto-detect

If arguments do not start with a phase keyword:

1. No survey directory exists → `frame`.
2. `index.md` exists but no `paper_index.md` rows → `round1`.
3. `paper_index.md` has rows but no `coverage_matrix.md` → `audit`.
4. `coverage_matrix.md` has gaps with `status: open` → `roundn`.
5. Coverage matrix is closed but no `survey.md` → `synthesize`.
6. `survey.md` exists and the user asks to add new evidence → `version`.

State the detected phase, `survey-id`, study root, and reason before loading.

## Loading Rules

1. Read exactly one phase file after resolution.
2. Load `references/source-coverage.md` during `round1` and `roundn` whenever
   you need to recall how to query each source.
3. Load `references/arxiv-query-patterns.md` before composing any arXiv
   query. The default `all:` query returns recency-sorted noise; the
   reference defines six template intents and their field specifiers.
4. Load `references/paper-rating-rubric.md` whenever you score papers.
5. Load `references/coverage-matrix.md` during `audit` and at every `roundn`
   re-audit.
6. Load `references/evidence-extraction.md` whenever a phase needs to
   extract numeric claims from a paper PDF, paperswithcode, OpenReview
   supplementary, or a repo README. Required reading before populating
   `chart_data.csv`-style structured tables.
7. Load `references/claims-discipline.md` before writing any synthesis section.
8. Load `references/taxonomy-revision.md` during `synthesize` and after every
   `roundn` that adds ≥3 papers.
9. Load `references/bias-audit.md` during `audit`.
10. Load `references/reproducibility-assessment.md` before populating any
    ★★★ paper's `Repro` column, and during `synthesize` to assign each paper a
    tier R1-R4 (the 5-question rubric and the annotation rule live there).
11. Load `references/datasets-section.md` during `synthesize` for any
    accuracy-comparison survey — canonical-vs-emergent classification + the
    adoption heatmap, placed at §4 before the method-route comparison.
12. Load `references/citation-graph.md` during `synthesize` for paper-to-paper
    Mermaid figures: recommended at ≥10 ★★★ papers, mandatory on a
    "lineage"/"who-cites-whom" request, skip for purely conceptual surveys.
13. Load `references/html-export.md` during `synthesize` when shipping the
    single-file interactive HTML deliverable (**requires `pip install markdown`**).
14. Load `references/multi-agent-dispatch.md` during `round1`/`roundn` for
    fan-out search (delegation template, runtime backings, dedup ordering
    barrier) and during `synthesize` for the `claims-adversary` gate — the
    survey specialization of project-meta's Task Dispatch paradigm.
15. Load `references/loop-mode.md` when the survey is running under `/loop`
    (ScheduleWakeup / self-paced async iteration).
16. Load templates only when scaffolding the matching artifact.

## Cross-Cutting Invariants

- Never skip `frame`; without sub-questions the gap audit cannot run.
- Sub-question decomposition is fixed at frame time; new sub-questions trigger
  a new survey, not a silent edit.
- Every paper has a stable ID (`P001`, `P002`, ...) that all later sections
  reference. Renumbering invalidates every cross-reference.
- **MUST** resolve every claim in `survey.md` to a row in `claims.jsonl` that
  names the paper ID, the section/page, and a verbatim quote or table reference.
  No speculation, no "I think", no implicit synthesis without a backing claim.
- Mark unknown values explicitly (e.g., "未披露", "not disclosed", "N/A") in
  comparison tables. Never guess.
- Round N is gap-driven, not curiosity-driven. Each Round N entry must name
  the gap it addresses. The **4-round cap applies only to audit-gated gap
  rounds**; post-audit `version` additions (new evidence, user-directed adds,
  bias/weak-cell hardening, sub-question additions) are unbounded and do not
  reopen the audit — see `phases/05-version.md`.
- Round-1 cap scales with sub-question count: `cap ≈ max(30, 3 × N_SQ)`, not a
  flat 25-35 (which assumes ~6-9 SQs). See `phases/01-round1.md`.
- Closed ≠ diverse. A cell with one ★★★ (or all from one lab/year) is `weak`,
  not done; `scripts/coverage_check.py` flags these. Harden via a weak-cell
  `version` pass or accept+document the concentration.
- Review/critical-review/survey dimensions: score a review's evidence on
  synthesis breadth (so the canonical review can reach ★★★), or close the cell
  on an authority-3 ★★ review. See `references/paper-rating-rubric.md` and
  `references/coverage-matrix.md`.
- Taxonomies are revisable. After Round N adds ≥3 papers, re-evaluate whether
  existing buckets still partition cleanly. Cross-cutting sub-questions are
  allowed: cross-tag one paper row across SQs (union the tags), but count each
  paper once in the bias audit — see `references/taxonomy-revision.md`.
- **MUST** run the bias audit before synthesis. If institution / country / year /
  method-route distribution is over-concentrated (any one bucket > 60% of
  ★★★ papers), trigger an additional Round N targeted at the under-represented
  bucket. `scripts/bias_audit.py` computes institution/country/year/venue (and
  method-route when the column exists); add a `Country` tag/column to enable
  country auditing.
- Version updates must preserve prior section anchors so cross-references
  survive.
- Fan-out search obeys an ordering barrier: parallel search subagents are
  read-only and return candidate rows; only the lead writes `paper_index.md`,
  after central dedup/merge. Never let parallel agents append index rows
  directly — that double-counts papers (see `references/multi-agent-dispatch.md`).
- **MUST** pass the `claims-adversary` review gate before status `synthesized`.
  A `block` verdict is a hard STOP — fix the flagged claims and re-run; never
  set status `synthesized` over an open `block`.
- Do not change secrets, credentials, or external accounts as part of survey
  work.

## Gotchas

- **arXiv-only is not enough.** arXiv preprints get out of date when the
  paper is accepted at a venue; OpenReview tells you peer-review status,
  DBLP tells you canonical venue, Semantic Scholar gives citation count.
  The four sources together prevent the "preprint label" trap (see
  `references/source-coverage.md`).
- **Star rating ≠ relevance.** A 5-citation 2025 preprint can be ★★★ if
  it answers a sub-question precisely; a 200-citation 2018 paper can be ★★
  if it predates the field's reframing. Score on the 4 dimensions
  independently before binning.
- **"Not found" ≠ "doesn't exist", especially for active industrial labs.**
  A clean search miss is weak evidence for a negative claim ("single paper / no
  successor / no vN"). Meta FAIR, DeepMind, the Allen Institute et al. ship
  successors faster than aggregators index them. Check the lab's publications
  page/blog before asserting absence, or hedge `confidence: low` — see
  `references/source-coverage.md`. (A real run missed a "v2" this way.)
- **Build claims at the right provenance tier.** If the survey is built from
  abstracts/metadata rather than full PDFs, set `source_tier` accordingly and
  `confidence ≤ medium`, and carry a provenance note in `survey.md` — don't
  imply verbatim full-text verification that didn't happen.
- **Gap audit on counts is weaker than on dimensions.** "≥3 papers per
  sub-question" lets you accumulate three papers from the same lab/year.
  The dimension matrix (theory / experiment / survey / critical-review)
  catches this — see `references/coverage-matrix.md`.
- **claims.jsonl is the anti-hallucination contract.** Build it before
  writing the synthesis prose. Every line in `survey.md` that asserts a
  fact must point to a claim row. The validator script checks this.
- **Versioning is delta-only.** v2 does not rewrite v1 sections. It adds
  new sections with `(vN added)` markers and updates prior sections with
  minimal in-place edits when a v1 claim is now superseded by new evidence.

## Running Under /loop Dynamic Mode

Load `references/loop-mode.md` for the full per-iteration hygiene procedure
(loop_state.json scaffold, progress journaling, ScheduleWakeup stop conditions).

## Trigger Decision

Invoke this skill when the request shape matches any of:

- the request is **literature-only**: surveying, mapping, or auditing published
  work with no experimental or code component
- the user says "literature review", "comprehensive survey", "research X for me",
  or asks to expand/audit an existing survey
- the request asks for a coverage matrix, gap audit, or sub-question decomposition
  over a body of papers
- a peer skill (e.g. `dl-research`) explicitly delegates its survey phase here

Do NOT invoke when the work is primarily experimental, code-generation, or
artifact-delivery without a literature component — see Skill Arbitration below.

## Bootstrap Order

**First invocation** (no survey directory): state `survey-id` + root → confirm
scope → load `phases/00-frame.md` → run `frame` → Auto-detect next phase.

**Re-entry** (directory exists): run Auto-detect → state phase, `survey-id`,
root, and reason → load the matching phase file plus any Loading Rules it
requires.

## Skill Arbitration

This skill is the right owner when the request is *literature-only* — surveying, mapping, or auditing published work. When the request expands beyond literature, defer:

| Request shape | Owner | This skill's role |
|---|---|---|
| Pure literature survey, comprehensive review, "research X for me" with no experimental component | **`deep-survey-bfs`** | acts |
| DL research study (frame → experiments → eval → synthesize) where literature survey is one of several phases | **`dl-research`** | invoked by `dl-research`'s `survey` phase as a sub-step; do not freelance experiments here |
| Repo lacks an agent harness (no `AGENTS.md` / `USER.md` / mirrors) and the user wants the survey shipped as a delivered artifact | **`project-meta` first**, then `deep-survey-bfs` | accept hand-off from `project-meta` after `init`; do not author harness from inside this skill |
| Survey output needs to be packaged as a target-repo artifact with provenance frontmatter, mirror sync, or pre-commit delivery | **`project-meta`** | hand off the rendered survey + claims.jsonl + paper_index.md for packaging |

State the resolution before acting. Never silently invoke a peer skill.

## Examples

A reference end-to-end run lives at [`examples/stereo-matching-edge-fm/`](examples/stereo-matching-edge-fm/). It demonstrates: 26 papers indexed (18 ★★★), 67 claims with verbatim quotes, 9 sub-questions (8 closed), §3.5 datasets canonical-vs-emergent classification, §11 institutional concentration narrative, §14 reproducibility tier, citation graph in three views, and a 99 KB single-file interactive HTML render. See [`examples/README.md`](examples/README.md) for the index. Use the example as the canonical pattern when the user asks "what should the output look like?" or when authoring new artifacts in this skill's style.

## Output Footer

End each invocation with:

```md
**Phase**: <phase>  **Survey**: <survey-id>  **Status**: <status>  **Next**: <phase|done>
```
