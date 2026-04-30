# Decision Rules

Use these defaults unless the study `index.md` defines stricter rules.

## Result Classes

- `exploratory`: useful signal from a probe, single seed, small sample, or
  partial budget. Can guide next design, but should not be promoted broadly.
- `promotable`: passes the predeclared gate with required repetitions and no
  unresolved protocol issues.
- `inconclusive`: direction is unclear, noisy, underpowered, or blocked by
  missing evidence.
- `invalid`: protocol violation, leakage risk, broken metric, wrong data, or
  untracked change undermines the result.

## Keep/Discard Defaults

- Keep if the primary metric improves in the intended direction by at least the
  configured threshold and secondary guardrail metrics do not regress beyond
  tolerance.
- Discard if it fails the threshold, violates protected files, exceeds budget,
  or adds complexity disproportionate to the gain.
- Mark inconclusive rather than kept when noise can plausibly explain the gain.

## Repetition Defaults

- Single cheap probes can choose the next experiment.
- Promotion requires the repetition rule in `index.md`. If none is declared,
  require at least two independent confirmations for noisy training workflows.
- If repeats disagree, compare confidence intervals, paired samples, or slice
  behavior before claiming improvement.

## Complexity Penalty

Penalize changes that increase code paths, training time, inference latency,
memory, data requirements, or operational fragility. A small metric gain is not
automatically worth adopting.

## Protocol Changes

Protocol changes are allowed only when recorded before use. After a protocol
change, compare results within the new protocol or rerun baselines.
