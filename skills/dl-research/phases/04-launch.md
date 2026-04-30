# Phase: launch

Use when prepared run material should be submitted to the configured execution
backend.

## Steps

1. Read the prepared row, adapter launch command, metric parser, budget, and
   stop policy.
2. Verify the launch command uses the intended code revision, config, data
   version, seed, and artifact sink.
3. Verify the run name follows the adapter's `run_name_pattern`. For H/E
   studies this means `<study-id>-<HnEn>-<experiment-name>`.
4. Launch through the adapter-defined backend.
5. Append or update one `runs.jsonl` row per run with:
   - `run_id` and `experiment_id` (canonical, e.g. `H1.E1` or `E1`);
   - for H/E studies: `track_id`, `slug`, and `parent_id`;
   - `status` set to `running` or `failed`;
   - hypothesis and intervention;
   - command or job spec;
   - code revision or dirty-diff note;
   - data version;
   - seed;
   - budget estimate;
   - tracking URL or artifact location.
6. If launch deviates from design, mark `design_deviation=true` and explain.
7. Run `python scripts/validate_ledger.py <study-root>/runs.jsonl`. Fix
   reported errors before handoff.

## Hand Off

Set status to `launched` if at least one run is in flight. The next phase is
`monitor`.
