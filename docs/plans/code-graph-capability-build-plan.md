---
artifact_name: code-graph-capability-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: project-meta/references/cli-command-patterns.md
project_scope: this repo only
owner: shared-user-facing
review_policy: user review when goal or readiness changes
last_reviewed: 2026-06-11
readiness: strict
goal: "Ship an optional `code-graph` capability in project-meta that wraps the external graphify engine (pip `graphifyy`) as a policy-governed, token-efficient code-navigation layer for target repos — reference + template seed + init/settings/status wiring + validator half-install check."
---

# code-graph capability — Build Plan

**Origin:** user goal — review the (uninstalled) "graphify" Claude plugin for usefulness to this
skill set (code navigation / token savings) and, if useful, implement it per project-meta rules.
**Verdict from due-diligence (2026-06-11):** useful, as an *optional external engine* behind a
project-meta capability — not as an installed plugin. graphify is a pip CLI, not a marketplace
plugin; per its README/docs at v0.8.x (verified 2026-06-11, see §8 trust boundary) its installer
self-modifies `~/.claude/CLAUDE.md` + `settings.json`, which our integration forbids and
replaces with harness-owned wiring.

## 1. Goal & non-goals

**Goal (statement of done):** project-meta v1.14.0 ships a fifth optional capability,
`code-graph`, install/toggle-able via `/project-meta init --code-graph` and
`/project-meta settings enable code-graph`, documented in a new
`references/code-graph-integration.md`, seeded by a new `templates/code-graph.md`
(→ target-repo `agents/code-graph.md` with provenance), detected by `status`/`settings`,
and half-install-guarded by `validate_target_harness.py`.

**Why a capability and not one paragraph of guidance** (critic round 1, scope-MAJOR-1):
the deliverable is not the preference "prefer the graph over scatter-reads" — it is the
**per-repo binding state** that preference depends on: which engine + pinned version, the
exact build command and indexed scope, the staleness rule, the gitignore decision, and the
safety prohibition, all of which differ per repo and must be visible to any agent at
navigation time. `settings`/`status` detection ("on iff present AND wired") requires a
committed, detectable artifact — a prose note in a skill reference is neither detectable
nor per-repo. This is exactly the role `agents/issue-tracking.md` plays for the
issue-tracker capability; `code-graph` follows that proven pattern at the same weight.

**Non-goals (drift fence):**
- **No vendoring / re-implementation** of graphify or any graph engine (engine vs policy split — same doctrine as the scripted-engine tier; AP-COORD-7 analog).
- **Never run `graphify install`** (the engine's self-installer), and the reference must forbid it: as of v0.8.x it appends to global `~/.claude/CLAUDE.md` and injects a PreToolUse hook into `settings.json` without graceful merge. Harness wiring is owned by project-meta artifacts only. The prohibition is **version-bound and re-verified** per the Engine Trust Boundary (§8).
- **No edits to `references/execution-policy.md`.** The read-pattern satisfaction clause lives in the capability's own reference (`code-graph-integration.md`), mirroring the issue-tracker precedent — base policy stays clean for repos without the capability. Touching execution-policy.md is a scope-expansion halt (§7).
- **No hook is part of the `code-graph` capability contract.** A future advisory hook, if ever wanted, is a separate capability increment with its own plan — it is not a deferred piece of this one.
- **No hard dependency**: every verb degrades to the existing Explorer fan-out `context-mapping` when no graph exists, the graph is stale, or `graphifyy` is absent.
- **No MCP server, Neo4j export, video/office extras** in the contract; default build is the code-only tree-sitter pass. The LLM doc-extraction pass is opt-in and flagged as costing API tokens.
- **Do not install graphify into hw-skills itself** (markdown-dominant repo, below the usefulness threshold). This repo only ships the capability.
- **No edits to other skills** (orchestration, dl-research, …).

## 2. Run discipline

- **Gate command:** `scripts/ship_plugin.sh validate` (marketplace sanity + version-bump gate + `validate_project_meta.py`). Excludes the pressure-test suite (no new MUST-rule is introduced; the reference is advisory + one validator check) — rerun it only if review upgrades a rule to MUST.
- **Branch:** `graphify-code-graph` worktree (primary worktree carries unrelated in-progress global-meta work — never touched).
- **Commit cadence:** one commit per wave (§5); push only at PR open (push is a checkpoint per `references/execution-policy.md`).
- **Capability lockstep checklist (closed list — miss one and the capability is half-shipped):**
  1. `skills/project-meta/references/code-graph-integration.md` (new; owns the read-pattern satisfaction clause, staleness & fallback, trust boundary)
  2. `skills/project-meta/templates/code-graph.md` (new seed → `agents/code-graph.md`)
  3. `skills/project-meta/recipes/init.md` (flag refs list + step 6 + output-contract line)
  4. `skills/project-meta/recipes/settings.md` (when-to-load, source-of-truth table, enable refs, quick checks — four distinct locations)
  5. `skills/project-meta/recipes/status.md` (step 7 capability inspection)
  6. `skills/project-meta/SKILL.md` (When To Load References entry + settings-trigger capability list)
  7. `skills/project-meta/scripts/validate_target_harness.py` — three sub-edits, each separately asserted: `check_code_graph` function; its registration in `main()`'s findings list; `agents/code-graph.md` added to `KNOWN_INSTANTIATED_ARTIFACTS`
  8. `scripts/validate_project_meta.py` (dev validator) — `references/code-graph-integration.md` in `REQUIRED_REFERENCES` (enforces existence + SKILL.md link). **Not** in `REQUIRED_TEMPLATES`: that set is the always-instantiated init core whose surface contract (`## Project Artifact Frontmatter` + fenced block) does not fit copy-style capability seeds — `templates/issue-tracking.md` is the precedent (verified during wave integration; first attempt to enumerate it FAILed both template checks)
  9. *(added by audit round 1 — the closed list above missed the board surface)* `skills/project-meta/scripts/board.py` harness capability detection (code-graph entry mirroring issue-tracker); `templates/board.dashboard.html` `HARNESS_CAP_META` entry; `scripts/validate_project_meta.py` `check_board_cli` five-capability assertion; re-render the derived `docs/dashboard.html` via `board.py`
- **Wave-3 ship checklist (release artifacts, not capability wiring):** `.claude-plugin/marketplace.json` version bump to 1.14.0 **required** (description unchanged — SKILL.md description does not change); board row DASH-033; plan §9 update.

## 3. Tiers

| Item | Tier |
|---|---|
| W1 reference + template (new files) | 🟢 autonomous |
| W2 wiring edits (init/settings/status/SKILL.md + both validators) | 🟢 autonomous |
| W2 `check_code_graph` verification | 🟡 against the §4 fixture **spec** (fixture is generated per spec at run time, not committed — noted for `audit`) |
| W3 board row DASH-033 via `board.py` | 🟢 autonomous (board.py is the only writer) |
| W3 bump + PR open + fresh review + land | 🔴 checkpoint — three-gate ship workflow + audit ledger gate |

## 4. Preflight & fixtures

- Preflight: `cd .claude/worktrees/graphify-code-graph` (exists, at origin/main d878ef5); `python3 --version` ≥ 3.10; `gh auth status` ok.
- **Fixture F1 (validator), three variants — generation spec:**
  ```bash
  T=$(mktemp -d); mkdir -p $T/agents; echo '# x' > $T/AGENTS.md          # variant ABSENT: no code-graph doc
  printf -- '---\nartifact_name: code-graph\ninstantiated_from: project-meta/templates/code-graph.md\nsource_reference: project-meta/references/code-graph-integration.md\nproject_scope: t\nowner: t\nreview_policy: t\nlast_reviewed: 2026-06-11\n---\n' > $T/agents/code-graph.md   # variant UNROUTED
  echo 'Code graph: see agents/code-graph.md.' >> $T/AGENTS.md           # variant ROUTED (exact-path pointer, mirroring check_issue_tracker's exact-path rule)
  ```
- **Fixture F2 (dev validator):** the repo itself — `python3 scripts/validate_project_meta.py` must stay green after all edits.

## 5. Build order

1. **Wave 1 — new artifacts:** `references/code-graph-integration.md`, `templates/code-graph.md`.
2. **Wave 2 — wiring:** `recipes/init.md`, `recipes/settings.md`, `recipes/status.md`, `SKILL.md`, `scripts/validate_target_harness.py`, root `scripts/validate_project_meta.py`.
3. **Wave 3 — ship:** board row (DASH-033), version bump (project-meta minor → 1.14.0), `ship_plugin.sh validate` → open PR → fresh-context review → audit-ledger round record → land.

Wave 1 and 2 are file-disjoint → dispatched as two parallel Sonnet workers; the Lead reviews both before Wave 3 and verifies the structural-distinctness assumptions the grep thresholds cannot (settings' four locations; init's three locations). (AP-COORD-1: the conductor does not edit once dispatch triggers.)

## 6. Per-item verification matrix

All commands run from the worktree root. `V=skills/project-meta/scripts/validate_target_harness.py`; `R=skills/project-meta/references/code-graph-integration.md`.

| Item | Test target (exact command / assertion) | Data | Threshold |
|---|---|---|---|
| reference: sections | `grep -c '^## ' $R` | repo | ≥ 6 (required headings: Engine, Install Contract, Build Contract, Read-Pattern Satisfaction, Staleness & Fallback, Engine Trust Boundary, Target-Repo Install, Uninstall — Lead verifies names) |
| reference: forbid-install rule | `grep -qiE '(must not|never) run .{0,2}graphify install' $R; echo $?` | repo | prints `0` |
| reference: read-pattern clause is precise | `awk '/^## Read-Pattern Satisfaction/,/^## Staleness/' $R \| grep -c 'context-mapping'` ≥ 1 AND `awk '/^## Staleness & Fallback/,/^## Engine Trust Boundary/' $R \| grep -cE 'stale\|fallback\|Explorer'` | repo | ≥ 3 (staleness definition + fallback + Explorer fan-out named, inside their sections) |
| reference: engine id + pin | `grep -c 'graphifyy' $R` | repo | ≥ 2 (double-y pip name + pin guidance) |
| template seed | `grep -cE 'template_name: code-graph\|intended_project_path: agents/code-graph.md' skills/project-meta/templates/code-graph.md` | repo | = 2 |
| init wiring | `grep -c -- '--code-graph' skills/project-meta/recipes/init.md` ≥ 2 AND `grep -c 'code-graph' skills/project-meta/recipes/init.md` | repo | ≥ 3 (flag refs list, step 6, output contract; Lead verifies distinctness) |
| settings: when-to-load | `grep -A3 'turn on/off' skills/project-meta/recipes/settings.md \| grep -c 'code-graph'` | repo | ≥ 1 |
| settings: source-of-truth table | `grep -cE '^\| .code-graph.' skills/project-meta/recipes/settings.md` | repo | ≥ 1 |
| settings: enable refs | `grep -cE 'code-graph → ' skills/project-meta/recipes/settings.md` | repo | ≥ 1 |
| settings: quick checks | `grep -cF 'agents/code-graph.md' skills/project-meta/recipes/settings.md` | repo | ≥ 1 |
| status wiring | `grep -cF 'agents/code-graph.md' skills/project-meta/recipes/status.md` | repo | ≥ 1 (inside step 7 — Lead verifies) |
| SKILL.md routing | `grep -c 'code-graph-integration.md' skills/project-meta/SKILL.md` ≥ 1 AND `grep -c 'code-graph' skills/project-meta/SKILL.md` | repo | ≥ 2 (When-To-Load entry + settings trigger list) |
| validator: fn + main() + provenance set | `grep -c 'check_code_graph' $V` ≥ 2 (def + findings call site) AND `grep -cF '"agents/code-graph.md"' $V` ≥ 1 (KNOWN_INSTANTIATED_ARTIFACTS) | repo | both hold |
| validator: ABSENT → PASS | run F1-ABSENT variant: `python3 $V $T` output | F1 | no line matching `code-graph.*(FAIL\|WARN)` |
| validator: UNROUTED → FAIL | run F1-UNROUTED: `python3 $V $T \| grep -qF 'agents/code-graph.md present but not routed'; echo $?` | F1 | prints `0` (exact substring, mirroring the issue-tracker message shape) |
| validator: ROUTED → clean | run F1-ROUTED: `python3 $V $T` output | F1 | no `code-graph` FAIL line |
| dev validator entries | `grep -c 'code-graph' scripts/validate_project_meta.py` | repo | = 1 (REQUIRED_REFERENCES only; capability seeds stay out of REQUIRED_TEMPLATES per the issue-tracking precedent — see §2.8) |
| dev validator green | `python3 scripts/validate_project_meta.py; echo $?` | F2 | prints `0` |
| marketplace bump (W3) | `python3 -c "import json;print([p['version'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name']=='project-meta'][0])"` | repo | prints `1.14.0` |
| board row (W3) | `python3 skills/project-meta/scripts/board.py list \| grep -c 'DASH-033'` | board store | = 1 |
| ship gate (W3) | `scripts/ship_plugin.sh validate; echo $?` | repo | prints `0` |

## 7. 🔴 Checkpoints

- **Land** — only after: validator gate 0, fresh-context review with zero blocking findings, `audit_ledger.py gate` green (Convergence MUST: BLOCKER/MAJOR findings ⇒ fix → fresh re-review, ≤ 3 re-audit rounds, no-ship at cap).
- **Scope expansion** — any file outside §2's lockstep + ship checklists ⇒ halt and surface. This **explicitly includes `references/execution-policy.md`** (fenced in §1).
- **Primary worktree** — any operation touching the dirty `global-meta-1.0` checkout ⇒ halt.

## 8. Pre-decided defaults

- **Capability name `code-graph`, not `graphify`** — generic capability, named engine: same convention as the scripted-engine tier. graphify (pip `graphifyy`, double-y; MIT; v0.8.x; solo maintainer) is the documented reference engine; alternatives (code-review-graph, LSP/MCP symbol servers) may back the same contract later.
- **Engine Trust Boundary (claims are version-bound, not eternal):** the two safety-relevant claims — (a) `graphify install` self-modifies global Claude config, (b) the default tree-sitter pass makes no LLM/API calls — were taken from the engine's README/docs/third-party reviews for v0.8.x on 2026-06-11, not from source audit. The reference carries an "Engine Trust Boundary" section requiring re-verification of both claims on any engine version change before relying on them, and the install prohibition stays in force regardless.
- **Default build = code-only tree-sitter pass** (local; no API key). The LLM doc/PDF/image pass is opt-in and the reference states it consumes API tokens of the user-configured key.
- **Staleness rule (mechanical):** the graph is stale iff `graphify-out/graph.json` mtime < `git log -1 --format=%ct` (last commit) **or** the engine version recorded in `agents/code-graph.md` ≠ installed `graphifyy` version (any tier — even a patch upgrade invalidates the cache). Stale ⇒ rebuild (`graphify --update`) before relying on it; unable/unwilling to rebuild ⇒ fall back to Explorer fan-out `context-mapping`.
- **`graphify-out/` is git-ignored in target repos** (derived, rebuildable); the committed contract is `agents/code-graph.md`, which records the pinned engine version (`pip install 'graphifyy>=0.8,<0.9'` guidance) at install time.
- **Usefulness threshold in the reference:** recommend enabling only for code-dominant repos ≳ 100 files or where `context-mapping` escalations recur; explicitly *not* for small or markdown-dominant repos (this one included).
- **`agents/memory-writeback-check.md`: no closeout line for code-graph** — the graph is a derived artifact agents rebuild, never a memory surface agents write through. (Explicit decision so the omission is not silent.)
- **Artifact registration:** this repo has no `agents/project-artifacts.md` (that manifest is a target-repo pattern); discovery here goes through the Project Board — this plan is registered via DASH-033's `--link`. Target-repo installs of code-graph DO add a manifest row (stated in the reference's install contract).
- **Single PR** carrying board row + plan + implementation (deviation from the two-PR DASH-032 cadence, chosen for a self-contained capability; noted for the reviewer).
- **Semver:** project-meta `minor` (new backward-compatible capability) → 1.14.0.

## 9. Audit provenance

- 2026-06-11 — plan drafted (strict, `goal` keyword).
- 2026-06-11 — **critic round 1** (pre-build, fresh-context panel of 2):
  - scope/over-machinery critic: 0 BLOCKER / 3 MAJOR / 3 MINOR / 1 NIT — all accepted: capability-vs-paragraph justification added (§1); `execution-policy.md` dropped from wiring, clause moved into the capability reference (§1 non-goals, §2); hook non-goal sharpened to "separate increment with its own plan"; engine-version invalidation folded into the staleness rule (§8); marketplace.json reclassified to the ship checklist; ABSENT→PASS fixture variant added (§4, §6).
  - contract/falsifiability critic: 4 BLOCKER / 7 MAJOR / 4 MINOR — all accepted: exact FAIL-substring threshold; `KNOWN_INSTANTIATED_ARTIFACTS` + `main()` registration asserted separately (§2.7, §6); installer + zero-token claims version-bound under the Engine Trust Boundary (§8); section-anchored greps replace bare counts (§6); `validate_project_meta.py` enumeration verified (REQUIRED_REFERENCES line 28 / REQUIRED_TEMPLATES line 42) and added as §2.8; memory-writeback-check decision made explicit (§8); F1 routed-variant line made exact (§4); staleness made mechanical (§8); marketplace wording fixed (§2); 🟡 tier annotated as spec-generated fixture (§3).
  - Verdict: revised in place; proceed to Wave 1. Final GO/NO-GO remains with the ship-time fresh review + audit ledger gate.
- 2026-06-11 — **waves 1+2 executed** (two parallel Sonnet workers, file-disjoint). All §6 wiring/reference/template/fixture rows reported PASS by the workers. **Integration finding (Lead):** enumerating `templates/code-graph.md` in the dev validator's `REQUIRED_TEMPLATES` FAILed `check_template_provenance` + `check_template_surface_contract` — that set carries the init-core surface contract, which capability seeds (precedent: `templates/issue-tracking.md`) do not follow. Resolved by keeping only the `REQUIRED_REFERENCES` entry; §2.8 and the §6 dev-validator row updated to the verified contract.
- 2026-06-11 — **release audit round 1** (PR #44, fresh-context reviewer): BLOCKED — 0 BLOCKER / 1 MAJOR (`board.py` + dashboard `HARNESS_CAP_META` hardcode four capabilities; `check_board_cli` asserts exactly four, silently passing the gap) / 1 MINOR (validator message says "four") / 1 NIT (two-tier template pattern undocumented — accepted residual, precedent-consistent). Fix: capability detection + dashboard meta + five-cap assertion added; lockstep §2.9 appended. Recorded in `.harness/audit-ledger.jsonl`; re-audit round 2 next.
