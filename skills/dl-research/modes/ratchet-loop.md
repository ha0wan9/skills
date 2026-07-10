# Mode: ratchet-loop

Use for bounded autonomous improvement when the target is narrow, the metric is
machine-readable, and the eval harness must remain fixed.

## Loop-Contract Conformance

This loop conforms to
[`project-meta/references/loop-contract.md`](../../project-meta/references/loop-contract.md)
(project-meta is canonical; this is a self-contained floor per the
Dependency & Canon pattern in `references/multi-agent-harness.md`). Inline
floor: **trigger** = a `ratchet` invocation with all Refuse-To-Start-Unless-Known
items resolved; **goal** = the study's keep rule beating the baseline within
protocol; **budget** = the declared time/trial/compute budget + no-improvement
patience; **verification** = computational floor `validate_ledger.py` (MUST,
every iteration) + optional `result-skeptic` critic on promotion; **state** =
`loop_state.json` at the study root (below), checkpointed at end-of-iteration —
this loop has no phase structure, so `phase` is omitted; **stopping rule** =
budget exhausted, patience exhausted, or user stop (Loop step 7) — a
`result-skeptic` `block` is a synchronous hard stop, never silent.

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

A final `result-skeptic` **`block` is a hard STOP** (the paradigm's Synchronous
Gate): the loop terminates and returns, the best result is **not promoted**, and
the blocker is surfaced to the user. The ratchet is the most background-like
dl-research backing, so this is exactly the "stop on the first block, never run
past it" rule — resume only by re-entry after the user resolves the block.

## Loop

1. Load `references/decision-rules.md`.
2. Read the current best ledger row and baseline.
3. Propose one small change inside the editable surface.
4. Apply the change, run the eval command, parse the metric, and record a
   ledger row.
5. Keep the change only if it beats the keep rule and does not violate
   complexity, protocol, or budget constraints.
6. Discard or revert failed changes and record why.
7. **Checkpoint** `loop_state.json` at the study root — this is the loop's
   phase boundary (end of iteration, right after the keep/discard record in
   step 6, never on a timer). Resolve project-meta the same way
   `references/multi-agent-harness.md` resolves the canon (installed
   project-meta preferred; repo-path fallback when developing inside this
   marketplace):

   ```bash
   # full dual-runtime set — see project-meta/references/shared-cli-delegation.md
   pm_dir=""
   for c in "${PROJECT_META_DIR:-}" \
            "$HOME/.codex/skills/project-meta" \
            "$HOME/.claude/skills/project-meta" \
            "$HOME"/.codex/plugins/marketplaces/*/skills/project-meta \
            "$HOME"/.claude/plugins/marketplaces/*/skills/project-meta \
            "$HOME"/.codex/plugins/cache/*/*/*/skills/project-meta \
            "$HOME"/.claude/plugins/cache/*/*/*/skills/project-meta \
            "$HOME"/.codex/plugins/cache/*/project-meta/* \
            "$HOME"/.claude/plugins/cache/*/project-meta/*; do
     [ -n "$c" ] && [ -f "$c/scripts/loop_state.py" ] && { pm_dir="$c"; break; }
   done
   [ -z "$pm_dir" ] && [ -f skills/project-meta/scripts/loop_state.py ] && pm_dir="skills/project-meta"
   if [ -n "$pm_dir" ]; then
     python3 "$pm_dir/scripts/loop_state.py" checkpoint <study-root>/loop_state.json \
       --current-task "<next proposed change>" --completed "<run_id: kept|discarded>"
   else
     # Thin floor: project-meta not found — loop_state.json is a convenience
     # checkpoint, not a hard gate. Continue relying on runs.jsonl rows alone
     # (the pre-L2 resume story) and note the gap in the study's Output.
     echo "[ratchet] loop_state.py not found; skipping checkpoint (runs.jsonl remains the record of truth)." >&2
   fi
   ```
8. Continue until budget, no-improvement patience, or user stop condition is
   reached (checked via `loop_state.py should-stop <study-root>/loop_state.json`
   when available, alongside the existing budget/patience checks).

## Resume

An interrupted ratchet resumes by reading `loop_state.json` (iteration,
current_task, blockers, completed/next targets, budget_spent) plus the last
row of `runs.jsonl` (the authoritative record of what actually ran) — the
checkpoint says what the loop *intended* next; the ledger says what
*actually happened*. Reconcile the two before continuing: if the last
`loop_state.json` checkpoint's `current_task` has no matching ledger row,
that iteration did not complete — redo it, don't assume it ran.

## Guardrails

- Do not edit protected files, metrics, parser, eval data, or data splits.
- Do not widen the editable surface without explicit protocol-change approval.
- Do not treat a single noisy win as a promoted result unless the study's
  decision rule allows it.
- Record crashes and timeouts as rows, not invisible failures.
- Preserve enough diff/context for the best row to be reproduced.
- **MUST delivery gate:** after every iteration that writes to `runs.jsonl`,
  run `python scripts/validate_ledger.py <study-root>/runs.jsonl`. A non-zero
  exit stops the loop until all errors are fixed — never proceed past a schema
  error. See `examples/sample-study/runs.jsonl` for a valid reference.

## Output

End with best run ID, metric delta, changes kept, changes discarded, remaining
risk, and whether the result is exploratory or promotable.
