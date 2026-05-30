# Skill Critics

The single source of truth for the marketplace's **critic suite** — the
deterministic checks and adversarial reviewer agents that audit the skills
themselves. Load this when running `/project-meta validate` or
`/project-meta audit` against a skill or the whole marketplace, or when adding
a new critic.

A critic is either a **script** (deterministic, mechanically decidable; runs
in the `validate` floor) or a **reviewer agent** (judgement-based, clean
context; dispatched as an `audit` dimension). The split mirrors AP-VAL-1: a
rule that *can* be mechanically checked becomes a script; a rule that needs
judgement becomes a reviewer with an artifact-citation discipline.

## Contents

- [Suite Overview](#suite-overview)
- [Deterministic Critics](#deterministic-critics) — the `validate` floor
- [Reviewer-Agent Critics](#reviewer-agent-critics) — the `audit` dimensions
- [How Critics Wire Into Recipes](#how-critics-wire-into-recipes)
- [Adding a Critic](#adding-a-critic)

## Suite Overview

| # | Critic | Form | Enforces | Owner |
|---|---|---|---|---|
| 1 | Skill-architecture | script `skill_architecture_lint.py` | writing-skills checklist (mechanical subset), AP-SKL-4 | project-meta |
| 2 | Trigger-collision | script `trigger_collision_check.py` | AP-SKL-3 (overlap + arbitration reciprocity) | project-meta |
| 3 | Context-cost | script `context_cost_estimate.py` | always-on description budget | project-meta |
| 4 | Determinism-gap | script `determinism_gap_scan.py` | AP-VAL-1 / AP-VAL-2 | project-meta |
| 5 | Redundancy | script `cross_skill_redundancy.py` | one-source-of-truth (writing-skills) | project-meta |
| 6 | Claims-adversary | agent `deep-survey-bfs/agents/claims-adversary.md` | survey anti-hallucination contract | deep-survey-bfs |
| 7 | Methodology-critic | agent `dl-research/agents/methodology-critic.md` | DL methodology checklist, decision rules | dl-research |

Critics 1–5 are marketplace-wide and live with `project-meta` because it owns
harness authoring. Critics 6–7 are skill-specific and live with the skill
whose artifacts they judge, as plugin `agents/` (subagents component).

## Deterministic Critics

All five are standard-library-only, expose `argparse --help`, accept a skill
directory or a marketplace root, and exit `0` (clean), `1` (finding under the
gate), or `2` (path could not be resolved). Run them from the marketplace root.

### 1. `skill_architecture_lint.py` — structural floor

Mechanical subset of the `writing-skills.md` audit checklist: SKILL.md ≤250
lines, frontmatter `name`+`description`, description names a trigger, an
invariants section / Gotchas / Output Footer exist, every `scripts/*.py`
exposes argparse (AP-SKL-4), `examples/` present when `templates/` ship.
FAIL only on hard structural breaks; everything heuristic is WARN.

```bash
python3 scripts/skill_architecture_lint.py .            # whole marketplace
python3 scripts/skill_architecture_lint.py skills/dl-research
```

### 2. `trigger_collision_check.py` — AP-SKL-3

Two signals, both AP-SKL-3: (a) **arbitration reciprocity** — if skill A names
B in its Skill Arbitration section but B is silent about A, that asymmetry
FAILs (robust; phrasing-independent); (b) **trigger-phrase overlap** with no
reciprocal arbitration. Trigger surface = frontmatter `description` + any
`Trigger Decision` / `Triggers` section; intra-skill `Auto-detect` routing is
excluded so its boilerplate doesn't manufacture collisions.

```bash
python3 scripts/trigger_collision_check.py . [--ngram 3] [--min-shared 4]
```

### 3. `context_cost_estimate.py` — always-on budget

Splits each skill's token cost into **always-on** (frontmatter description,
paid every session a plugin is enabled), **on-invoke** (SKILL.md body), and
**lazy** (references + templates), mirroring Claude Code's per-component cost
display. FAILs any description over `--max-desc-tokens` (default 200). Token
counts are a `chars/N` estimate, not a real tokenizer.

```bash
python3 scripts/context_cost_estimate.py . [--max-desc-tokens 200]
```

### 4. `determinism_gap_scan.py` — AP-VAL-1 / AP-VAL-2

Finds MUST/Gotcha rules that name a backing `*.py` but no hook config
(`settings*.json`, `hooks*.json`, `*.fragment`, `hooks/*.sh`) actually
invokes — the candidates for promotion to a PostToolUse/Stop hook. Advisory by
default (gaps are expected until hooks exist); `--strict` turns gaps into
exit 1 for a gate.

```bash
python3 scripts/determinism_gap_scan.py . [--strict]
```

### 5. `cross_skill_redundancy.py` — one source of truth

Compares every `references/*.md` across skills and flags cross-skill pairs that
share **distinctive** headings (generic boilerplate like `Contents` /
`Anti-patterns` is excluded) AND have body overlap, or whose bodies exceed a
similarity ratio. Candidates for extraction into a single owner that the others
reference. Uses `difflib`; advisory by default.

```bash
python3 scripts/cross_skill_redundancy.py . [--ratio 0.5] [--min-shared-headings 2] [--strict]
```

## Reviewer-Agent Critics

Judgement-based critics are dispatched as fresh clean-context subagents (see
`references/multi-agent-protocols.md` Reviewer role and dl-research
`references/agent-charter.md`). Each runs its mechanical floor first, then does
the adversarial read the script cannot, and returns the
`reviewer-report.md` shape with the verdict vocabulary
`pass | pass-with-warnings | block | insufficient-context`.

### 6. `claims-adversary` (deep-survey-bfs)

Attacks the survey anti-hallucination contract: unbacked assertions,
quote/claim mismatch, paraphrase drift, un-sourced aggregation, hedging without
a `paper_id`. Floor: `claims_validate.py` (which deliberately does **not**
verify a quote supports its claim — that human-judgement gap is the agent's
core job). Dispatch during/after `synthesize`.

### 7. `methodology-critic` (dl-research)

Attacks a study's protocol before promotion: unfair baselines, data leakage,
metric gaming, seed/variance gaps, unrecorded protocol changes, exploratory
probes promoted as results. Floor: `validate_ledger.py`. Dispatch during
`design`, `evaluate`, `synthesize`, or `audit`.

## How Critics Wire Into Recipes

- **`recipes/validate.md`** runs the five deterministic critics as part of the
  validation floor, after `validate_target_harness.py`. Aggregate PASS/WARN/
  FAIL; a script exit 1 is a FAIL for the validate gate.
- **`recipes/audit.md`** uses critic output as audit-dimension evidence: the
  scripts feed the "Skill / harness authoring" and "Validation & enforcement"
  dimensions; the reviewer agents are dispatched when auditing a survey or a
  study artifact (not for a plain harness audit).

A critic that reports ENFORCED on a rule with no backing script or agent is
itself an AP-VAL-1 violation — mark it WARN with the actual evidence instead.

## Adding a Critic

1. Decide form via the AP-VAL-1 test: mechanically decidable → script;
   needs judgement → reviewer agent.
2. Scripts: std-lib only, `argparse --help`, exit `0/1/2`, remediation message
   on a missing dependency (AP-SKL-4). Must run cleanly against all three
   skills and any `examples/`.
3. Reviewer agents: a plugin `agents/<name>.md` with `name`+`description`
   frontmatter, the shared reviewer stance, a mechanical floor command, a
   bounded adversarial read, read-only boundaries, and the
   `reviewer-report.md` output shape.
4. Register the critic in the [Suite Overview](#suite-overview) table and wire
   it into the relevant recipe. One source of truth: this file is the catalog;
   recipes point here rather than re-describing critics.
