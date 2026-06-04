# Recipe: plan

Scaffold a goal-oriented, **falsifiable** build plan from `templates/building-plan.md`,
instantiated to this repo and a stated Goal.

> **Stability: provisional.** Promoted from the Reserved list on user-directed demand
> (one worked example so far — the ArkDisplay Gears MVP). Treat the workflow shape as
> still settling; widen scope only as more runs confirm it.

## When to load

- User invokes `/project-meta plan`
- User asks to "plan this build", "make a build plan for <goal>", or hands a Goal to
  execute and wants it pinned down before edits begin
- Before an unattended / hand-off run, to produce the target the run will be checked against

## Mode

**editing** — creates/updates a build-plan artifact under `docs/plans/`. It does **not**
execute the plan. (Reviewing an existing plan for readiness is `audit`, read-only — see
*Hand-off* below.)

## Readiness trigger (the keyword)

The plan is written at one of two `readiness` tiers. **The keyword in the request sets
the tier; the tier is recorded in the artifact frontmatter so `audit` can see it.**

- **`floor` (default)** — any plain `/project-meta plan`. The §6 per-item verification
  matrix is **mandatory** at this tier and is *not* gateable: forgetting a keyword can
  never drop a plan below the falsifiable floor (a quality floor you can forget is no
  floor — AP-SKL-2, and the whole point of AP-PLAN-1).
- **`strict`** — the request contains **`autopilot`**, **`goal`**, or **`unattended`**
  (a self-directed discipline switch for plans destined for hand-off / overnight runs).
  Set `readiness: strict` in frontmatter and require §1 non-goals fence, §3 tiers,
  §4 committed/specced fixtures, and §7 🔴 checkpoints in addition to the floor.

The keyword is the **human-facing trigger**; `readiness: strict` in the artifact is the
**audit-facing, legible record** of why the strict gate applies. Do not gate on an
invisible heuristic — the field must be present so a misfire is visible.

If the user types `autopilot` expecting an execution engine, clarify: `plan` produces the
falsifiable target and `audit` gates its readiness; **execution governance lives in
`references/execution-policy.md`** and is honored by whatever drives the run. There is no
separate run engine in this skill.

## Required references

- `templates/building-plan.md` — the artifact seed (always)
- `templates/project-artifact-manifest.md` — register the plan for provenance/discovery (always)
- `references/execution-policy.md` — when the plan must cite the gate command / hard-stops
- `references/cli-command-patterns.md` — the route + shared rules (delivery-before-commit)

## Workflow

1. **Capture the Goal** — one statement of done. Under `strict`, also capture the
   **non-goals** (the drift fence) before anything else.
2. **Derive the readiness tier** from the keyword (above) and record it in frontmatter.
3. **Instantiate** `templates/building-plan.md` at `docs/plans/<goal>-build-plan.md` with
   full provenance frontmatter (`artifact_name`, `instantiated_from`, `source_reference`,
   `project_scope`, `owner`, `review_policy`, `last_reviewed`, `readiness`, `goal`).
4. **Fill §6 for every item** — test target (exact command/assertion) + data (real
   fixture path or mock) + threshold (objective, self-checkable). This is mandatory at
   both tiers. A row you cannot fill is a gap to surface, not a row to omit.
5. **Under `strict`**, also complete §1 non-goals, §3 tiers, §4 fixtures, §7 checkpoints.
6. **Register** the plan in `agents/project-artifacts.md`.
7. **Hand off to readiness review**: tell the user to run `/project-meta audit` on the
   plan (its Goal-readiness dimension emits GO / NO-GO + the requirement-gap categories).
   `plan` writes; `audit` judges — never self-certify here.
8. **Delivery before commit** — show the build plan as a delivery (per the `deliver`
   contract) before any commit, since it is a shared-user-facing artifact.

## Output contract

- A build-plan artifact at `docs/plans/<goal>-build-plan.md` with provenance + `readiness`.
- A manifest entry registering it.
- A one-line pointer to the next step: `/project-meta audit` for the readiness gate.

## Anti-patterns

- **Unfalsifiable plan (AP-PLAN-1).** Any §6 row missing test target / data / threshold.
  Floor or strict, this is the failure the recipe exists to prevent.
- **Gating the floor behind the keyword.** The §6 matrix is mandatory at `floor` too;
  `strict` adds gates, it does not *enable* falsifiability (AP-SKL-2).
- **Self-certifying.** `plan` is editing; it must not declare a plan run-ready. Readiness
  is `audit`'s read-only call.
- **Re-inventing execution policy.** Do not copy hard-stops/budget/push rules into the
  plan; cite `execution-policy.md`.
- **Skipping delivery.** A build plan is user-facing; show it before commit (Shared
  Command Rules).
