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

**Base** — loaded when the verb runs:

- [`references/harness-engineering.md`](../references/harness-engineering.md) — audit checklist + redesign triggers (always)
- [`references/anti-patterns.md`](../references/anti-patterns.md) — the AP-XXX-N catalog; the scoring rubric consulted while walking the dimensions (step 4) and naming findings (step 6) (always)

**Lazy-load** — only when the named step needs it:

- [`references/repo-memory-structure.md`](../references/repo-memory-structure.md) — when memory layout is in scope (load only here)
- [`references/mirrors-and-updates.md`](../references/mirrors-and-updates.md) — when mirrors are in scope (load only here)
- [`references/writing-skills.md`](../references/writing-skills.md) — when auditing a skill (not a project) (load only here)
- [`references/skill-critics.md`](../references/skill-critics.md) — when auditing a skill/marketplace; the critic suite that feeds the authoring + enforcement dimensions (load only here)
- [`references/multi-host-manifests.md`](../references/multi-host-manifests.md) — when host manifests are in scope (load only here)
- [`references/review-tier.md`](../references/review-tier.md) — step 3 (dispatch reviewer critics) / step 8 (convergence loop): pick the right review level (L0–L3); `scripts/review_tier.py` suggests a floor, the conductor escalates on judgment (load only here)
- [`templates/building-plan.md`](../templates/building-plan.md) — when the audit target is a build plan (the Goal-readiness dimension below) (load only here)

## Audit dimensions

Score each dimension as **ABSENT / PARTIAL / ENFORCED**.

### Memory layer

- [ ] Bootstrap file is short (≤200 lines), is a router, and routes to topical files (AP-MEM-1)
- [ ] Canonical-vs-mirror selection follows the tool-awareness rule (Claude Code primary → CLAUDE.md canonical; otherwise → AGENTS.md canonical)
- [ ] Mirrors carry generation banners; no rule lives only in a mirror (AP-MEM-2)
- [ ] No stale rules layered over new ones; no contradictions (AP-MEM-3)
- [ ] No session logs / time-stamped notes accumulating in canonical memory (AP-MEM-4)
- [ ] Topical files (`agents/*.md`) are narrow enough that the agent loads only relevant context per task
- [ ] Referential citations in memory files resolve to real repo paths — run `memory_staleness.py --target-root <repo>` (the staleness lint feeds this dimension; STALE rows indicate paths that no longer exist)

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
- [ ] Lesson-lifecycle forget leg has run (AP-LIFE-2/3 mechanization): when `.harness/lessons.jsonl` exists, run `lesson_registry.py trim-candidates` and `lesson_registry.py auto-demote` (draft mode) and review their suggestions — demotion drafts print their evidence inline; retirements go through the board inbox

### Goal-readiness (when the audit target is a build plan)

Forward-looking readiness gate for a `/project-meta plan` artifact — *"can this Goal run
to completion without drifting or self-declaring victory on empty output?"* Verify against
the **real repo**, not the plan's claims. Run this dimension when the target is a build
plan; required when its frontmatter is `readiness: strict`.

- [ ] **§0 assumption ledger present and complete** — absent or empty on a multi-file
      goal is a NO-GO; any high-impact OPEN assumption row unresolved is a NO-GO (AP-PLAN-2)
- [ ] **Every §6 row is falsifiable** — has a test target + data + threshold; any row
      missing one is a NO-GO blocker (AP-PLAN-1)
- [ ] `risk_band` / `readiness` consistency — MAJOR finding when `risk_band` ∈
      {incremental, spike-first} is recorded in frontmatter but `readiness: floor`
      (risk assessment recommended more care than the keyword set; visible tier misfire)
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
8. **Convergence loop — final audits are multi-round (MUST).** When the audit gates a
   ship/release and fixes were applied for any BLOCKER or MAJOR finding (out of band, via
   the appropriate editing verb with explicit user consent — never by this read-only
   recipe), re-run the audit over the changed scope with **fresh reviewer context** —
   fixes are themselves new changes and can introduce new findings; one pass over a
   moving target is not a clean audit. Loop fix → re-audit until a round reports
   **zero BLOCKER and zero MAJOR**, capped at **3 re-audit rounds** (Round 1 = initial
   pass; re-audits are Rounds 2–4; the cap triggers at Round 4). At the cap with
   BLOCKER/MAJOR still open: do **not** ship — hand the operator the residual findings
   plus the round-by-round trail. MINOR/NIT findings never force another round.
   Re-audit scope = the fix delta plus any file or section that references the changed
   item; escalate to full-scope only when a fix moves content across recipe/reference
   boundaries.

   **Mechanical leg — MUST record rounds in `scripts/audit_ledger.py`.** Open a
   transaction when and ONLY when the audit gates a ship/release — ordinary L1/L2
   delivery reviews MUST NOT record rounds here (that boundary is what keeps the gate
   meaningful). Per round: `audit_ledger.py record --round N --gate release --blockers X
   --majors Y [--findings "slug,slug"]` — the first row opens the transaction, rounds are
   sequential, and finding slugs preserve identity across rounds (are Round 3's two
   blockers the same two from Round 1, or fresh regressions?). Mid-fix turns:
   `record --ack --round N` (one per round; an auditable ledger row, not a marker file).
   Converged: `record --final`. At the cap with residuals the only path is the operator
   override `record --final --accept-residuals "reason"` — persistent and reviewable.
   Enforcement: `verify-before-stop.sh` step 6 (advisory in standard, blocks in strict)
   and the `ship_plugin.sh land` hard gate. The only compliant land path is
   `ship_plugin.sh land`; merging directly via `gh pr merge` bypasses the gate and is a
   policy violation.

## Output contract

Structured findings report:

```
### Audit summary
- Scope: <full harness | skill: <name> | mirrors only | ...>
- Round: <n> (1 = initial pass; 2–4 = re-audit rounds after BLOCKER/MAJOR fixes; cap at Round 4 — Convergence loop, workflow step 8)
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
- Single-pass final audit. Fixing BLOCKER/MAJOR findings and shipping on the strength of the original report means the fixes themselves were never audited. Final audits loop until clean (Convergence loop, workflow step 8).

## Loop-Contract Conformance

The Convergence loop (workflow step 8) is a declared loop per
[`references/loop-contract.md`](../references/loop-contract.md) — the
canon-writer conforms to its own canon (self-citation, no exemption).
Inline floor: **trigger** = a ship/release-gating audit with BLOCKER/MAJOR
fixes applied; **goal** = a round reporting zero BLOCKER and zero MAJOR;
**budget** = 3 re-audit rounds (cap at Round 4); **verification** =
computational floor `audit_ledger.py gate` (deterministic exit code) +
inferential fresh-reviewer critique per round; **state** = the audit ledger
JSONL, one row per round; **stopping rule** = converged (record `--final`)
or capped with residuals handed to the operator (`--accept-residuals`),
never silent.

## Cadence

Recommended audit cadence:

- Per-project: every quarter, or when recurring agent failures suggest harness drift
- Per-skill: before each release (multi-round per the Convergence loop, workflow step 8); after any structural refactor; when a peer skill is added that could collide
- Across the marketplace: after adding/removing a plugin, or when multi-host parity drifts
