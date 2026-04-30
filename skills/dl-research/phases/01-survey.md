# Phase: survey

Use when the study is framed but evidence has not yet been gathered from prior
runs, papers, code, or data.

## Steps

1. Read `index.md` and the adapter. Keep the study question and success
   criteria visible while gathering evidence.
2. Gather the cheapest relevant evidence first:
   - prior experiment trackers, logs, reports, or notebooks;
   - repository source/config truth;
   - dataset cards, split definitions, or data-version metadata;
   - baseline checkpoints and evaluation summaries;
   - recent papers or official docs when the question depends on external
     methods.
3. Write `01-survey.md` as append-only notes. Tag analytic bullets:
   - `E:` evidence observed directly;
   - `I:` interpretation of evidence;
   - `H:` hypothesis to test later.
4. For broad or high-stakes studies, load `references/multi-agent-harness.md`
   and use optional clean-context scouts:
   - literature/prior-work scout for external evidence;
   - code-truth/prior-run scout for repository and tracker evidence.
   Keep their outputs as evidence notes, not decisions.
5. Store large plots, tables, or exports under `artifacts/` and link them from
   the notes.
6. Record unresolved evidence gaps explicitly; do not hide missing baselines or
   missing data-version details.

## Hand Off

Set status to `surveyed`. The next phase is `design` if there is enough
evidence to propose controlled experiments; otherwise continue survey with the
named gaps.
