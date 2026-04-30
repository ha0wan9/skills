# Mode: ratchet-loop

Use for bounded autonomous improvement when the target is narrow, the metric is
machine-readable, and the eval harness must remain fixed.

## Refuse To Start Unless Known

- immutable eval command;
- protected files and eval harness;
- editable files/configs;
- primary metric and direction;
- fixed time, trial, or compute budget;
- keep/discard threshold;
- ledger path;
- timeout/crash policy.

If any item is unknown, stop and ask for it or run `frame`/adapter setup.

## Managed Review

Load `references/multi-agent-harness.md` for:

- preflight harness review before the first autonomous loop in a study;
- final result-skeptic review if the best result may be promoted.

Do not invoke reviewers inside every iteration; that breaks the ratchet loop's
speed and determinism.

## Loop

1. Load `references/decision-rules.md`.
2. Read the current best ledger row and baseline.
3. Propose one small change inside the editable surface.
4. Apply the change, run the eval command, parse the metric, and record a
   ledger row.
5. Keep the change only if it beats the keep rule and does not violate
   complexity, protocol, or budget constraints.
6. Discard or revert failed changes and record why.
7. Continue until budget, no-improvement patience, or user stop condition is
   reached.

## Guardrails

- Do not edit protected files, metrics, parser, eval data, or data splits.
- Do not widen the editable surface without explicit protocol-change approval.
- Do not treat a single noisy win as a promoted result unless the study's
  decision rule allows it.
- Record crashes and timeouts as rows, not invisible failures.
- Preserve enough diff/context for the best row to be reproduced.
- After every iteration that writes to `runs.jsonl`, run
  `python scripts/validate_ledger.py <study-root>/runs.jsonl`. A schema error
  stops the loop until fixed.

## Output

End with best run ID, metric delta, changes kept, changes discarded, remaining
risk, and whether the result is exploratory or promotable.
