# DL Methodology Checklist

Use during design, evaluation, and audit when claims depend on model quality,
speed, cost, or robustness.

## Baseline Fairness

- Same data split and preprocessing unless the change is the intervention.
- Comparable training budget, early-stop policy, and model selection rule.
- Same evaluation harness and metric parser.
- If compute differs, report compute-normalized results.

## Data Integrity

- Train, validation, and test split sources are identified.
- Dataset versions are immutable or logged with enough detail to reproduce.
- Leakage risks are checked for near-duplicates, sequence overlap, subject
  overlap, temporal leakage, and generated data contamination where relevant.
- Data filtering or relabeling is part of the protocol when it affects metrics.

## Metric Validity

- Primary metric direction is explicit.
- Secondary metrics capture regressions the primary metric may hide.
- Slice metrics cover known failure modes or deployment-critical subsets.
- Metric parser is deterministic and protected.

## Robustness

- Repeated seeds or tolerance bands are required when run-to-run noise can
  affect the decision.
- Qualitative samples are used to explain behavior, not to override metrics.
- Claims distinguish exploratory probes from promotable results.

## Reproducibility

- Code revision, config, data version, seed, command, and artifacts are logged.
- Crashes and discarded attempts are visible in the ledger.
- Any dirty working tree or manual intervention is recorded.
