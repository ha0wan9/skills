# Phase: design

Use when evidence exists and a controlled experiment shortlist is needed.

## Steps

1. Read `index.md`, `01-survey.md`, the adapter, and
   `references/decision-rules.md`.
2. Load `references/dl-methodology-checklist.md` when the study touches data
   splits, baselines, metrics, or claims of improvement.
3. Scaffold or append `02-design.md` from `templates/design.md`.
4. For each candidate, record:
   - stable ID (`H1.E1`, `H1.E2`, ... for H/E studies; `E1`, `E2`, ... only
     for single-route studies);
   - slug (`H1E1-<experiment-name>`) for run names and file-safe references;
   - hypothesis track (`H1`, `H2`, ...), if applicable;
   - hypothesis;
   - intervention;
   - control/baseline;
   - config or code diff at behavior level;
   - dataset/split/version;
   - primary and secondary metrics;
   - seeds or repetition rule;
   - expected cost;
   - decision gate;
   - dependency and parallelism class.
5. Prefer one-factor experiments. If a multi-factor experiment is justified,
   label it and include the isolation or follow-up needed to interpret it.
6. Schedule probes before full runs when the probe can answer a gate.
7. Ensure every active hypothesis route has a corresponding
   `Hn-<track-name>/index.md` with its falsifiable hypothesis, decision gate,
   status, and child experiment list.
8. Load `references/multi-agent-harness.md` and run a clean-context
   `design-critic` review when compute budget is non-trivial, claims will be
   promotable, or the shortlist has multi-factor interventions. Record blocking
   issues and corrections in `02-design.md` before handoff.

## Hand Off

Set status to `designed`. The next phase is `prepare` for the highest-priority
candidate whose dependencies are satisfied.
