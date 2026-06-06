# Phase: monitor

Use while runs are active or when the user asks for status.

## Steps

1. Read `runs.jsonl` and the adapter's tracking backend.
2. For active runs, collect status, elapsed time, cost estimate, latest metric,
   and failure signals.
3. Apply the stop policy from `index.md`. Early stop only when the policy
   authorizes it or the run is clearly invalid.
4. Append `03-monitor.md` with changed-state events only:
   - submitted, running, completed, failed, stopped;
   - crashes, stale metrics, invalid data, budget warnings;
   - manual interventions.
5. Update ledger rows with the newest status and metric summary.

**MUST delivery gate:** run `python scripts/validate_ledger.py <study-root>/runs.jsonl` after updating the ledger. A non-zero exit blocks handoff — fix all reported errors before handing off to `evaluate`. See `examples/sample-study/runs.jsonl` for a valid reference.

## Hand Off

If runs completed, next phase is `evaluate`. If runs remain active, next phase
is `monitor` with the next check interval.
