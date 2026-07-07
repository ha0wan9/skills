---
artifact_name: model-tier-routing-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: project-meta/references/multi-agent-protocols.md#model-tier
project_scope: this repo only
owner: shared-user-facing
review_policy: user review when goal or readiness changes
last_reviewed: 2026-07-07
readiness: floor
critic_panel: 2x sonnet (adversarial + scope/AP-COORD-5), 2026-07-07 — 2 BLOCKER + 6 MAJOR findings folded into rev 2 (see §6)
goal: "Close the prose-vs-mechanics gaps in per-model-tier routing: (1) an advisory dispatch-tier guard hook that surfaces silent session-model inheritance at Agent-dispatch time, (2) a mechanical read leg for retro-inspect tier promotion in dispatch_ledger.py, (3) a unified tier vocabulary (cli|haiku|sonnet|opus|fable) across the routing-policy docs with one model-mapping point — plus: haiku utility rung, tier-mix auto-computation with <80% WARN in budget_hint, and per-backing effort mapping."
---

# Model-tier routing — Build Plan (rev 2, post-critic)

**Origin:** operator review (2026-07-07) of per-model-tier routing at dispatch time. The canon
(`multi-agent-protocols.md#model-tier`) is mature — three tiers, two-axis (model × effort),
escalate-on-signal, ≥80% fleet token-share, retro-inspect promotion — but key rules have **no
mechanical leg**, and the tier vocabulary is fragmented. Same failure class token-diet D5 fixed:
prose MUST-rules whose only enforcement is model memory.

**Rev 2 delta (critic panel):** hook is advisory-only at every profile (no deny in v1);
promotion-record storage does NOT move to lesson_registry (descoped to backlog — no structural
fit today); WP3 explicitly owns the canon-coherence edits ("three tiers" sentence, 80%-target
definition, haiku's relation to the promotion ladder); tier-mix keeps the shipped footer format.

## §0 Assumption ledger

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A1 | Agent-tool dispatches that omit `model` inherit the session model by default; the exact resolution chain (agent-definition frontmatter, session default) is NOT visible in the PreToolUse payload. | Agent tool contract ("If omitted, uses the agent definition's model, or inherits from the parent"); hooks payload = `{prompt, description, subagent_type, model?}` only. | Hook stays advisory (it already is); wording of the WARN adjusts. |
| A2 | Custom agent types may carry `model` in frontmatter, invisible to the hook. Built-ins (Explore/Plan) may also resolve models internally. | Agent-definition frontmatter supports `model:`; resolution undocumented. | Advisory-only design already absorbs this. |
| A3 | `dispatch_ledger.py query` surfaces neither `tier` nor `task_type`; `validate`/`gate`/`overlap` never parse `tier`. | Verified in source 2026-07-07 (cmd_query prints utc/role/verdict/comment; cmd_validate ignores tier). | WP2 re-verifies before editing. |
| A4 | Haiku 4.5 output price $5/MTok; Sonnet 4.6 $15; Opus 4.8 $25; Fable $50. | claude-api model table (cached 2026-06-24), read 2026-07-07. | Adjust `TIER_PRICE` only. |
| A5 | **(flipped by critic)** lesson_registry has NO structural fit for tier-promotion records (no `task_type` field; `applies_below` = session-tier visibility filter, not start-tier; candidate→enforced ladder ≠ per-task-type evidence accumulation). | Critic B finding #1, verified against lesson_registry.py schema. | — already on the fallback branch: repo-memory prose stays canonical; registry fit goes to backlog. |
| A6 | Workflow `agent()` accepts `opts.effort`; the Agent tool has no effort param. | Workflow/Agent tool contracts. | WP3 note wording adjusts. |
| A7 | Workflow-internal `agent()` fan-out does NOT pass through the PreToolUse `Agent`/`Task` matcher — only the top-level `Workflow` call is hook-visible. The hook therefore does not cover the scripted-engine path at all. | Critic A finding #2; PreToolUse tool-name enumeration. | If it turns out internal calls DO fire the matcher, the hook simply covers more than promised — no harm. |

## §1 Non-goals

- **No new dispatch engine/router/classifier** (AP-COORD-5). Tier selection stays Lead judgment.
- **No deny path in the hook, v1.** The PreToolUse payload cannot see frontmatter/session model
  resolution (A1/A2), so any deny would false-positive on legitimate flows (incl. Explore/Plan
  built-ins). v1 is advisory at every profile; a strict deny may be revisited only with evidence
  that `tool_input.model` is a reliable signal (board item).
- **Workflow fan-out is unguarded by the hook (A7).** The engine-path lever is the orchestration
  contract's per-task tier table + budget_hint tier-mix, not PreToolUse. No script static analysis.
- **`pre-tool-guard.sh` is not extended** — it is Bash-matcher-only and its parsing is
  shell-command-shaped; a separate script is the correct minimal unit, not "add before extend".
- **No lesson_registry schema change in this run.** Promotion records stay in repo memory per
  current canon; a structured registry fit (task_type field + query verb) is a backlog item.
- **Out-of-scope drift surfaces, deliberately:** `render_host_manifests.py` Codex seed text
  (point-in-time snapshot, re-rendered on demand — regenerating is the update path) and
  `scripts/ship_plugin.sh` co-author line (attribution, not routing policy). The single-mapping-
  point claim (§2.2) is scoped to **routing-policy docs**, not the whole repo.
- **No TIER_FACTOR calibration**; budget_hint stays declared non-predictive.
- **No renaming of role labels** (utility/fleet/escalation/conductor stay prose labels).

## §2 Canonical decisions (fixed so parallel workers cannot diverge)

1. **Tier vocabulary (canonical ids):** `cli | haiku | sonnet | opus | fable`.
   Role labels: haiku = *utility* (an opt-in rung **below** fleet, not a fourth peer tier),
   sonnet = *fleet* (default), opus = *escalation/synth*, fable = *conductor*.
   Codex mapping unchanged (gpt-5.4 ↔ sonnet-tier, gpt-5.5 ↔ opus/fable-tier).
2. **Single model-mapping point (scoped):** within the routing-policy docs (project-meta
   `references/*`, orchestration skill docs), the tier table in
   `multi-agent-protocols.md#model-tier` is the ONE place tier-id → concrete model version
   is written. Other routing docs use tier ids and cite the section. (Non-routing surfaces
   are explicitly non-goaled in §1.)
3. **Ledger `--tier` format:** `<tier-id>[/<effort>]`, effort ∈ `low|medium|high|xhigh|max`.
   `record` lowercases/trims; stderr WARN (never failure, still recorded) when the model token
   is outside {cli,haiku,sonnet,opus,fable,gpt-5.4,gpt-5.5} **or** the effort token is outside
   the enum. Aggregation must tolerate legacy rows: mixed case, missing effort (report effort
   `-`), free-text tiers (bucket as-is after lowercase).
4. **Hook `dispatch-tier-guard.sh` — advisory tier-visibility guard.**
   PreToolUse matcher `Task|Agent` (`Agent` is the current tool name; `Task` is the historical
   alias — a dead regex alternative is harmless and covers older runtimes). Branches evaluated
   in order, first match wins; ALL branches exit 0 (advisory); `minimal` profile exits silently;
   fail open on unparseable payloads, and treat non-string `subagent_type`/`model` values as
   "custom/unknown" (notice path), never crash:
   1. `model` present and ∈ {haiku, sonnet} (substring match on model string) → silent.
   2. `model` present and opus-class → one-line notice: "escalation-tier dispatch (sanctioned
      ≤2/run — see model-tier canon); this notice also fires on legitimate escalations".
   3. `model` present and fable/conductor-class → one-line notice: "conductor-tier dispatch —
      canon allows at most one unblock call per run".
   4. `model` absent + `subagent_type` ∈ {general-purpose, claude, unset} → WARN: "dispatch
      inherits the session model — fleet default is sonnet; pass model:'sonnet' or confirm the
      agent definition pins a model (invisible to this hook)".
   5. `model` absent + any other `subagent_type` (incl. Explore/Plan/custom/plugin) → short
      notice only (the type likely pins its own model in frontmatter).
   The hook is **stateless** — it never queries the ledger (coupling/perf; the ≤2/run count is
   contract-reviewed, not hook-counted).
5. **Promotion records: storage unchanged; evidence leg mechanized.** Canon keeps repo memory
   as the durable promotion-record store (current text). WP3 adds only: (a) a sentence naming
   `dispatch_ledger.py query --tiers` as the mechanical evidence read leg retro-inspect step 1
   already promises, and (b) haiku's relation to the ladder (see #8). A structured
   lesson-registry fit (task_type field + lookup verb) is filed as a board item, not built.
6. **budget_hint tier-mix:** fleet share = **(haiku + sonnet) expected tokens / total** (cli is
   excluded from the concept — it is "no model", contributes 0 anyway). Text render appends the
   footer in the ALREADY-SHIPPED format `tier-mix: NN% fleet / n×opus / n×fable / n×cli` plus a
   `WARN: fleet token-share below 80% target (advisory — mistagged tiers are not detectable
   here; review the per-task model_tier column)` line iff share < 80% and any modeled task
   exists. `--json` adds `fleet_share` + per-tier token totals. `TIER_FACTOR["haiku"]=0.6`,
   `TIER_PRICE["haiku"]=5.0`. Existing invocations: identical output except appended lines/keys.
7. **Effort per-backing note (canon):** Workflow `agent(opts.effort)` = native; Agent tool = no
   effort param → encode depth in the brief wording; Codex = reasoning-effort config. One short
   list under "Tier is two axes".
8. **Canon coherence edits (owned by WP3, mandatory):**
   - "Three tiers govern a pipeline run" → keep the three governing tiers, introduce haiku as
     an opt-in **utility rung below fleet** (e.g. "Three tiers govern a pipeline run; an
     optional utility rung (haiku) sits below fleet for high-fanout bounded judgment").
   - Haiku usage rule: extract/classify/label/summarize-class bounded judgment at high fanout;
     never code edits, reviews, or security surfaces; **outside the promotion/demotion ladder**
     — chosen up-front by task classification; a haiku failure promotes to sonnet (one-way entry
     into the normal ladder); retro-inspect never demotes a sonnet task-type to haiku (re-classing
     to haiku is a Lead classification decision, not a ladder move).
   - The ≥80% target sentence is restated in the SAME paragraph as: fleet share counts sonnet
     **plus haiku** utility tokens (matching §2.6), so canon and budget_hint cannot fork.
   - Mention the WP1 guard (advisory backing of the fleet default) and the WP2 read leg
     (mechanical backing of retro-inspect step 1) where those rules are stated.
9. **`query --tiers` output contract (pinned):** plain text, one block per task_type present:

   ```
   [tiers] reviewer:methodology — 3 record(s)
     sonnet/medium   PASS=1 BLOCKER=1
     opus/max        PASS=1
     latest: 2026-07-01T…  opus/max  PASS
   ```

   Rows without task_type are aggregated under `(untyped)`. `--task-type X` filters the same
   view to one key. No JSON mode in v1.

## §3 Work packages (parallel Sonnet workers, shared tree, disjoint files)

| WP | Files | Content |
|---|---|---|
| **WP1 hook** | `skills/project-meta/templates/hooks/scripts/dispatch-tier-guard.sh` (new), `skills/project-meta/templates/hooks/README.md` (new section + hook table), repo `.claude/hooks/dispatch-tier-guard.sh` (instantiated copy), repo `.claude/settings.json` (PreToolUse entry `Task\|Agent`), `AGENTS.md` hooks-pack line | Decision #4. Style-match `pre-tool-guard.sh` (profile-aware, python3 payload parse, fail-open, stderr-only). README section states: advisory-only rationale (A1/A2), Workflow non-coverage (A7), deny = possible v2 behind evidence. |
| **WP2 ledger** | `skills/project-meta/scripts/dispatch_ledger.py` | Decision #3 (record normalization + WARNs) + read leg per decision #9 (`query --task-type`, `query --tiers`). Non-breaking; legacy-row tolerant. |
| **WP3 canon** | `skills/project-meta/references/multi-agent-protocols.md` (Model Tier section), `skills/project-meta/references/dispatch-card.md` (pointer refresh if needed) | Decisions #1, #2, #5, #7, #8. Also: verify `recipes/roadmap.md` / `recipes/refine.md` model-name hits are citations not routing policy (read-only check; report, don't edit unless they encode routing). |
| **WP4 orchestration** | `skills/orchestration/scripts/budget_hint.py`, `skills/orchestration/templates/orchestration-contract.md`, `skills/orchestration/references/orchestration-contract.md`, `skills/orchestration/recipes/orchestrate.md`, `skills/orchestration/examples/sample-orchestration-contract.md`, `skills/orchestration/SKILL.md` (model-tier quick-reference line) | Decision #6; docs updated to `cli|haiku|sonnet|opus|fable`; footer format preserved; contract docs say "paste budget_hint's computed tier-mix" instead of hand-computing. |
| **WP5 lead (serial, after merge)** | `.claude-plugin/marketplace.json`, `docs/backlog/` via `board.py`, ship flow | Bumps: project-meta **minor**, orchestration **minor**. Board items: 4 shipped capabilities + 2 backlog (strict-deny v2 evidence gate; lesson-registry task_type fit). Validators → fresh L2 review (correctness + adversarial lenses) → PR → land. |

## §4 Verification matrix

| Item | Test target | Data | Threshold |
|---|---|---|---|
| WP1 | `dispatch-tier-guard.sh` with synthetic PreToolUse JSON on stdin | 9 cases: model=sonnet (silent), model=haiku (silent), model=opus (notice), model=fable (notice), missing-model generic type (WARN), missing-model Explore (notice), missing-model custom plugin type (notice), `subagent_type` as dict/non-string (notice or silent, exit 0, no crash), garbage payload (exit 0 silent); plus HARNESS_PROFILE=minimal → exit 0 silent for all | every case exits 0; correct stderr class per case; stdout untouched |
| WP2 | `dispatch_ledger.py record/query` in a scratch repo | records: `sonnet/medium`, `SONNET/high` (normalizes), `opus/max`, `sonnet` (no effort → `-`), `sonnet/ultra` (bad effort → WARN, recorded), `gpt6/max` (bad tier → WARN, recorded); legacy hand-written row `Sonnet/Medium` in the JSONL; two task_types + one untyped row | `query --tiers` matches §2.9 shape; `--task-type` filters; no crash on legacy rows; `validate` still exit 0 |
| WP3 | `python3 scripts/validate_project_meta.py` + greps | canon | validator exit 0; "utility rung" + ladder-exclusion + restated 80% sentence present; concrete model versions inside `references/` appear only in multi-agent-protocols.md's mapping table (existing review-tier.md name-drops converted to tier ids or explicitly cited) |
| WP4 | run `budget_hint.py` | `--task haiku:lint:8 --task sonnet:edit:2 --task opus:plan:1` (share <80% → WARN present), `--task sonnet:edit:4 --task cli:lint:2` (≥80% → no WARN), `--json` both | haiku accepted; footer format matches shipped `% fleet / n×opus / n×fable / n×cli`; `fleet_share` in JSON; pre-existing invocations unchanged except appended lines |
| WP5 | `scripts/ship_plugin.sh validate`; fresh L2 review of full diff | full diff | validate exit 0; review clean of blockers |

## §5 Orchestration contract (compact)

| Task | model_tier | parallelization | review_level | budget_hint |
|---|---|---|---|---|
| critic panel (done) | sonnet | 2 parallel | — | sonnet:review:2 |
| WP1–WP4 build | sonnet | 4 parallel (disjoint files) | L1 inline self-check | sonnet:edit:4 |
| WP5 lead + ship | fable (session) | serial | L2 fresh panel ×2 | sonnet:review:2 |

Budget hint: expected ≈ 56,000 output tokens (low ≈ 16,800 · high ≈ 168,000) — estimate, not a
guarantee. tier-mix: 100% fleet dispatched / 0×opus / 0×fable (conductor = session, not fan-out).

## §6 Critic-panel disposition (rev 1 → rev 2)

- A#1/A#3 (strict deny false-positives; Explore/Plan) → **accepted**: advisory-only v1 (§1, §2.4).
- A#2 (Task name; Workflow gap) → **accepted**: A7 added; Workflow non-coverage is a named
  non-goal; `Task` kept as documented harmless alias.
- A#4 (WARN fatigue) → **accepted, adapted**: opus/fable are low-key notices with
  "fires on legitimate escalations" wording; hook stays stateless (no ledger query per call).
- A#5 / B#8 (legacy/effort tier strings) → **accepted**: §2.3 + WP2 test rows.
- A#6 / B#2 (tier-mix format + 80% fork) → **accepted**: shipped footer format kept; fleet share
  = haiku+sonnet; canon restates the target in the same paragraph (§2.6, §2.8).
- A#7 (gameable WARN) → **accepted**: advisory sentence in the WARN text.
- A#8/A#9 (payload shape, branch order) → **accepted**: §2.4 preamble + test case.
- B#1/B#9 (lesson-registry misfit) → **accepted**: descoped; A5 flipped; backlog item (§2.5).
- B#3 (haiku vs ladder) → **accepted**: ladder exclusion made explicit (§2.8).
- B#4 (drift surfaces beyond scope) → **accepted, bounded**: single-mapping-point claim scoped
  to routing-policy docs; generator/ship-script non-goaled with reasons (§1).
- B#5 (orchestration SKILL.md) → **accepted**: added to WP4.
- B#6 (query output unpinned) → **accepted**: §2.9 pins the shape.
- B#7 (justify new script) → **accepted**: §1 sentence added.
