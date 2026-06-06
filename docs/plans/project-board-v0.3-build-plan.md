---
artifact_name: project-board-v0.3-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: docs/backlog/project-board-system.md
project_scope: this repo only
owner: shared-user-facing
review_policy: per-wave fresh-context review before land (AP-COORD-2); milestone close-out in roadmap co-review
last_reviewed: 2026-06-06
readiness: floor
goal: "Ship the v0.3 'Mirrors and orchestration' milestone: a new orchestration skill (DASH-09/10/11/22) plus project-meta's push-only Linear mirror (DASH-03) and experimental browser edit-back (DASH-13)."
---

# Project Board v0.3 — Build Plan

**Milestone:** v0.3 "Mirrors and orchestration" (6 items: DASH-03, 09, 10, 11, 13, 22). Built in **2 dependency-ordered waves**, each shipped as its own reviewable PR (the v0.1/v0.2 cadence) with a fresh-context review gate + version bump before every land.

> **Wave shape (revised during build):** the four orchestration items (DASH-09/10/11/22) are deeply interdependent — a contract you can't emit, or a budget hint with no contract, is an incoherent half-skill. They ship as **one coherent wave**. The two project-meta additions (DASH-03 mirror, DASH-13 edit-back) are independent and additive → the second wave. Two coherent waves beat three half-ones (and is lighter — fewer PRs).

> v0.1 shipped the store + CLI + dashboard. v0.2 added the grooming/review layer. v0.3 adds the **orchestration spine past the plan step** — a committed, reviewable contract that hands a chosen milestone to the engine without re-implementing it — plus the two **mirror/edit-back** surfaces (repo→Linear push, browser edit-back).

## 1. Goal & non-goals

**Done** = the goal above, with the v0.3 roadmap milestone flipped to `done` after both waves land.

**Non-goals (drift fence):**
- **No run engine.** The orchestration skill never builds its own worker pool, run-journal, or cross-turn loop. It owns *policy* (the contract); the engine (Workflow / Codex Agents-SDK / Agent-loop floor) owns *mechanism*. AP-COORD-7.
- **No autonomous engine launch.** The skill may call the Workflow tool **only** when the user invoked `orchestrate` (the two-bar opt-in). Never from a hook, never autonomously, never enabling `ultracode` session-mode.
- **No predictive budget.** DASH-22 is a coarse *hint*, explicitly "estimate, not a guarantee." No calibration claim — there is no cost corpus yet (`dispatch_ledger.py` has no token/runtime fields; adding them is a separate later item).
- **No Linear pull / two-way sync.** DASH-03 is **push-only**; reverse-drift (Linear edited directly) is documented, not pulled back. Mirror runs **interactive only**, never from the headless capture subprocess.
- **Browser edit-back is experimental,** not a canonical write path. CLI (`board.py`) stays the only canonical writer; the File System Access API path is a convenience with a download-fallback.

## 2. Run discipline

- **Gate command per wave:** `scripts/ship_plugin.sh validate` (marketplace sanity + version-bump gate + `validate_project_meta.py` when project-meta changed) → exits 0. Plus `python3 skills/project-meta/scripts/skill_architecture_lint.py` over the new skill.
- **Branch/PR rule:** one PR per wave from this worktree branch; **fresh-context review agent** over the diff (gate 3) before `land`; merge only if clean.
- **Version bump (mechanical lockstep):** every wave bumps a version in `.claude-plugin/marketplace.json` — the new `orchestration` plugin in Wave 1, `project-meta` in Wave 2 (when project-meta changes).
- **Route-registration touch-points (lockstep):** a new skill MUST land in all of: its own `SKILL.md`, a `marketplace.json` plugin entry (description copied **verbatim** from SKILL.md frontmatter), the `AGENTS.md` routing table, `README.md`, and the marketplace `metadata.description`. Missing any one = stale manifest.

## 3. Tiers

- 🟢 **autonomous:** budget_hint script (DASH-22), references/templates authoring, dashboard edit-back JS (DASH-13).
- 🟡 **autonomous-against-a-committed-fixture:** `budget_hint.py` unit acceptance; skill-architecture lint; marketplace JSON parse.
- 🔴 **checkpoint:** each wave's **land** (push + merge = a push checkpoint); the DASH-03 Linear mirror touches a live external backend → **dry-run/plan only by default**, real push is a 🔴 the operator triggers.

## 4. Preflight & fixtures

- No new env. Python 3 stdlib only (matches `board.py`, `review_tier.py`).
- Fixture for budget_hint acceptance: synthetic task specs passed as CLI args (`tier:class:fanout`), no file needed.
- Fixture for edit-back: the existing `templates/board.dashboard.html` + the dogfood store under `docs/backlog/`.

## 5. Build order (waves)

### Wave 1 — The orchestration skill (DASH-09/10/11/22) *(complete, coherent skill: produce → sign → emit)*

| Item | Deliverable | Acceptance (falsifiable) |
|---|---|---|
| **scaffold** | `skills/orchestration/SKILL.md` — frontmatter (name `orchestration`, verbatim description), trigger policy, `orchestrate` route, **thin Dependency & Canon floor** citing project-meta canon via a single swappable pointer + the **review-tier pointer** (resolves the open question); Cross-Cutting Invariants + Gotchas + Output sections | `skill_architecture_lint.py` → 0 WARN/FAIL; floor names roles + the one pointer |
| **DASH-10** | `references/orchestration-contract.md` — the contract **schema, single owner**: per task → model tier · parallelization · orchestrator effort · human-in-the-loop checkpoints · review level (review-tier L0–L3) · budget hint | reference exists; schema enumerated once; linked from SKILL.md + recipe + template |
| **DASH-10** | `templates/orchestration-contract.md` (seed) + `examples/sample-orchestration-contract.md` (filled, **signed** instance) | template uses the seed convention; the **example** passes `provenance.py check`; both carry the per-task table matching the schema |
| **DASH-22** | `scripts/budget_hint.py` — coarse non-predictive hint: per-task `tier × class-band × fan-out`, summed to **wide low/expected/high**, always prints "estimate, not a guarantee" | `budget_hint.py --task cli:lint:1` → 0 tokens; `--task opus:hard:1` → nonzero low<expected<high; disclaimer always printed; `--json` emits machine output; does NOT reference an engine `budget` |
| **DASH-09** | `recipes/orchestrate.md` — for a chosen milestone: reuse project-meta `plan` build-plan + produce an orchestration plan; fill the contract per task; run `budget_hint`; set review levels; **produce → sign → emit** | recipe routes from SKILL.md; cites `plan`, review-tier, budget_hint, engine-handoff |
| **DASH-11** | `references/engine-handoff.md` — signed contract → engine emission. **Two-bar opt-in posture** (user-invoked skill naming the tool + cost surface → MAY call Workflow; does NOT enable `ultracode`, NOT autonomous/hook-driven). **Cross-runtime:** Claude Code Workflow / Codex Agents-SDK / **Agent-Task subagent-loop floor** (AP-VAL-1). AP-COORD-7: contract=policy, engine=mechanism. The compliant replacement for the killed `autopilot` run-engine. | reference enumerates the three backings + floor; states the opt-in bars explicitly; no self-built run loop |
| **parity** | `agents/openai.yaml` — Codex parity stub naming the Agents-SDK backing | present; matches the shape of other skills' `agents/openai.yaml` |
| **wiring** | marketplace entry + `AGENTS.md` + `README.md` + metadata.description + metadata.version bump | marketplace.json parses; skills path resolves to a dir with SKILL.md; name unique; description **verbatim** from SKILL.md |
| **plan** | this build-plan doc | committed |

**Wave-1 gate:** `ship_plugin.sh validate` green, `skill_architecture_lint.py` 0 WARN/FAIL, fresh-context review CLEAN, new `orchestration` plugin at `0.1.0` + marketplace `metadata.version` bumped.

### Wave 2 — project-meta mirrors + browser edit-back

| Item | Deliverable | Acceptance |
|---|---|---|
| **DASH-03** | push-only Linear mirror in project-meta: a recipe/reference reusing the **issue-tracker Track Loop** (`references/issue-tracking-integration.md`); repo canonical → Linear; body **links back**; mirror `linear_id`; **push-only** (reverse-drift documented); **interactive only**, never headless | reference/recipe exists; states push-only + interactive-only; a `board.py` mirror-plan/export path lists items to push **without** performing a live write by default |
| **DASH-13** | browser edit-back in `templates/board.dashboard.html`: edit status/fields → write back via **File System Access API** where supported, **download-patched-store fallback** elsewhere; experimental; CLI stays canonical | dashboard offers an edit affordance; uses `showSaveFilePicker`/`File System Access API` with a download fallback; a banner marks it experimental + CLI-canonical; zero new client deps |
| **harness** | `validate_target_harness.py` / `validate_project_meta.py` coverage for any new project-meta artifacts; provenance on new files | validators cover the new files; green |

**Wave-2 gate:** validate green, fresh review CLEAN, `project-meta` minor bump. Then roadmap co-review flips **v0.3 → done**.

## 6. Per-item verification matrix

| Item | Test target (exact command / assertion) | Data | Threshold |
|---|---|---|---|
| scaffold | `python3 skills/project-meta/scripts/skill_architecture_lint.py skills/orchestration` (or repo-wide) | new skill dir | exit 0, no ERROR for orchestration |
| DASH-22 | `python3 skills/orchestration/scripts/budget_hint.py --task cli:lint:1` | CLI args | prints 0 expected tokens + disclaimer; exit 0 |
| DASH-22 | `python3 skills/orchestration/scripts/budget_hint.py --task opus:hard:1 --task sonnet:review:4 --json` | CLI args | JSON with low<expected<high, all >0; disclaimer field present |
| DASH-10 contract | `python3 skills/project-meta/scripts/provenance.py check skills/orchestration/examples/sample-orchestration-contract.md` | filled example (templates are seeds, exempt) | exit 0 (required keys present) |
| manifest | `python3 -c "import json,sys; json.load(open('.claude-plugin/marketplace.json'))"` + every `skills:[]` path has a SKILL.md + unique names | marketplace.json | exit 0; orchestration entry present; description == SKILL.md description |
| DASH-13 | grep the rendered/template HTML for `showSaveFilePicker` + a download fallback + an "experimental" banner | dashboard template | all three present; no external `<script src>` added |
| DASH-03 | grep the mirror reference for "push-only" + "interactive" + "links back"; mirror CLI path runs **dry-run** without network | reference + board.py | dry-run lists items, performs no live write |

## 7. 🔴 Checkpoints

- Each wave's `land` (push + merge).
- DASH-03 **live** Linear push (external backend) — default is dry-run/plan; real push is operator-triggered.
- Any decision to widen budget_hint into a *predictive* forecast — out of scope; stop and ask.

## 8. Pre-decided defaults

1. **Skill home = new `orchestration` skill** (operator-confirmed this session; honors the locked split). Consumes project-meta + review-tier via the root-skill pointer.
2. **Open question resolved — review-tier cross-skill pointer shape:** the orchestration skill cites `project-meta/references/review-tier.md` from **one** "Dependency & Canon" block (the single swappable pointer), and names the L0–L3 levels in the contract schema; it does **not** copy the tier table.
3. **Budget-hint envelope:** `low = expected × 0.3`, `high = expected × 3` (order-of-magnitude band per the critic's non-predictive finding). Bands are heuristic constants in the script, labeled as such.
4. **Linear creds in headless capture (open question):** capture writes the **repo only**; the mirror runs interactive (matches v0.2 wave-3 capture decision).
5. **Wave order:** orchestration core first (the headline + harder design), mirrors/edit-back last (independent, additive).

## 9. Audit provenance

_Filled per wave by the fresh-context review gate (gate 3). Each wave records: reviewer verdict (CLEAN / blocking), what changed, land date._

---

*Build order is dependency-driven. Each wave lands independently behind a fresh review. v0.3 closes when both waves are merged and the dogfood roadmap shows the v0.3 milestone `done`.*
