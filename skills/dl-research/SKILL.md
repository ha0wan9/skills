---
name: dl-research
description: >-
  Guide rigorous Deep Learning research studies: initialize a project research
  adapter, frame questions, survey evidence, design controlled experiments,
  prepare/launch/monitor runs, evaluate results, synthesize findings, audit
  methodology, or run a bounded autonomous ratchet loop. Use for
  project-agnostic model training, ablation, optimization, and research
  workflow orchestration.
metadata: {version: 1.2.0, compat: [claude-code, codex], published: [claude-marketplace]}
---

# DL Research

> **Runtimes:** Claude Code · Codex &nbsp;|&nbsp; **Published:** Claude Marketplace

Project-agnostic meta skill for Deep Learning research workflows. It defines
the research lifecycle, adapter contract, H/E identity rules, ledger shape, and
synthesis graph requirements. Project-specific infrastructure lives in a
repo-local adapter; do not hardcode ClearML, Hydra, queue names, eval scripts,
or repository paths in this skill.

**Depends on `project-meta`** (the upstream/root skill) for the canonical Task
Dispatch paradigm. This skill's `references/multi-agent-harness.md` is a domain
specialization with a self-contained floor, so it still runs if project-meta is
not installed; when both are present, project-meta is canonical.

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

## Trigger Decision

Invoke this skill when the request matches one of these shapes:

- A request to **run, design, or evaluate a DL experiment** (ablation, hyperparameter study, architecture comparison, optimization trial) with an experimental component — even a single run.
- A request to **frame a research question** for a DL project: define success criteria, scope, baseline, or budget.
- A request to **survey evidence** (existing runs, prior work, code truth) as a precursor to designing experiments — when the survey feeds an experiment plan.
- A request to **launch, monitor, or track training runs** against a study ledger.
- A request to **evaluate completed runs** against a design gate or decision rule.
- A request to **synthesize research findings** into a study conclusion or promotion decision.
- A request to **audit an existing study** for methodology soundness, protocol drift, or reproducibility gaps.
- A request to **initialize or repair project research infrastructure** (adapter, study-root config, ledger schema).
- A request to **run an autonomous ratchet loop** to improve a metric within a fixed editable surface.

Do not invoke for: pure literature surveys with no experiment plan (delegate to `deep-survey-bfs`); harness/AGENTS.md bootstrapping with no study (delegate to `project-meta`).

## Bootstrap Order

On every invocation the agent MUST load in this order:

1. This `SKILL.md` in full (always loaded).
2. Detect or confirm: phase or mode, `study-id`, study root, adapter path. State these before acting.
3. Load exactly one phase or mode file (see Phases table).
4. Lazy references — load only when the task class requires it:
   - `references/adapter-contract.md` — when no project adapter exists or backend details are unclear.
   - `references/dl-methodology-checklist.md` — for design, evaluate, and audit when methodology risk is non-trivial.
   - `references/decision-rules.md` — for design, evaluate, synthesize, and ratchet decisions.
   - `references/multi-agent-harness.md` — when a phase asks for managed clean-context review or independent reviewers.
   - `references/agent-charter.md` — only when creating a reviewer prompt or adjudicating reviewer disagreement.
5. Load templates only when scaffolding or repairing an artifact.

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

- MUST NOT skip `frame`; an audit needs a stable question, scope, budget, and
  success criteria.
- MUST NOT use `dl-research init` to create a study directory unless the user
  also asks for `frame`; init only creates or repairs the project adapter.
- MUST name the repo-local adapter and write the resolved study root in
  `index.md` for every real project study.
- MUST respect adapter patterns for branch, root, run names, editable surface,
  protected files, metric parsing, tracking, and graph generation.
- MUST treat the eval harness, metric parser, protected files, and data split
  as protocol. Changes require explicit protocol-change approval and must be
  recorded before use.
- MUST separate evidence, interpretation, and hypothesis in analytic notes.
- MUST record every run — including crashes and discarded attempts — in a
  ledger row.
- MUST include `track_id`, canonical `experiment_id` (e.g. `H1.E1`), and
  `slug` (e.g. `H1E1-<experiment-name>`) on every ledger row for H/E studies.
- MUST NOT promote a result unless the decision rule for this study permits it.
- MUST NOT change secrets or credentials as part of research workflow setup.
- MUST run `python scripts/validate_ledger.py <study-root>/runs.jsonl` before
  any phase handoff or commit that mutates `runs.jsonl`. A non-zero exit is a
  hard delivery gate — fix reported errors before proceeding.
- Default: prefer cheap probes before full training when they can answer the
  question.

## Skill Arbitration

This skill owns DL research studies with an experimental component. When a
request would also match a peer skill on this marketplace, resolve as follows
and state the resolution before acting. Never silently invoke a peer.

| Request shape | Owner | This skill's role |
|---|---|---|
| DL research study (frame → design → experiments → evaluate → synthesize), launch/monitor runs, ablation design, autonomous ratchet loop | **`dl-research`** | acts |
| Pure literature survey / comprehensive review / "research X for me" with no experimental component | **`deep-survey-bfs`** | the `survey` phase invokes it as a sub-step; do not freelance a survey here |
| Bootstrap or repair the repo's agent harness (`AGENTS.md`/`USER.md`/mirrors/hooks), or package a study's output as a target-repo artifact with provenance + delivery | **`project-meta`** | accept the hand-off; if no harness exists, run `/project-meta init` first, then resume the study |

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
- **`runs.jsonl` delivery gate is a hard MUST.** After every mutation of
  `runs.jsonl` (phases: `prepare`, `launch`, `monitor`, `evaluate`, `ratchet`),
  MUST run `python scripts/validate_ledger.py <study-root>/runs.jsonl` and fix
  all reported errors before phase handoff or commit. Non-zero exit blocks
  handoff. The validator is dependency-free and catches schema drift the eye
  misses. See `examples/sample-study/` for a passing reference.

## Output Footer

End each invocation with:

```md
**Phase**: <phase-or-mode>  **Study**: <study-id>  **Status**: <status>  **Next**: <phase|mode|done>
```

For audit:

```md
**Phase**: audit  **Study**: <study-id>  **Verdict**: aligned | warnings | drift | invalid  **Next**: <action>
```
