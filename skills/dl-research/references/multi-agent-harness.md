# Multi-Agent Harness

Use managed clean-context reviewers at phase boundaries where independent
judgment prevents expensive or invalid research. The lead agent remains the
orchestrator and source-of-truth owner.

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

## Adjudication

- Blocking reviewer findings must be addressed, explicitly rejected with
  artifact evidence, or escalated to the user.
- Reviewer consensus never overrides raw metrics, protected protocol, or
  predeclared decision gates.
- Record reviewer verdicts in the phase artifact, not in the ledger unless they
  affect a run verdict.
