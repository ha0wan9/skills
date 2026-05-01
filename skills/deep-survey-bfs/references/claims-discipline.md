# Claims Discipline

## Contents

- [Why claims.jsonl](#why-claimsjsonl) — the anti-hallucination contract
- [Schema](#schema) — required fields per claim row
- [Build Order](#build-order) — claims first, prose second
- [Reference Patterns](#reference-patterns) — inline citation conventions
- [Validator Behavior](#validator-behavior) — what the script enforces
- [Common Pitfalls](#common-pitfalls)

## Why claims.jsonl

Free-form synthesis is the highest-risk part of a survey: this is where
hallucination, paraphrase drift, and citation creep happen. The discipline
inverts the usual order — every fact you intend to state in the survey
prose must first exist as a row in `claims.jsonl`, with a stable identifier
and a verbatim source quote.

The synthesis prose is then constrained to assertions that resolve to
claims rows. The validator script checks this mechanically.

## Schema

Each line in `claims.jsonl` is a JSON object:

```json
{
  "claim_id": "C001",
  "kind": "metric | architecture | dataset | finding | scale | timeline",
  "paper_id": "P004",
  "section": "Table 2 | §4.3 | Abstract | Figure 5",
  "quote": "verbatim text from the paper or table reference",
  "status": "active | superseded",
  "superseded_by": null
}
```

Required: `claim_id`, `kind`, `paper_id`, `section`, `quote` (or
`table_ref` / `figure_ref`).

Optional but encouraged:
- `notes`: brief context for the claim (e.g., "reported on TUEG split")
- `confidence`: low | medium | high (used when paper hedges its own claim)
- `depends_on`: list of other `claim_id`s this claim relies on. Most
  common use: a runtime claim was originally `confidence: medium`
  because hardware was unspecified; later, a separate claim confirms
  the hardware. Add the hardware-claim id to `depends_on`. The
  validator (`claims_validate.py`) prints a promotion hint when all
  depends_on targets are confidence=high, so the agent can decide
  whether to lift the dependent claim's confidence ceiling.

## Build Order

1. Skim each ★★★ paper. As facts you'll want to use surface, write them
   into `claims.jsonl`. Don't try to extract every fact — only the ones
   you'll actually cite.
2. After all ★★★ are processed, you should have 30-80 claims for a
   typical survey.
3. Synthesis prose is now templated: write the prose, cite by claim_id
   in comments during draft, then collapse to inline `(P004, §4.3)` style
   references in the final pass.

## Reference Patterns

In the final survey prose:

- Single claim: `(P004, §4.3)` or `(Liu et al. 2026, Table 2)`
- Multiple papers, same point: `(P004, P011, P017)`
- Quoted material: use quotation marks and a tighter ref:
  `"...60% accuracy on TUEG..." (P004, Table 2)`
- Method description without quote: cite paper ID and section that
  establishes the method: `(P018, §3 Method)`

## Validator Behavior

`scripts/claims_validate.py claims.jsonl survey.md` checks:

1. JSONL parses; every line has required fields.
2. Every paper_id in claims.jsonl exists in `paper_index.md`.
3. Every `(Pxxx)` reference in `survey.md` resolves to a row in
   `paper_index.md`.
4. Every claim_id mentioned in `survey.md` (if cited explicitly) resolves
   to a row in `claims.jsonl`.
5. Superseded claims with status='superseded' have a `superseded_by` that
   resolves to another claim_id with status='active'.

The validator does not check that quotes match the paper text — that
requires the original PDFs and is out of scope for the skill. The user
or a human reviewer remains responsible for verbatim accuracy.

## Common Pitfalls

- **Paraphrase drift**: the prose says "X% accuracy" but the quote field
  says "X.Y% accuracy". The verbatim quote is the contract; if you mean
  to round, say so explicitly.
- **Aggregated claims without a single source**: "EEG FMs are typically
  Transformers" is an aggregation. Either cite the survey paper that
  makes that aggregation, or split into individual claims per paper.
- **Hedging without source**: "It is widely believed that..." has no
  paper_id. Drop the claim, or attribute it to a specific paper that
  makes the belief explicit.
- **Empty quote with table_ref**: acceptable when the claim is
  table-driven (e.g., comparing benchmark numbers from a results table),
  but the table_ref must be specific enough to find it: `Table 4, row
  "LaBraM-base", column "TUEG accuracy"`.
