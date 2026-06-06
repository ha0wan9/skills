# /loop Dynamic Mode — Per-Iteration Hygiene

When the survey is being progressed asynchronously via `/loop` (no fixed interval;
ScheduleWakeup self-pacing), maintain a `loop_state.json` artifact at the survey
root scaffolded from `templates/loop_state.json`. Read it at the start of every
fired iteration so the agent immediately knows iteration number, current task,
target paper IDs, blockers, and completed targets without re-deriving from
`paper_index.md` and `claims.jsonl`.

## Per-Iteration Steps

1. Read `loop_state.json`. If missing, scaffold from the template.
2. Use `current_task.target_paper_ids` and `target_metric_keywords` to plan the
   next 60-180 seconds of work. Prefer `scripts/extract_paper_metrics.py` for PDF
   table surfacing.
3. After completing the work, append a one-line entry to
   `audits/r<N>-progress.jsonl` summarizing what landed.
4. Update `loop_state.json`: increment `iteration`, set `last_updated_utc`, move
   the just-finished task into `completed_targets`, pop the next target from
   `next_targets` into `current_task`. Add to `blockers` if a target failed.
5. If any `stop_conditions` flip true, omit `ScheduleWakeup` and write a final
   summary instead.
