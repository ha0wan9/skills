---
template_name: building-plan
description: "Seed for a goal-oriented, falsifiable build plan. Default floor carries a per-item verification matrix; the `autopilot`/`goal` keyword escalates it to a strict, unattended-run-readiness gate."
source_reference: references/cli-command-patterns.md
intended_project_path: docs/plans/<goal>-build-plan.md
owner: shared-user-facing
secure_derivation: required
review_policy: user-review-when-goal-or-readiness-changes
---

# Building Plan Template

Use this seed when `/project-meta plan` scaffolds a build plan for a stated Goal.
The plan is a **contract shape, not prose**: every section below exists so the plan
can be *self-certified* — an agent (or a critic in `audit`) can check it without human
judgement. A plan whose items lack a test target / data / threshold is unfalsifiable
and silently declares victory on empty output — that is AP-PLAN-1.

## Two readiness tiers

The `readiness` frontmatter field (set by the `plan` recipe) selects how strict the
plan must be. **The keyword sets it; `audit` reads it.**

| `readiness` | When | What it requires |
|---|---|---|
| `floor` (default) | any `/project-meta plan` | §6 per-item verification matrix is **mandatory** — every item has test target + data + threshold. Nothing gates it; forgetting a keyword never drops below this floor. |
| `strict` | request contains `autopilot` / `goal` / `unattended` (the self-directed discipline switch) | floor **plus** §1 non-goals fence, §3 tiers, §4 fixtures committed-or-specced, §7 🔴 checkpoints — all required. `audit`'s Goal-readiness dimension runs a **GO / NO-GO** gate before the plan is considered run-ready. |

## Project Artifact Frontmatter

```yaml
---
artifact_name: <goal>-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: project-meta/references/cli-command-patterns.md
project_scope: this repo only
owner: shared-user-facing
review_policy: user review when goal or readiness changes
last_reviewed: YYYY-MM-DD
readiness: floor            # floor | strict  — `strict` set by the autopilot/goal keyword
goal: "<one-line statement of done>"
---
```

Register the instantiated plan in the project artifact manifest (`agents/project-artifacts.md`)
so `audit` and `status` can discover it and check provenance.

## Required sections

`floor` requires §5, §6, §8. `strict` requires all nine. `audit` scores each
ABSENT / PARTIAL / ENFORCED; under `strict`, any §6 row missing test-target / data /
threshold is a **NO-GO blocker**.

1. **Goal & non-goals** — one statement of done, plus the **non-goals** (the drift
   fence: what this run must *not* wander into). *(strict: required)*
2. **Run discipline** — the self-check **gate command** (and what it *excludes* + why),
   commit cadence, branch rule, push rule, and any **mechanical lockstep checklists**
   (closed-list schemas/tests, route-registration touch-points — traps that silently
   red-gate a run). *(strict: required)*
3. **Tiers** — classify each item: 🟢 autonomous · 🟡 autonomous-against-a-committed-fixture
   · 🔴 checkpoint (new dep / ops / live backend / push / unresolved decision). *(strict: required)*
4. **Preflight & fixtures** — exact env-setup commands + every **fixture committed or
   specced** (real path or generation spec), so no step stalls on missing data. *(strict: required)*
5. **Build order** — dependency-ordered phases; nothing references a not-yet-built artifact.
6. **Per-item verification matrix** — the core. *(floor + strict: required)*

   | Item | Test target (exact command / assertion) | Data (real fixture path \| mock) | Threshold (objective, self-checkable — never human judgement) |
   |---|---|---|---|
   | <item> | `<command>` → `<expected>` | `<path or mock>` | <e.g. "exit 0 + ≥1 row asserted; not just 'renders'"> |

7. **🔴 Checkpoints** — the explicit stop-and-log set (the halt-and-ask points). *(strict: required)*
8. **Pre-decided defaults** — answers that keep the agent from guessing on open
   questions mid-run. *(floor + strict: required)*
9. **Audit provenance** — which critics ran (from `audit`), what changed, the
   GO/NO-GO verdict and date. *(strict: required; filled by `audit`)*

## Notes

- Execution governance (hard-stops, halt-and-ask, budget, push-is-a-checkpoint) is
  **not** re-specified here — it already lives in `references/execution-policy.md`.
  This plan produces the falsifiable target; whatever drives execution honors that policy.
- The §6 matrix is mechanically checkable; promoting it from prose to a linter is the
  intended next step (today `audit`'s Goal-readiness dimension checks it by hand — see
  AP-VAL-2 follow-up in `references/cli-command-patterns.md`).
