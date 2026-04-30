# <study-id>

> Master record for this DL research study. The audit phase treats the
> protocol fields as the reference unless an explicit protocol-change record
> appears below.

## Identity

- Study ID: `<study-id>`
- Owner: `<owner>`
- Created UTC: `<YYYY-MM-DDThh:mmZ>`
- Study root: `<path>`
- Branch: `<res/study-id or adapter-defined branch>`
- Adapter: `<agents/research/adapter.yaml or inline>`
- Status: `framed`
- Parent study: `<none or study-id>`

## Question

<One paragraph. State the research question and the decision it feeds.>

## Success Criteria

- Primary metric: `<name>` (`minimize|maximize`)
- Decision gate: `<observable threshold>`
- Secondary guardrails: `<metrics or checks>`
- Required repetitions: `<seed/repeat rule>`

## Scope

- In scope:
  - `<item>`
- Out of scope:
  - `<item>`

## Protocol

- Baseline/control: `<run/checkpoint/command>`
- Data version source: `<source>`
- Eval command/parser: `<command or reference>`
- Editable surface: `<paths or config areas>`
- Protected files: `<paths or rule>`
- Run naming: `<study-id>-<HnEn>-<experiment-name>`
- Budget: `<time/compute/trials/cost>`
- Stop policy: `<timeout/retry/early stop>`

## Adapter

<Inline adapter fields or link to adapter file.>

## H/E Tracks

| Track | Directory | Hypothesis / route | Status | Decision gate |
|---|---|---|---|---|
| `H1` | `H1-<track-name>/` | | | |

## Managed Review Policy

- Design critic required when: `<budget/claim/multi-factor trigger>`
- Result skeptic required when: `<promotion/surprise/repeat-disagreement trigger>`
- Methodology auditor required when: `<adoption/important-claim/drift trigger>`
- Optional reviewers: `<survey scouts, implementation reviewer, ratchet reviews>`

## Protocol Changes

| UTC | Change | Reason | Approved by | Effective from run |
|---|---|---|---|---|

## Pointers

- `01-survey.md`
- `02-design.md`
- `03-monitor.md`
- `04-evaluation.md`
- `05-synthesis.md`
- `runs.jsonl`
- `research_graph.mmd`
- `research_graph.json`
- `artifacts/`
- `audits/`
