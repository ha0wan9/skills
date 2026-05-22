---
name: dl-research
description: >-
  Guide rigorous Deep Learning research studies: initialize a project research
  adapter, frame questions, survey evidence, design controlled experiments,
  prepare/launch/monitor runs, evaluate results, synthesize findings, audit
  methodology, or run a bounded autonomous ratchet loop. Use for
  project-agnostic model training, ablation, optimization, and research
  workflow orchestration.
---

# DL Research

Project-agnostic meta skill for Deep Learning research workflows. It defines
the research lifecycle, adapter contract, H/E identity rules, ledger shape, and
synthesis graph requirements. Project-specific infrastructure lives in a
repo-local adapter; do not hardcode ClearML, Hydra, queue names, eval scripts,
or repository paths in this skill.

Thin router: resolve the mode or phase, resolve `study-id`, then load only the
needed procedure file.

`study-id` rules: kebab-case, 2-5 tokens, no dates, no version suffixes,
explicit about the research question. Good: `token-pruning-efficiency`,
`depth-loss-scaling`, `batch-size-noise`. Bad: `test1`, `new-study-v3`,
`stuff`.

Default study root without an adapter: `.research/studies/<study-id>/`. A
project adapter should override this for real projects. The preferred
project-local adapter path is `agents/research/adapter.yaml` plus optional
human notes in `agents/research/adapter.md`. The active root and adapter path
must be written in each study `index.md`.

When a project adapter defines `research_root_pattern`, use it as the
canonical study root. The preferred convention is:

- branch/worktree identity: `res/<study-id>`
- study root: `agents/research/<study-id>/`
- run name prefix: `<study-id>-<HnEn>-<experiment-name>`

## H/E Identity

Use H/E IDs when a study contains multiple competing routes.

- Hypothesis track display ID: `H1`, `H2`, ...
- Experiment display ID: `H1.E1`, `H1.E2`, ...
- Slug/run ID: `H1E1`, `H1E2`, ...
- Directory layout: `H1-<track-name>/E1-<experiment-name>/`
- Run prefix: `<study-id>-H1E1-<experiment-name>`

`Hn` means a hypothesis track or research route. `En` means a concrete
experiment under that route. Keep the root ledger global so routes can be
compared without reading every nested artifact.

## Phases

| Phase | Question answered | Procedure |
|---|---|---|
| `frame` | What are we studying, why, and what decides success? | `phases/00-frame.md` |
| `survey` | What do prior work, existing runs, and code truth already show? | `phases/01-survey.md` |
| `design` | Which controlled experiments should run, with what gates? | `phases/02-design.md` |
| `prepare` | Are configs, scripts, data versions, and jobs reproducible? | `phases/03-prepare.md` |
| `launch` | How do planned experiments become tracked runs? | `phases/04-launch.md` |
| `monitor` | What is the health, cost, and live state of runs? | `phases/05-monitor.md` |
| `evaluate` | What did completed runs show against gates and baselines? | `phases/06-evaluate.md` |
| `synthesize` | What is the answer, what changed, and what is next? | `phases/07-synthesize.md` |
| `audit` | Are claims, protocol, budget, and reproducibility still valid? | `phases/08-audit.md` |
| `init` | How does this project map the meta protocol to local infra? | `phases/00-init.md` |
| `ratchet` | Can an autonomous bounded loop improve a metric safely? | `modes/ratchet-loop.md` |

## Auto-detect

If arguments do not start with a phase or mode:

1. User asks to initialize or repair project research infra -> `init`.
2. No project adapter exists and the target is a real project -> `init`.
3. No study directory exists -> `frame`.
4. `index.md` exists but no survey notes -> `survey`.
5. Survey exists but no active design shortlist -> `design`.
6. Shortlist has prepared=false rows -> `prepare`.
7. Prepared rows have launched=false -> `launch`.
8. Ledger has running rows -> `monitor`.
9. Ledger has completed rows without verdicts -> `evaluate`.
10. Evaluation exists but no synthesis -> `synthesize`.
11. User asks "are we still on track", "is this valid", or "audit" -> `audit`.

State the detected phase, `study-id`, study root, and reason before loading a
procedure file.

## Loading Rules

1. Read exactly one phase or mode file after resolution.
2. Load `references/adapter-contract.md` when no project adapter exists or
   when backend details are unclear.
3. Load `references/dl-methodology-checklist.md` for design, evaluate, and
   audit when methodology risk is non-trivial.
4. Load `references/decision-rules.md` for design, evaluate, synthesize, and
   ratchet decisions.
5. Load `references/multi-agent-harness.md` when a phase asks for managed
   clean-context review, or when the user requests independent reviewers.
6. Load `references/agent-charter.md` only when creating a reviewer prompt or
   adjudicating reviewer disagreement.
7. Load templates only when scaffolding or repairing an artifact.

## Optional Front-End

`templates/frontend/report.html` is a project-agnostic HTML report
skeleton (theme system, 9-phase sticky flow bar, fixed TOC, comment
rail, goals tracker, Plotly + Mermaid hooks). `scripts/research_server.py`
is a stdlib HTTP host that serves the per-study reports and sidecars
from `agents/research/<study-id>/` and exposes `/api/role`,
`/api/studies`, `/<study-id>/api/state`, and
`/<study-id>/api/objectives/latest`.

The front-end is **optional**. The protocol works without it; do not
load `templates/frontend/` unless the user is instantiating a report,
adding a visualisation, or wiring the server. See
`templates/frontend/README.md` for placeholders, the goals-tracker
JSONL schema, and customisation notes.

## Cross-Cutting Invariants

- Never skip `frame`; an audit needs a stable question, scope, budget, and
  success criteria.
- `dl-research init` only creates or repairs the project adapter. It must not
  create a study directory unless the user also asks for `frame`.
- Every real project study must name the repo-local adapter and write the
  resolved study root in `index.md`.
- Respect adapter patterns for branch, root, run names, editable surface,
  protected files, metric parsing, tracking, and graph generation.
- Treat the eval harness, metric parser, protected files, and data split as
  protocol. Changes require explicit protocol-change approval and must be
  recorded before use.
- Separate evidence, interpretation, and hypothesis in analytic notes.
- Prefer cheap probes before full training when they can answer the question.
- Every run, including crashes and discarded attempts, must have a ledger row.
- Ledger rows for H/E studies must include `track_id`, canonical
  `experiment_id` such as `H1.E1`, and `slug` such as `H1E1-<experiment-name>`.
- A result can be promoted only if the decision rule for this study permits it.
- Do not change secrets or credentials as part of research workflow setup.

## Gotchas

Non-obvious traps the agent will hit without being warned. Keep these here, not
in references — the agent reads them before encountering the situation.

- **Phase number ≠ artifact number.** Phases are numbered `00..08` for ordering;
  artifacts are numbered by appearance in the study folder:
  `01-survey.md` (from `survey`), `02-design.md` (`design`), `03-monitor.md`
  (`monitor`), `04-evaluation.md` (`evaluate`), `05-synthesis.md`
  (`synthesize`). `prepare` and `launch` produce no top-level numbered file —
  they write to `runs.jsonl`, the design table, and per-experiment manifests.
  Audits look for these exact filenames.
- **`runs.jsonl` is global per study, not per-track.** Multi-route studies
  must include `track_id`, `experiment_id` (canonical, e.g. `H1.E1`), and
  `slug` (e.g. `H1E1-<experiment-name>`) on every row so routes can be
  compared without opening every nested artifact.
- **Protocol changes must be recorded before the deviating run.** Editing
  protected files, metric, parser, baseline source, eval data, or seed policy
  after a run launches makes the result invalid; record the change, reason,
  approval, and effective run ID first.
- **`research_graph.mmd` and `research_graph.json` must be updated together.**
  The audit "Graph consistency" check fails silently if only one exists or if
  they disagree on H/E nodes, verdicts, or the winning route.
- **`study-id` is fixed at `frame`.** Renaming after `prepare`/`launch`
  corrupts run names, ledger lookups, and graph node IDs. Fork a new study
  instead of renaming.
- **`runs.jsonl` is mutated by `prepare`, `launch`, `monitor`, `evaluate`, and
  `ratchet`.** After every mutation, run
  `python scripts/validate_ledger.py <study-root>/runs.jsonl` and fix the
  reported errors before phase handoff. The validator is dependency-free and
  catches schema drift the eye misses.

## Output Footer

End each invocation with:

```md
**Phase**: <phase-or-mode>  **Study**: <study-id>  **Status**: <status>  **Next**: <phase|mode|done>
```

For audit:

```md
**Phase**: audit  **Study**: <study-id>  **Verdict**: aligned | warnings | drift | invalid  **Next**: <action>
```
