# Phase: prepare

Use when a design row must become reproducible run material.

## Steps

1. Read the active design row and adapter. If the design row is ambiguous, go
   back to `design`.
2. Confirm all changes stay within the adapter's editable surface. Do not edit
   protected files, eval harnesses, metric parsers, or data split definitions
   without protocol-change approval.
3. Create or update configs, scripts, or job specs using the project's native
   configuration style.
4. Capture reproducibility metadata:
   - code revision or dirty-diff note;
   - config path or override set;
   - dataset/split/version;
   - seed plan;
   - expected artifacts;
   - launch command template.
5. For H/E studies, create or update
   `Hn-<track-name>/En-<experiment-name>/manifest.md` with the display ID
   (`H1.E1`), slug (`H1E1-<experiment-name>`), config diff, command template,
   expected artifacts, and protocol references.
6. For non-trivial code/config changes, load `references/multi-agent-harness.md`
   and run the Reviewer-Between-Subtasks gate on the Worker's edit: a fresh,
   separate `implementation-intent-reviewer` (not the agent that wrote the
   change) receives the design row, adapter editable surface, diff, and
   protected-file list. A `block` is a hard STOP — fix the mismatch before
   `launch`; do not proceed on an unresolved block.
7. Run the narrowest dry-run, config validation, or syntax check supported by
   the adapter.
8. Append a `prepared` ledger row or update the design table with the prepared
   artifact paths. Include `experiment_id` (canonical, e.g. `H1.E1` or `E1`)
   and, for H/E studies, `track_id`, `slug`, and `parent_id`.

**MUST delivery gate:** run `python scripts/validate_ledger.py <study-root>/runs.jsonl` after writing the ledger row. A non-zero exit blocks handoff — fix all reported errors before proceeding to `launch`. See `examples/sample-study/runs.jsonl` for a valid reference.

## Hand Off

Set status to `prepared`. The next phase is `launch` when the user or workflow
authorizes execution.
