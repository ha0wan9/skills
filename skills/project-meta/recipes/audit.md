# Recipe: audit

Review harness health, layering, triggers, mirrors, and memory boundaries. Surface fixes as recommendations.

## When to load

- User invokes `/project-meta audit`
- Recurring agent-behaviour failures suggest the harness has structural drift
- Periodic scheduled review (the AP-LIFE-3 cadence)
- After major refactors or framework upgrades

## Mode

**read-only by default** — produces findings + repair recommendations. The user (or a follow-up `/project-meta init` invocation) does the actual edits. Switch to editing only with explicit consent on a specific finding.

## Required references

Load only the references relevant to the audit target:

- [`references/harness-engineering.md`](../references/harness-engineering.md) — audit checklist + redesign triggers (always)
- [`references/anti-patterns.md`](../references/anti-patterns.md) — name failures by AP-XXX-N when they match (always)
- [`references/repo-memory-structure.md`](../references/repo-memory-structure.md) — when memory layout is in scope
- [`references/mirrors-and-updates.md`](../references/mirrors-and-updates.md) — when mirrors are in scope
- [`references/writing-skills.md`](../references/writing-skills.md) — when auditing a skill (not a project)
- [`references/skill-critics.md`](../references/skill-critics.md) — when auditing a skill/marketplace; the critic suite that feeds the authoring + enforcement dimensions
- [`references/multi-host-manifests.md`](../references/multi-host-manifests.md) — when host manifests are in scope
- [`templates/building-plan.md`](../templates/building-plan.md) — when the audit target is a build plan (the Goal-readiness dimension below)

## Audit dimensions

Score each dimension as **ABSENT / PARTIAL / ENFORCED**.

### Memory layer

- [ ] Bootstrap file is short (≤200 lines), is a router, and routes to topical files (AP-MEM-1)
- [ ] Canonical-vs-mirror selection follows the tool-awareness rule (Claude Code primary → CLAUDE.md canonical; otherwise → AGENTS.md canonical)
- [ ] Mirrors carry generation banners; no rule lives only in a mirror (AP-MEM-2)
- [ ] No stale rules layered over new ones; no contradictions (AP-MEM-3)
- [ ] No session logs / time-stamped notes accumulating in canonical memory (AP-MEM-4)
- [ ] Topical files (`agents/*.md`) are narrow enough that the agent loads only relevant context per task

### Skill / harness authoring (when auditing a skill)

- [ ] `SKILL.md` ≤250 lines (`writing-skills.md` rule)
- [ ] Frontmatter description names every distinct capability + trigger condition
- [ ] Trigger bullets are shape-based, disjoint from peer skills
- [ ] Skill Arbitration table present if any peer could partially match
- [ ] Core Rules use MUST for invariants; "Default:" or unmarked for the rest (no AP-SKL-2)
- [ ] Procedures longer than one line live in references, not in `SKILL.md` (no AP-SKL-1)
- [ ] References cite anti-pattern IDs when fixing a named trap
- [ ] Scripts have argparse `--help` + remediation message on missing dependencies
- [ ] At least one `examples/` entry for any skill producing non-trivial artifacts (AP-SKL-4)

### Coordination

- [ ] Multi-file harness edits in an editing recipe (`init`) dispatch via subagents (AP-COORD-1)
- [ ] Reviewer subagent runs between implementation subtasks (AP-COORD-2)
- [ ] Plans are kept current as execution proceeds (AP-COORD-3)
- [ ] No over-orchestration: scripted engine (Workflow / Agents-SDK) is gated on opt-in or semantic scope, not raw file count (AP-COORD-4)
- [ ] **Prose dispatch protocol is intact and runtime-agnostic**; any Claude-Code-only Workflow fast path has a named backing on each declared compat runtime (Codex Agents-SDK / `.codex/agents/*.toml`) **or** a prose fallback. Score **ABSENT** if a Workflow is the *only* documented path (AP-VAL-1 / AP-SKL-4 cross-runtime regression)
- [ ] Read-only verbs (`status`/`validate`/`deliver`/`audit`) contain no edit-capable stages; editing is owned by `init` / a dedicated editing verb

### Validation & enforcement

- [ ] `validate_target_harness.py` runs cleanly; every check is PASS or WARN with explicit acknowledgement
- [ ] Repeated mistakes have been promoted from prose to scripts/linters/hooks/templates (AP-VAL-1)
- [ ] Validators are wired into the delivery contract (AP-VAL-2)
- [ ] Pressure-test methodology has been applied to MUST rules (AP-VAL-3) — see `scripts/pressure_test_skill.py`

### Goal-readiness (when the audit target is a build plan)

Forward-looking readiness gate for a `/project-meta plan` artifact — *"can this Goal run
to completion without drifting or self-declaring victory on empty output?"* Verify against
the **real repo**, not the plan's claims. Run this dimension when the target is a build
plan; required when its frontmatter is `readiness: strict`.

- [ ] **Every §6 row is falsifiable** — has a test target + data + threshold; any row
      missing one is a NO-GO blocker (AP-PLAN-1)
- [ ] Named test data / fixtures **actually exist in the repo** (or are specced with a
      generation command), not assumed
- [ ] Tiers are honest — no 🟢 item that actually needs a new dep / ops / live backend /
      unresolved decision (mis-tier = a stall or a silent red-gate mid-run)
- [ ] `strict` plans carry the §1 non-goals fence, §4 committed/specced fixtures, and
      §7 🔴 checkpoints
- [ ] The gate command in §2 passes *now* against the current repo
- [ ] Provenance frontmatter + manifest entry present (`readiness`, `goal`, the standard fields)

Emit, in addition to the severity grouping, the **four requirement-gap categories** and a
**GO / NO-GO** verdict: (1) requirements-doc details still ambiguous, (2) test data
missing/absent + where it must come from, (3) protocols undefined, (4) contracts unstated
(closed-list schemas, route touch-points, emit/acceptance shape). NO-GO until every §6 row
is verifiable and every blocker has an owner. Do **not** emit a numeric readiness score —
GO/NO-GO + blockers only (a score invites gaming, cf. "Auditing for show" below).

### Lifecycle

- [ ] Init walks the questionnaire before rendering `USER.md` (AP-LIFE-1)
- [ ] Lessons from reviews / failures / corrections write back to canonical memory (AP-LIFE-2)
- [ ] Periodic audit cadence is defined and observed (AP-LIFE-3)

## Workflow

1. **Scope the audit**: full harness, single skill, mirrors only, etc. Default scope = full harness.
2. **Run `validate_target_harness.py`** as the structural floor — record PASS/WARN/FAIL. When the target is a skill or the marketplace, also run the deterministic critic suite (`references/skill-critics.md`); its output is the mechanical evidence for the *Skill / harness authoring* and *Validation & enforcement* dimensions below.
3. **Dispatch reviewer-agent critics** when the audit target includes a survey or a study artifact: `deep-survey-bfs/agents/claims-adversary.md` for a `survey.md`, `dl-research/agents/methodology-critic.md` for a study. Skip for a plain harness/memory audit.
4. **Walk the dimensions** above, scoring each item.
5. **Group findings** by severity (BLOCKER / MAJOR / MINOR / NIT) and by owner (template, reference, script, instantiated artifact, mirror).
6. **Cite anti-pattern IDs** for every finding that matches a named pattern. Findings without a matching AP-XXX-N are candidates for adding new entries to the catalog.
7. **Recommend the next command**: typically `init` for missing artifacts, targeted edits for structural issues, or a follow-up `audit` after the user fixes findings.

## Output contract

Structured findings report:

```
### Audit summary
- Scope: <full harness | skill: <name> | mirrors only | ...>
- Score: <ENFORCED N / PARTIAL N / ABSENT N> across <total> dimensions
- Validation: <PASS | WARN | FAIL>

### BLOCKER findings (cannot ship)
- [<dim>] <finding> — AP-XXX-N — <repair>

### MAJOR findings
- [<dim>] <finding> — AP-XXX-N — <repair>

### MINOR / NIT findings
- ...

### Anti-pattern catalog gaps
<failures observed that don't match a named AP; candidates for catalog additions>

### Recommended next steps
1. <command + scope>
2. ...
```

The report is the artifact. The user reviews, decides what to fix, and invokes the relevant follow-up command.

## Anti-patterns

- Auditing for show. If every audit reports ENFORCED on every dimension, either tighten checks or audit cadence too high.
- Audit-as-prose. Audit findings without AP-XXX-N citations and concrete repairs degrade to opinion.
- Mixing audit + repair. Audit reports findings; repair runs in the appropriate editing recipe with explicit user consent.
- Skipping the validation floor. An audit that doesn't first run `validate_target_harness.py` misses mechanical findings the human eye doesn't catch.

## Cadence

Recommended audit cadence:

- Per-project: every quarter, or when recurring agent failures suggest harness drift
- Per-skill: before each release; after any structural refactor; when a peer skill is added that could collide
- Across the marketplace: after adding/removing a plugin, or when multi-host parity drifts
