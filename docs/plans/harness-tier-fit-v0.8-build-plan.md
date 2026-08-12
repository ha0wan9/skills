---
artifact_name: harness-tier-fit-v0.8-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: project-meta/references/cli-command-patterns.md
project_scope: this repo only
owner: shared-user-facing
review_policy: user review when goal or readiness changes; per-PR fresh-context review before land
last_reviewed: 2026-08-12
readiness: floor
goal: "v0.8 Wave 1 (tier-fit follow-through of the 2026-08-12 skill-set review): engine-handoff refreshed against the 2026 Workflow surface; project-meta de-prescription pass landed behind A/B evidence; persona-pack roster and config-root loose ends executed per resolved decisions DEC-003/DEC-004."
discovery: full
---

# Build Plan — Harness tier-fit (v0.8 Wave 1)

Follow-through of the **2026-08-12 skill-set review** (tier-fit against Fable-class sessions).
The mechanical leg already shipped in PR #79 (tier table → Sonnet 5 / Opus 5; env-probe
secret-leg false-positive fix; inbox hygiene). This wave carries the four remaining review
items. Orchestrated by `docs/plans/harness-tier-fit-v0.8-orchestration-contract.md`.

**Wave scope:** DASH-081, DASH-083, DASH-080 (gated DEC-003), DASH-082 (gated DEC-004).
**Out of wave (stay in v0.8, not review-derived):** DASH-54 (audit panel), DASH-55
(project-meta upgrade / components manifest per resolved DEC-002).

## §0 Assumption ledger

| id | statement | type | tier | impact | evidence / resolution |
|---|---|---|---|---|---|
| A-1 | Official Fable 5 migration doctrine applies to this harness: de-prescribe prior-model scaffolding, delete redundant verification steps, A/B with scaffolding removed before keeping it | stated | ESTABLISHED | high | claude-api skill `shared/model-migration.md` → "Migrating to Claude Fable 5" (cached 2026-06-24, read 2026-08-12) |
| A-2 | Phase-lock **hard** gates under `standard` profile provide enforcement margin a Fable-class session no longer needs (advisory suffices; `strict` keeps hard) | inferred | WORKING | high | Resolution path: DASH-083a A/B evidence note + 🔴 operator evidence gate — **no gate-authority edit before the gate clears** |
| A-3 | Model-tier table is current (fleet=Sonnet 5, escalation=Opus 5, conductor=Fable 5); budget_hint TIER_PRICE unchanged (output $/MTok stable across generations) | stated | ESTABLISHED | high | PR #79 merged 2026-08-12; claude-api model table (cached 2026-06-24) |
| A-4 | `known_marketplaces.json` installLocation is literal-prefix-checked per profile; the CLI does not realpath — one profile's spelling at a time is the only stable state | stated | ESTABLISHED | high | Live probe 2026-08-12: shared-canonical spelling rejected, `~/.claude-work` spelling accepted; memory `marketplace-installlocation-alias` |
| A-5 | Persona-pack removal is reversible (one-command marketplace reinstall); find-skills covers rediscovery | assumed | ESTABLISHED | low | `claude plugin` marketplace add/install semantics; pack remains in registry |
| A-6 | The `~/.agents/skills` copy is a real load path with an unknown sync mechanism (drifted to 1.28.1 while cache held 1.28.2) | uncertain | OPEN | low | DASH-082 investigation resolves: identify writer, then formalize into ship reload or retire the track |

## §5 Build order

Dependency-ordered; `W1.x` are contract rows. Fan-out only where touch-sets are disjoint.

1. **W1.1 — DASH-081** engine-handoff refresh (independent; parallel-safe with W1.2)
2. **W1.2 — DASH-083a** phase-lock A/B evidence note (independent; parallel-safe with W1.1)
3. **🔴 evidence gate** — operator reads the A/B note, green-lights or rejects the softening
4. **W1.3 — DASH-083b** de-prescription edits (references + templates/hooks + instantiated `.claude/hooks` together; only after the evidence gate clears)
5. **W1.4 — DASH-080** roster slimming (only after DEC-003 resolves; CLI-mechanical)
6. **W1.5 — DASH-082** config-root reconcile (only after DEC-004 resolves for the scope leg; spelling-rule + ~/.agents legs ride the same gated slot)
7. **W1.6 — wave review** L2 panel over the wave diff + L3 adversarial pass on W1.3
8. **W1.7 — land** via the standing validated-edit → ship → reload workflow (AGENTS.md)

## §6 Per-item verification matrix

| Item | Test target (exact command / assertion) | Data | Threshold |
|---|---|---|---|
| DASH-081 | `grep -rEn 'Sonnet 4\.6\|Opus 4\.8\|sonnet-4-6\|opus-4-8' skills/orchestration/` → no matches outside `proposals/`; emission example field names checked against the current Workflow tool schema (script/scriptPath/args/resumeFromRunId; agent()/parallel()/pipeline()/phase() opts) | live skill tree + current tool schema | zero stale model strings; zero emission-example fields absent from the current schema |
| DASH-083a | A/B note exists at `docs/plans/harness-tier-fit-ab-note.md` with: per-gate baseline behavior, softened-behavior simulation under `standard`, friction/quality delta, explicit `VERDICT: soften | keep-hard` line | `.harness/gates/*.sh` + phase-lock fixtures exercised both ways | note committed; verdict line present; every gate in `agents/phase-lock-contract.md` covered |
| DASH-083b | `HARNESS_PROFILE=standard` run of each phase-lock gate fixture → exit 0 with `WARN` (advisory); `HARNESS_PROFILE=strict` → unchanged non-zero deny; `python3 scripts/validate_project_meta.py` → exit 0 | gate fixtures under `.harness/gates/` | all three assertions hold; template + instantiated hook copies stay byte-identical |
| DASH-080 | `claude plugin list` after restart matches the DEC-003 resolution; skill-listing delta recorded in the run writeback | live plugin registry | roster == resolved keep-list; delta noted on DASH-080 |
| DASH-082 | `config_root_audit.py` (global-meta) run flags a seeded installLocation profile-mismatch fixture and emits the one-line fix; ~/.agents writer identified or track documented as retired; scope state == DEC-004 resolution | seeded fixture + live config root | audit detects + fix emitted; A-6 flipped from OPEN; scope matches decision |
| W1.6/W1.7 | `scripts/ship_plugin.sh validate` → exit 0; fresh-context review verdict CLEAN | wave diff | validate exit 0; review CLEAN; first BLOCKER halts (AP-COORD-2) |

## §7 🔴 Checkpoints

1. **Evidence gate (after W1.2):** operator reads `harness-tier-fit-ab-note.md`; W1.3 dispatches only on explicit green-light. Ambiguous evidence → default **keep-hard** (see §8).
2. **DEC-003 (before W1.4):** roster decision — resolve via `board.py decision-resolve`.
3. **DEC-004 (before W1.5):** scope-normalization decision — resolve via `board.py decision-resolve`.

Push/PR/merge fall under the standing "Validated Edit → Ship → Reload" authorization (AGENTS.md); any reviewer BLOCKER stops forward dispatch synchronously.

## §8 Pre-decided defaults

- Ambiguous or negative A/B evidence → **keep hard gates**, record the negative result as a lesson, close DASH-083 as "evidence rejected softening" — that is a valid completion.
- Gate edits always land template + instantiated `.claude/hooks` copy together (byte-identical), same as PR #79 practice.
- No AGENTS.md task-logging; run writeback goes to board items + `lesson_registry.py`.
- Worker branches per wave item; landing serialized via the land-queue discipline (`agents/land-queue.md`).
- DASH-082's three legs stay one board item; if the scope leg (DEC-004) resolves "keep local", the item completes on legs (a)+(b) alone.
