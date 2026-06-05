# Proposal: `autopilot` — a Project Meta mode for drift-free Goal-Mode execution

> **Status:** Proposed (design only). Author handoff doc; supersede sections as it lands.
> **Scope:** a new `/project-meta` verb + one reference + one template + 2 anti-patterns.
> **Grounding:** this proposal is reverse-engineered from a live, hand-run instance — the
> ArkDisplay *Gears MVP* build (`docs/plans/mvp-build-plan.md` + a 3-critic audit). AutoPilot
> is the generalization of what was done there by hand.

## 1. Problem

The operator wants to hand a repo to an agent that runs **continuously and unattended**
(e.g. overnight) toward a stated **Goal**, with **no human review between phases or tasks** —
the agent iterates via its own critic agents and proceeds. Today's `/project-meta` verbs don't
cover this: `init` builds the harness, `audit` reviews harness *health*, `validate`/`status`
report state — but none of them (a) produce the **executable, drift-proof plan** an unattended
run needs, nor (b) **gate** whether a Goal is even ready to be run unattended.

Two failure modes dominate unattended Goal-Mode runs:

- **AP-DRIFT-1 (proposed) — Goal drift.** Without a fixed, machine-checkable spec, the agent
  re-interprets the Goal each phase and wanders off it; small reinterpretations compound over a
  night into a demo that doesn't match the intent.
- **AP-PLAN-1 (proposed) — unfalsifiable plan.** A plan whose steps lack a **test target + data +
  accomplishment threshold** can't be self-certified; the agent either loops on "is this done?"
  or declares victory on empty/vacuous output (e.g. a smoke test that "renders" against empty data).

AutoPilot exists to eliminate both *before* the run starts, and to keep them out *during* it.

## 2. The mode (verb + sub-modes)

`/project-meta autopilot <sub-mode>`:

| Sub-mode | Mode | What it does |
|---|---|---|
| `plan` | editing | Scaffold a **Building Plan** from `templates/building-plan.md`, instantiated to the repo + the stated Goal (with provenance frontmatter, like every project-meta artifact). |
| `review` (a.k.a. `gate`) | read-only | **Audit an existing Building Plan for Goal-readiness.** Dispatch critic agents; emit a **GO / NO-GO gate** + the exact list of unresolved *requirements details, test data, protocols, and contracts* that must be nailed down before an unattended run. |
| `run` | governed loop | Execute the plan under the **anti-drift contract** (§5): per-step self-check gate, commit-per-step, critic re-review between phases, halt-and-ask hard-stops, stop-at-checkpoint, budget. |

`review` is the heart of the request: *"what still needs deciding so a continuous overnight run
won't drift."* `plan` and `run` bracket it. Read-only `review`/`status` never edit; editing lives
in `plan`/`run` (mirrors the existing read-only-vs-editing verb split).

## 3. The Building Plan template (`templates/building-plan.md`)

AutoPilot's central artifact. Generalized from the ArkDisplay worked example, every Building Plan
MUST carry these sections (the template seeds them; `review` checks them):

1. **Goal** — one statement of done, + the **non-goals** (drift fence).
2. **Run discipline** — the self-check **gate command** (and what's *excluded* + why), commit
   cadence, branch rule, push rule, and any **mechanical lockstep checklists** (closed-list
   schemas/tests, route-registration touch-points — the traps that silently red-gate a run).
3. **Tiers** — 🟢 autonomous · 🟡 autonomous-against-a-committed-fixture · 🔴 checkpoint
   (new dep / ops / live backend / push / unresolved decision).
4. **Preflight & fixtures** — exact env-setup commands + every **fixture committed or specced**
   (real path or generation spec), so no step stalls on missing data.
5. **Build order** — dependency-ordered phases; nothing references a not-yet-built artifact.
6. **Per-item verification matrix** — *every* task/Gear has **(a) test target** (exact
   command/assertion), **(b) data** (real fixture path or mock), **(c) accomplishment threshold**
   (objective, self-checkable — never human judgment).
7. **🔴 Checkpoints** — the explicit stop-and-log set.
8. **Pre-decided defaults** — the answers that keep the agent from guessing on open questions.
9. **Audit provenance** — which critics ran, what changed, and the readiness verdict.

> The template is a *contract shape*, not prose. `review` scores a plan ABSENT/PARTIAL/ENFORCED
> against §6 especially: a row missing any of test-target / data / threshold is a NO-GO blocker.

## 4. The `review` (Goal-readiness gate)

Extends the `audit` recipe's machinery (critic dispatch, severity grouping, AP-XXX-N citation),
but **forward-looking**: instead of scoring harness health, it scores *"can this Goal run
unattended without drifting?"* It dispatches diverse critics (reuse the multi-agent protocol),
each on a lens, against the plan **and the real repo** (claims must be verified, not trusted):

- **Ordering / autonomy-safety** — dependency-order bugs; stalls; **mis-tiered** items (🟢 that
  actually needs a dep/ops/decision); thrash/loop risk.
- **Verifiability + invariants** — per-item test target / data / threshold present? data actually
  *in the repo*? MUST-rule compliance (test gates, no-push, dep-approval, repo invariants).
- **Environment** — does the gate command pass *now*; is all validation data present; are reused
  engines real; what preflight is required.

Output = the four **requirement-gap categories** the operator asked for, each a concrete to-do:

1. **Requirements-doc details** still ambiguous (a spec a critic couldn't pin to a "how").
2. **Test data** missing/absent (and where it must come from — committed fixture vs operator).
3. **Protocols** undefined (the run loop, the stop conditions, the critic-review cadence).
4. **Contracts** unstated (closed-list schemas, route touch-points, the emit/acceptance shape).

…then a **GO / NO-GO** verdict. NO-GO until every §6 row is verifiable and every blocker has an
owner. (In the ArkDisplay run, this pass turned a plausible-looking plan into 5 BLOCKERs +
4 MAJORs — e.g. a promotion board seeded from a field the data didn't have, a "real RSS" smoke
test with no offline data, two flagship features that silently red-gate a closed-list contract test.)

## 5. The anti-drift contract (`run`)

Continuous unattended execution is governed by contracts that already exist in project-meta,
composed into one loop (reuse, don't reinvent):

- **Per-step self-check gate** — the plan's gate command must pass before each commit
  (the falsifiable bar; from the Building Plan §2).
- **Commit-per-green-step** — every step is a checkpoint; the run is resumable + auditable.
- **Critic re-review between phases** — the operator's "no human between steps; iterate via the
  agent's critic review" *is* the loop: at each phase boundary, dispatch a critic to check the
  phase output against the Goal + plan §6 thresholds. A failed critic → iterate, don't advance.
  This is the **drift detector** (kills AP-DRIFT-1).
- **Halt-and-ask hard-stops** — reuse `references/execution-policy.md` worker constraints: stop at
  any 🔴 checkpoint, any new-dependency need, any ambiguity not covered by Pre-decided defaults,
  any invariant collision. **Stop + log, never guess past.**
- **Phase-lock gates** — optionally back the phase boundaries with `templates/phase-lock-contract.md`
  so a phase can't be skipped or a gate bypassed.
- **Budget** — a token/time ceiling; degrade to "log remaining work + open PR" at the limit.
- **Push is always a checkpoint** — the run opens a PR; the operator merges (matches the existing
  no-push-to-main posture; never `--no-verify` silently).

## 6. How it composes with existing Project Meta

AutoPilot adds, it doesn't fork:

- **New verb** `autopilot` in `references/cli-command-patterns.md` route table.
- **New recipe** `recipes/autopilot.md` (owns the plan/review/run workflows; `review`/`status`
  read-only, `plan`/`run` editing).
- **New template** `templates/building-plan.md` (§3) + a `building-plan` artifact instantiated at
  a project path (e.g. `docs/plans/<goal>-build-plan.md`) with provenance frontmatter.
- **New reference** `references/autopilot.md` (the anti-drift contract + readiness-gate protocol).
- **Reuses:** `audit` (critic dispatch + scoring), `multi-agent-protocols` (diverse critics),
  `execution-policy` (hard-stops/halt-and-ask/budget), `phase-lock-contract` (gates),
  `pressure-testing` (pressure-test the plan's MUST/threshold rows).
- **New anti-patterns:** AP-DRIFT-1 (goal drift in unattended runs) + AP-PLAN-1 (unfalsifiable
  plan / no per-item threshold) added to `references/anti-patterns.md`.
- **Skill Arbitration:** AutoPilot is project-meta's own mode; for the *content* of a phase it still
  delegates to peers (`dl-research`, `deep-survey-bfs`, `meta-debug`) per the existing table.

## 7. Worked example (the hand-run that motivated this)

ArkDisplay Gears MVP: a Goal ("build MVPs of ArkPress/ArkLab/Arkademy/ArkWiki overnight"), a
Building Plan with per-Gear specs, then a 3-critic `review` that produced GO-blocking findings
(missing fixtures, mis-tiered live-backend steps, closed-list contract-test traps, no objective
thresholds), then an iterated v2 plan with a per-item verification matrix + committed fixtures +
🔴 checkpoints. That is exactly `autopilot plan` → `autopilot review` → (iterate) → ready-for-`run`,
done by hand. AutoPilot makes it a first-class, repeatable mode.

## 8. Open questions

- **Run engine:** does `run` drive a scripted loop (Workflow / Agents-SDK) or stay a prose loop
  with critic checkpoints? Gate on opt-in/semantic-scope per AP-COORD-4, not file count.
- **Drift metric:** is "drift" measured purely by the per-phase critic verdict, or also by a
  diff-against-Goal heuristic? Start with the critic verdict (cheap, already in the loop).
- **Resumability:** standardize the commit-per-step + a run-log so a killed run resumes cleanly.
- **Readiness score:** should `review` emit a numeric readiness score, or just GO/NO-GO + blockers?
  (Lean GO/NO-GO + blockers; a score invites gaming — cf. the `audit` "auditing for show" trap.)
