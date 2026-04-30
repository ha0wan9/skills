# Phase: audit

Use when the user asks whether the study is valid, before broad adoption, after
surprising results, or when scope/protocol/budget drift is suspected.

## Steps

1. Read `index.md` first. Treat research question, success criteria, scope,
   protected files, metric, data split, and budget as the reference protocol
   unless an explicit protocol-change record exists.
2. Sample only the files needed for each check; do not load every artifact by
   default.
3. Load `references/dl-methodology-checklist.md` and
   `references/decision-rules.md`.
4. Load `references/multi-agent-harness.md` and run a clean-context
   `methodology-auditor` before broad adoption, for important claims, or when
   drift is suspected. Use the auditor's blocking findings as audit findings
   unless direct artifact evidence contradicts them.
5. Write an audit report from `templates/audit.md` under `audits/`.

## Required Checks

Each check is `aligned`, `warning`, `drift`, or `invalid`.

- Identity: study ID, root, ledger, and artifacts agree.
- Adapter: project adapter exists when required and its root, branch, run-name,
  metric, tracking, protected-file, and graph settings match the study.
- Protocol: metric, eval harness, parser, data split, and protected files did
  not change without approval.
- Baseline: comparisons use a fair baseline/control.
- Data integrity: split/version is known and leakage risk is addressed.
- Decision validity: verdicts follow predeclared gates and repetition rules.
- Tracking: every run, crash, and discard has a ledger row.
- Budget: cost stayed within budget or was reauthorized.
- Scope: active work still serves the framed question.
- Reproducibility: code revision, config, data version, seed, and artifacts are
  sufficient to rerun or explain why not.
- Graph consistency: `research_graph.mmd` and `research_graph.json` exist after
  synthesis and reflect the ledger's H/E tracks, experiments, verdicts, and
  final decision.

## Hand Off

Aggregate verdict:

- `aligned`: continue or close.
- `warnings`: continue after listed corrections.
- `drift`: pause launches and repair design/protocol docs.
- `invalid`: do not promote claims; rerun under a repaired protocol or fork a
  new study.
