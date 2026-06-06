# Phase: evaluate

Use when one or more runs have completed and need a verdict against the design.

## Steps

1. Read `index.md`, `02-design.md`, `runs.jsonl`, the adapter metric parser,
   and `references/decision-rules.md`.
2. Load `references/dl-methodology-checklist.md` for non-trivial claims.
3. Compare each run to its baseline/control using the planned metric direction,
   slices, seeds, and decision gate.
4. Separate:
   - `E:` measured results;
   - `I:` interpretation;
   - `H:` follow-up hypotheses.
5. Mark each run or experiment as `kept`, `killed`, `inconclusive`, or
   `invalid`.
6. Invalid results include changed eval protocols, missing data versions,
   leakage risk, broken metric parsing, or unapproved protected-file changes.
7. Load `references/multi-agent-harness.md` and run a clean-context
   `result-skeptic` review before marking any result promotable, when results
   are surprising, or when repeats disagree. The reviewer receives only the
   protocol, design gates, ledger rows, and raw metric artifacts.
8. Write or append `04-evaluation.md`; update `runs.jsonl` verdict fields.

**MUST delivery gate:** run `python scripts/validate_ledger.py <study-root>/runs.jsonl` after updating verdict fields. A non-zero exit blocks handoff — fix all reported errors before handing off to `synthesize`. See `examples/sample-study/runs.jsonl` for a valid reference.

## Hand Off

If the study question is answered, next phase is `synthesize`. If not, return
to `design` with the remaining question.
