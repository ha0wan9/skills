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
| 6 | Domain critics (owning-skill self-declaration) | agent, declared by the artifact's owning skill | artifact-specific adversarial review | owning skill |

Critics 1–5 are marketplace-wide and live with `project-meta` because it owns
harness authoring. Critic 6 is a class, not a single agent: each artifact type
is judged by whatever domain critic its owning skill declares, self-declared
rather than hardcoded here — see §6 below.

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
display. FAILs any description over `--max-desc-tokens` (default 200).
`--max-invoke-tokens` (default 0 = disabled; recommend 4000 for a
root/router skill, 3000 for ordinary ones) gates the on-invoke body — it's
advisory (prints an `INVOKE>N` flag, exit code unchanged) unless paired with
`--fail-on-invoke`. Token counts are a `chars/N` estimate, not a real
tokenizer.

```bash
python3 scripts/context_cost_estimate.py . [--max-desc-tokens 200] [--max-invoke-tokens 4000] [--fail-on-invoke]
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

### 6. Domain critics — owning-skill self-declaration protocol

Artifact-specific adversarial review is not hardcoded here as a peer-path
list; it is **self-declared by the artifact's owning skill**. project-meta
does not own — and must not enumerate — which skill judges which artifact
type; that binding lives with the skill that produces the artifact.

Dispatch protocol, at audit time:

1. **Identify the owning skill** from the artifact type. Generic rule: an
   artifact belongs to whichever skill authors/consumes that artifact shape
   as its primary output. *(informative, examples only)* a `survey.md`
   belongs to the survey-producing skill; a DL study belongs to the
   research skill — these are illustrations, not a normative lookup table.
2. **Load the owning skill's own docs** (its `SKILL.md` / `references/`).
   The owning skill names, in its own documentation, the critic agent file
   it ships under its `agents/` directory. project-meta never names that
   path itself — it asks the owning skill to name it.
3. **Dispatch the declared critic** via whatever the runtime offers:
   - Claude Code: the plugin-registered agent type from the session agent
     list if the owning skill's agent is registered, or a subagent seeded
     with the agent file's content otherwise.
   - Codex: a native subagent seeded with the agent file's content.
4. **Degrade explicitly if the owning skill can't be found.** If the
   artifact's owning skill install cannot be located (skill not present,
   agent file missing), run generic critics 1–5 only and **state the
   degradation in the audit output** — do not silently skip domain review.

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

### Floor vs. orchestration

- The five deterministic critics are a **budget-independent floor** and remain
  **directly CLI-invokable on any runtime** (`python3 scripts/<critic>.py .`) —
  including Codex, which has no Claude Code Workflow tool. A `parallel()` /
  `agentType` fan-out (or a Codex Agents-SDK equivalent) is an *optional*
  orchestration over the **same** scripts, never a replacement for them. If
  audit depth is scaled to a token budget, only the reviewer-agent dimensions
  (critic 6's domain critics, extra review passes) may scale — dropping a
  deterministic floor critic under budget pressure is AP-VAL-2 (validator not
  in the gate).

### Verdict vocabulary

Two vocabularies coexist and MUST be mapped explicitly before any structured
schema entrenches a split:

- reviewer-agent critics return `pass | pass-with-warnings | block | insufficient-context`;
- the dispatch protocol (`multi-agent-protocols.md` Reviewer-Between-Subtasks) returns `PASS | SUGGEST | BLOCKER`.

Mapping: `block` ≙ `BLOCKER` (hard synchronous halt), `pass-with-warnings` ≙
`SUGGEST` (log + proceed), `pass` ≙ `PASS`, `insufficient-context` ≙ halt-and-ask
(treat as a BLOCKER for gating). Do not flatten `SUGGEST`/`pass-with-warnings`
into a binary pass/fail, and preserve `BLOCKER`'s stop semantics in any schema.

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
4. **Scripts (critics 1–5)** register directly in the
   [Suite Overview](#suite-overview) table and wire into the relevant recipe.
   **Domain critics (critic 6)** do not register here: the owning skill
   declares its critic in its own `SKILL.md`/`references/` per the §6
   self-declaration protocol — this table stays generic (a single row
   pointing at §6), never a per-skill peer-path list. One source of truth:
   this file is the catalog for critics 1–5; recipes point here rather than
   re-describing them.
