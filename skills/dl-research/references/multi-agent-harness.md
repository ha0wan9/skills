# Multi-Agent Harness

Use managed clean-context reviewers at phase boundaries where independent
judgment prevents expensive or invalid research. The lead agent remains the
orchestrator and source-of-truth owner.

## Dependency & Canon

This harness is a domain **specialization** of the canonical Task Dispatch
paradigm owned by **project-meta** (the upstream/root skill):
`project-meta/references/multi-agent-protocols.md`. This skill **declares
project-meta as a dependency**. The section below is a self-contained *floor*
so the skill works if installed alone; project-meta is canonical — on any
conflict, defer to it. (This is the single place the canon path appears; cite
the paradigm by name elsewhere.)

**Floor (works without project-meta installed):**

- **Roles**: Lead (orchestrator, owns source of truth) · Planner · Explorer
  (read-only) · Worker (edits a bounded surface) · Reviewer (independent check).
- **Context Package** = the fields of the Reviewer Packet
  (`templates/reviewer-packet.md`): goal, artifacts supplied, ownership,
  constraints, output required, review criteria.
- **Reviewer-Between-Subtasks**: brief a fresh worker → fresh, separate reviewer
  returns a verdict → lead integrates; lead does not edit inside a dispatched
  chain; rotate reviewers.
- **Ordering barrier**: parallelize only across disjoint write-sets; a dependent
  write (here, the `runs.jsonl` integration) is a lead-owned barriered step.
- **Synchronous gates**: a `block` verdict is a hard STOP-and-return — see
  [Synchronous Gates](#synchronous-gates).

### Role mapping (paradigm → dl-research)

| Paradigm role | dl-research role |
|---|---|
| Lead | the lead agent (owns `index.md`, `runs.jsonl`, launch state, verdicts) |
| Planner | the lead during `frame` / `design` |
| Explorer (read-only) | `literature-scout`, `code-truth-scout` |
| Worker (bounded edits) | the `prepare`-phase implementer (configs/scripts inside the adapter editable surface) |
| Reviewer | `design-critic`, `methodology-auditor`, `result-skeptic`, `implementation-intent-reviewer`, and the managed `methodology-critic` agent |

`templates/reviewer-packet.md` *is* the paradigm's Context Package specialized
for reviewers; the [Clean-Context Rule](#clean-context-rule) packet header is
the same shape.

### Runtime backings

One contract, per-runtime mechanical backing — behaviorally equivalent, never a
replacement for the prose loop.

| Tier | Claude Code | Codex | Floor |
|---|---|---|---|
| Model-driven dispatch | Agent tool / subagents | native subagents — reviewers/scouts on a read-only `explorer` base, `prepare` worker on `worker` | the prose Clean-Context loop |
| Scripted orchestration | Workflow (`parallel`/barrier/`resumeFromRunId`) | Agents SDK + `codex mcp` (handoffs/gating) | the prose loop |

- **Model**: dispatched reviewers/scouts/workers default to **Sonnet**; escalate
  a single agent to Opus only on a concrete signal (it already failed or
  returned low-quality output at Sonnet tier), not precautionarily.
- Read-only roles (Explorer/Reviewer) map to Codex's `explorer`; only the
  `prepare` Worker writes. `resumeFromRunId` journaling and git-worktree
  isolation are Claude-Code-only.

## Contents

- [Invocation Priority](#invocation-priority) — when to call which reviewer
- [Clean-Context Rule](#clean-context-rule) — packet header and stance
- Reviewer Roles
  - [design-critic](#design-critic) — gate experiment plans before compute
  - [methodology-auditor](#methodology-auditor) — validate study claims
  - [result-skeptic](#result-skeptic) — falsify or downgrade verdicts
  - [implementation-intent-reviewer](#implementation-intent-reviewer) —
    confirm prepared changes match intent
  - [literature-scout](#literature-scout) — external prior work
  - [code-truth-scout](#code-truth-scout) — repository and prior-run evidence
- [Synchronous Gates](#synchronous-gates) — block = hard STOP-and-return
- [Ordering Barriers](#ordering-barriers) — disjoint write-sets, barriered integration
- [Adjudication](#adjudication) — handling reviewer findings

## Invocation Priority

Mandatory when managed subagents are available:

1. `design-critic` during `design` when compute is non-trivial, claims may be
   promotable, or any intervention is multi-factor.
2. `methodology-auditor` during `audit` before adoption, for important claims,
   or when drift is suspected.
3. `result-skeptic` during `evaluate` before a promotable verdict, when results
   are surprising, or when repeats disagree.

Optional:

- `implementation-intent-reviewer` during `prepare` for non-trivial code/config
  changes.
- `literature-scout` and `code-truth-scout` during broad `survey`.
- ratchet preflight and final review; never per-iteration review.

Skip reviewers for routine `frame`, `launch`, and `monitor`.

## Clean-Context Rule

Do not give reviewers the full conversation. Give a compact packet with only
the artifacts needed for the role. Include `references/agent-charter.md` in the
packet or summarize its stance.

Required packet header:

```md
Role: <reviewer-role>
Study: <study-id>
Question: <one paragraph from index.md>
Decision needed: <what the lead agent needs from the reviewer>
Artifacts supplied:
- <path or pasted excerpt>
Output required: verdict, blocking issues, warnings, evidence references,
recommended correction, missing context.
```

## Reviewer Roles

### design-critic

Purpose: prevent bad experiment plans before compute is spent.

Packet:
- `index.md` question, success criteria, scope, budget, protocol;
- adapter summary;
- `01-survey.md` findings relevant to the shortlist;
- proposed `02-design.md` round;
- decision rules and methodology checklist excerpts.

Checks:
- fair baseline/control;
- one-factor isolation or justified multi-factor plan;
- measurable decision gates;
- seed/repetition policy;
- data version and metric direction;
- cost and dependency realism;
- out-of-scope drift.

### methodology-auditor

Purpose: independently test whether a study claim is valid.

Packet:
- `index.md` protocol;
- protocol-change table;
- active design round;
- relevant ledger rows;
- evaluation and synthesis excerpts;
- audit checklist.

Checks:
- protocol drift;
- metric/eval/data split changes;
- leakage risk;
- baseline fairness;
- repetition and noise;
- ledger completeness;
- reproducibility evidence;
- whether claims exceed evidence.

### result-skeptic

Purpose: falsify or downgrade unsupported verdicts.

Packet:
- success criteria and decision gate;
- design row for the completed run(s);
- ledger rows;
- raw metric tables or parsed summaries;
- baseline/control rows;
- seed/repetition rule.

Checks:
- verdict follows the gate;
- primary and guardrail metrics agree;
- repeats are sufficient;
- missing or failed runs are accounted for;
- effect size is not likely noise;
- complexity/cost penalty is applied.

### implementation-intent-reviewer

Purpose: confirm prepared changes implement exactly the intended intervention.

Packet:
- design row;
- adapter editable surface and protected files;
- diff or config changes;
- launch command template;
- validation output.

Checks:
- change stays inside editable surface;
- protected protocol is untouched;
- diff matches intervention and does not add extra knobs;
- reproducibility metadata is sufficient;
- launch command points at the prepared artifact.

### literature-scout

Purpose: gather external prior work without deciding the study.

Packet:
- research question;
- known baselines and constraints;
- target domain and date sensitivity.

Output:
- relevant prior findings;
- methods worth testing;
- negative results or caveats;
- citations or source links.

### code-truth-scout

Purpose: gather repository and prior-run evidence without deciding the study.

Packet:
- research question;
- adapter summary;
- paths or trackers to inspect.

Output:
- source/config facts;
- prior run facts;
- missing evidence;
- artifact references.

## Synchronous Gates

A reviewer `block` verdict is the paradigm's **BLOCKER**: a hard
STOP-and-return, not a logged annotation. The lead halts the chain and surfaces
the blocker to the user; no further dispatch (no `launch`, no promotion) until
the user decides (re-brief / re-scope / abort).

Under any scripted or background backing — a Workflow running `evaluate` /
`audit`, or the `ratchet` loop — the runner MUST stop forward progress on the
**first** `block` and return. Batch-collecting blocks to surface at end-of-run
is not acceptable: it reopens the "flaw found late" window the gate exists to
close. `resumeFromRunId` (Claude Code) or a Codex re-entry resumes *after* the
user resolves the block — it never runs past one.

Other hard STOP-and-return boundaries in this skill:

- **Protocol-change / promotion** is the user's commit-equivalent boundary; a
  runner assembles the evidence and stops — it does not self-promote a result.
- **Read-only phases** (`survey`/`audit` reviewers) must not write study
  artifacts; their backing contains no edit-capable stage by construction.

## Ordering Barriers

- Parallel **reviewers** are safe — they are read-only with disjoint outputs.
- Parallel **`prepare` workers** are safe only across **disjoint editable
  surfaces**, and must never touch protected files (eval harness, metric parser,
  data split). Overlapping surfaces need a single owner.
- `runs.jsonl` is the shared write-set: it is a **lead-owned barriered
  integration write**, never written by parallel workers in an unbarriered
  stage. This is dl-research's instance of the paradigm's canonical→barrier→mirror
  rule (worktree isolation makes an unbarriered ledger write *worse*, not safer:
  isolated workers append to stale ledgers with no merge conflict to signal it).

## Adjudication

- A `block` is a [Synchronous Gate](#synchronous-gates): address it, explicitly
  reject it with artifact evidence, or escalate to the user — do not run past it.
- Reviewer consensus never overrides raw metrics, protected protocol, or
  predeclared decision gates.
- Record reviewer verdicts in the phase artifact, not in the ledger unless they
  affect a run verdict.
