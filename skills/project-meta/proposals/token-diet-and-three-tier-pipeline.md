# Proposal: project-meta token diet + three-tier (Fable/Opus/Sonnet) pipeline contract

> **Status:** Partially shipped (2026-06-10) — **D2** (router repair), **D6** (trigger coverage)
> and **PR-D** (three-tier model canon + orchestration schema) landed in project-meta 1.10.0 /
> orchestration 0.2.0 (PR #36); the harness-feedback machinery (Stop gate #5 et al.) landed via
> the board PR line. Remaining: **D1 description trim (DASH-031)**, **D3–D5**. Branch
> coordinates referenced below (`harness-feedback`, `claude/clever-jang-25c094`) are
> historical — all branches have merged and been deleted.
> (Design **rev 2** — revised after a 4-lens adversarial critic panel:
> cost-model, enforcement-feasibility, regression, scope/conflict. Panel adjudication in §7.)
> Extends board item DASH-031 (token diet) with the audit evidence behind it, and adds the
> model-tier v2 contract for the 2026 three-tier lineup (Fable 5 > Opus 4.8 > Sonnet 4.6;
> Haiku out of scope for now).
> **Grounding:** full-branch + full-skill audit of this repo (2026-06-09, four dispatched
> Sonnet auditors), verified against Anthropic skill best-practices docs, the multi-agent
> research-system post, and cascade-routing literature. Aligns with memories
> `prefer-sonnet-subagents`, `cli-toolkit-doctrine`, `prefer-lightweight-derived-design`,
> `critic-before-build-canon` (this doc is the PLAN; the panel has now run once).

## 0. Audit verdict (what motivates this proposal)

Measured worst-case context loads per verb (recipe-mandated reads, incl. SKILL.md ≈ 25 KB):

| verb | mandated load | ≈ tokens |
|---|---|---|
| `init` | 85 KB base / 107 KB with multi-agent-protocols.md | 21k–27k |
| `audit` | 93 KB | 23k |
| `deliver` | 74 KB | 19k |
| `validate` | 64 KB | 16k |
| `status` | 37 KB | 9k |

Cannon-to-mosquito core finding: **`references/multi-agent-protocols.md` (27 KB / ~6.7k tok)
is co-loaded on every `init` and most `deliver` runs even when dispatch never fires.** The
mandatory-dispatch trigger (≥2 harness files) has a trivial-change carve-out that relies on
self-classification under pressure; the complexity trigger (2-of-6 signals) matches nearly
every non-trivial invocation, so it over-dispatches small tasks into Worker+Reviewer pairs.

Caching nuance (panel F-cost-4): the per-invocation *dollar* saving from trimming loads is
concentrated at cold-start (prompt-cache reads are ~0.1× within the 5-min TTL); the
*context-window* saving is unconditional and is the primary justification for D3/D4.

Second always-on tax: the 897-char description (~225 tok) exceeds the 200-tok ceiling its own
`context_cost_estimate.py` enforces — captured as DASH-031. Per-session saving is ~170 tok at
single install, ~10× that under the current duplicate-marketplace-install state (which
collapses back to ~170 once global-meta dedups installs — environmental fix, §5).

Routing-table defect (narrowed per panel F-scope-4): `roadmap` and `refine` are **absent from
SKILL.md's Recipes table** (`roadmap` is routable only via `cli-command-patterns.md:28`;
`refine` is a documented sub-workflow of `roadmap`). A model following SKILL.md's table alone
misroutes them. `validate_project_meta.py` checks `cli-command-patterns.md` only, so the
SKILL.md table can drift silently.

## 1. Token diet (D1–D6)

- **D1 — description diet to ≤150 tok (not 55).** Panel BLOCKER (F-reg-1): the validator's 16
  required description phrases cannot fit in 55 tokens, and the description is the **only
  auto-trigger surface** (the Trigger Decision section loads only *after* triggering — moving
  phrases there cannot rescue recall). Revised scope, one atomic commit: rewrite description
  to ~100–150 tok keeping the highest-recall trigger phrases; update
  `validate_project_meta.py` phrase list to the kept set; sync `marketplace.json` description
  (verbatim check) **and** `agents/openai.yaml` `default_prompt` in the same commit.
- **D2 — router repair (narrowed):** add `roadmap` + `refine` rows to the SKILL.md Recipes
  table; add a ~15-line `check_skillmd_recipe_table_sync` to `validate_project_meta.py`
  diffing the SKILL.md table against the `cli-command-patterns.md` route table, with an
  allowlist for documented sub-workflows (`refine`, `mirror-linear`). Collapse the three
  partially-overlapping delivery-contract restatements to one canon + pointers.
- **D3 — dispatch trigger card (boundary redesigned, panel F-feas-4):** extract a ~2 KB
  `references/dispatch-card.md` containing **only** the trigger conditions and the bypass
  rule, with links into the full protocol. `multi-agent-protocols.md` **keeps its filename
  and every existing anchor** (`#model-tier` is cited by 4 downstream files;
  `#mandatory-subagent-dispatch` by `dispatch_ledger.py` and hooks README — zero breakage).
  Editing recipes mandate the card; the full protocol loads only when the trigger actually
  fires. Saves ~6.7k context tokens on the common init/deliver path.
- **D4 — stage recipe reads + measurable acceptance:** convert recipes' eager
  required-references lists to staged loads keyed to the step that needs them. Panel
  F-scope-3: `context_cost_estimate.py` cannot measure per-verb load, so D4 ships a new
  ~60-line `scripts/verb_load_estimate.py` that parses each recipe's required-reference list
  and sums file sizes; acceptance runs on it. Target: `init` base ≤40 KB.
- **D5 — deterministic gates, mechanism redesigned (panel BLOCKERs F-feas-1, F-feas-3/F-reg-7):**
  - *No transcript grepping.* Stop hooks in this pack are file-derived; "grep the turn tail"
    is not implementable reliably. Instead, editing recipes end by writing
    `.harness/last-turn-meta.json` (`verb`, `review_tier`, `read_pattern`, footer fields);
    the Stop gate checks that file's presence + required keys. Prose footer stays for humans;
    the JSON file is the machine contract.
  - *Provenance:* PostToolUse hook runs `provenance.py` in **advisory auto-stamp** mode for
    newly created `agents/*.md` (exit 0 + warning; no deadlock on first-draft files, panel
    F-feas-2) and hard-`check` mode only for pre-existing files; the hard gate for new files
    moves to `deliver`/`validate`.
  - *Ledger:* the non-empty `.harness/dispatch-log.jsonl` requirement fires **only when
    `(≥2 harness files changed) AND no `.harness/dispatch-ack` exists`** — the documented
    single-context bypass keeps producing zero ledger entries (panel F-reg-7). Promotion
    records land via `dispatch_ledger.py record --tier --verdict`; a new lightweight
    `bypass-record` subcommand (no `--worker` required) is optional, not gating.
  - *Prerequisite:* the `harness-feedback` branch **must land first** (it owns gate #5 and
    the friction machinery D5 builds on); coordinate gate numbering with
    `claude/clever-jang-25c094` (also adds a gate #5). D5 gates append after both.
- **D6 — trigger evals, honestly named (panel F-feas-7):** per-skill `evals/triggers.json`
  (~10 should-trigger / 10 should-not). CI runs a deterministic **token-coverage gate**
  (stdlib keyword overlap — *not* called precision/recall) with a coverage floor that fails
  the build (panel F-reg-2: a measurement without a floor only observes the regression).
  True model-based precision/recall runs as a separate scheduled job with an API key,
  outside the CI lint path.

Acceptance (per-PR, see §6): `context_cost_estimate.py` clean (no DESC>200 at the new ≤150
budget — lower the script ceiling only if the rewrite lands under it); router ≤250 lines with
all verbs routable; `verb_load_estimate.py` reports init ≤40 KB; validator suite green
including the new table-sync check; lint 0 FAIL.

## 2. Model-tier v2 — the three-tier contract (canon edit)

Single authoritative edit point: `multi-agent-protocols.md#model-tier` (the file keeps its
name and anchors; downstream skills cite this section rather than restating it).

| tier | model (Claude Code 2026-06) | role in a pipeline | output $/MTok |
|---|---|---|---|
| **fleet** (default) | Sonnet 4.6 | every dispatched bounded role: Workers, Reviewers, Explorers, scouts, finders, verifiers, extract/summarize/lint-adjacent judgment | $15 |
| **escalation/synth** | Opus 4.8 | (a) the single escalate-on-demonstrated-shortfall agent; (b) cross-agent synthesis where one context reconciles many fleet outputs; (c) adversarial/security review where a miss is expensive | $25 |
| **conductor** | the **active session model** (Fable 5 when available) | Lead/session only: framing, contract signing, architecture forks, final canon gate; plus at most **one** dispatched "unblock" call when an Opus escalation already failed | $50 (Fable) |

Conductor note (panel F-reg-10): "conductor = Fable" is a *target*, not a guarantee — on a
Sonnet session the conductor is Sonnet and the contract must say so. The tier-mix report
counts **dispatched** agents only; dispatched Fable is normally zero and any non-zero count
must be justified per-slot (there are no standing "Fable slots" to pad).

Rules (delta vs today's canon):

1. **Default stays Sonnet for all spawned roles** — unchanged, now named the *fleet* tier.
2. **Escalation ladder unchanged by default: a demonstrated fleet shortfall escalates that
   one agent to Opus.** The fleet *panel* (N diverse-lens Sonnet reviewers, majority verdict)
   is **opt-in, expressed as review-tier L2** — it is the *same mechanism* as
   `review-tier.md` L2 (3–4× Sonnet + opt Opus synth), not a new rung (panel F-scope-2,
   F-reg-6/8). Choose it at contract time for high-volume bounded judgments where a single
   reviewer's failure signal is ambiguous; never chain "L2 panel then Opus-escalate the
   panel" — cap the combined path at one escalation. Cost claim, stated honestly: a panel is
   cheaper than an Opus retry **only when** panel output tokens ≪ retry output tokens
   (typical for bounded verdicts); same-model panels do not decorrelate systematic failure
   modes — diversity comes from the lens prompts, and a capability-ceiling failure (e.g. a
   missed subtle security bug) should skip the panel and escalate directly.
3. **Opus is never a fan-out tier.** At most twice per pipeline run: one escalation slot +
   one synthesis slot.
4. **Fable is never dispatched in fan-out** — it is the session (see conductor note).
5. **Promotion records stay**, recorded via `dispatch_ledger.py record --tier --verdict`,
   enforced by D5's ledger gate (with the bypass exemption).
6. Two-axis rule (model × effort) unchanged.

Tier-mix target (re-based per panel F-cost-3): **≥80 % of *estimated output tokens* (from
`budget_hint.py` totals at signing) on the fleet tier** — token-share, not agent-count, so
the ratio cannot be padded with trivial agents. Each Opus slot is justified individually in
the contract's review section.

## 3. Pipeline contract changes (orchestration skill)

- `model_tier` enum: `cli | sonnet | opus | fable` — updated **atomically in one PR** across
  the schema (`references/orchestration-contract.md`), the template, the recipe (including
  the conductor line `recipes/orchestrate.md:16` → "main session model (Fable-class when
  available)"), the SKILL.md floor, `budget_hint.py` (which hard-errors on unknown tiers),
  and one `fable` example row in the sample contract.
- `budget_hint.py` — **dimension fix (panel BLOCKER F-cost-1):** `TIER_FACTOR` is a *token*
  multiplier ("stronger models think/emit more"), not a price ratio. Keep
  `{"cli": 0.0, "sonnet": 1.0, "opus": 2.5}` semantics, add `"fable": 3.0` (heuristic:
  adaptive thinking always on ⇒ ≥ Opus emission; uncalibrated, like the others — say so in
  a comment). Add a separate `TIER_PRICE = {"sonnet": 15, "opus": 25, "fable": 50}`
  ($/MTok output) and a `--dollars` mode so contracts can show both a token band and a cost
  band. Changelog note: factors were never pricing-derived.
- New contract footer line: `tier-mix: <tok-share>% fleet / <n>×opus / <n>×fable / <n>×cli`
  computed from the budget-hint totals, so the ≥80 % token-share target is checkable at
  signing and in the post-run report.
- **Dropped from rev 1:** the per-task `verify` field. It re-enumerated review-tier L0–L3
  under new names with no runtime consumer (panel F-scope-2 + F-feas-6 — schema without an
  executor). The existing `review_level` field already expresses panel topology; rule 2
  above binds the panel rung to L2.
- Arbitration repair **extracted to a standalone micro-PR / backlog item** (panel
  F-scope-5): add an `orchestration` row to project-meta's Skill Arbitration table + a
  reciprocal Skill Arbitration section in orchestration's SKILL.md.

## 4. Subagent context contract (token side of the pipeline)

Codify in the full protocol (not the dispatch card), per the research-system pattern:

- Context package is **by value and minimal**: objective, output format, tool/source
  guidance, task boundary. Never session history.
- Heavy outputs go to the filesystem; the agent returns a ≤2k-token condensed summary +
  artifact path. The Lead reads artifacts on demand only.
- Workers receive the **floor rules they're expected to obey** (provenance, footer/meta
  file) inside the package — dispatched workers otherwise never see them.

## 5. Out of scope / explicitly not proposed

- No Haiku tier yet (owner's call); the enum leaves room.
- No learned router — heuristic table + escalate-on-evidence (`prefer-lightweight-derived-design`).
- No new orchestration machinery (AP-COORD-7); rev 2 additionally *removed* one piece of
  machinery rev 1 had invented (`verify` field).
- Duplicate-marketplace-install dedup: global-meta audit territory; biggest real-world
  always-on saving, tracked separately.

## 6. Sequencing (re-sliced per panel F-scope-6; version bumps per F-scope-7)

| PR | content | prereq | bump |
|---|---|---|---|
| **A** | land `harness-feedback` branch (friction machinery + gate #5 + DASH-031) | — | per branch |
| **B** | D2 router repair + D6 coverage gate + `evals/triggers.json` | — | project-meta patch |
| **C** | D5 gates (last-turn-meta file gate, provenance advisory hook, ledger gate w/ bypass exemption) appended after A's and clever-jang's gates | **A** (+ coordinate clever-jang) | project-meta minor |
| **D** | tier v2 canon + orchestration enum/schema/template/recipe + budget_hint fable + TIER_PRICE | — | orchestration minor + project-meta patch |
| **E** | D3 dispatch card + D4 staged reads + `verb_load_estimate.py` (L3 review — MUST-rule surface) | B | project-meta minor |
| **F** | D1 description diet (SKILL.md + marketplace.json + openai.yaml + validator phrase list, atomic) | B (coverage gate exists first) | project-meta minor |
| **micro** | arbitration cross-link (pm table row + orchestration section) | — | both patch |

DASH-031's acceptance shape is amended (not silently extended) when A lands: D1/D2 stay in
its scope; D3–D6 get their own board items pointing at this proposal as `source`.

## 7. Panel adjudication record (rev 1 → rev 2)

Accepted BLOCKERs: TIER_FACTOR dimension error (cost-1) → kept token semantics + separate
price table; Stop-hook transcript grep infeasible (feas-1) → file-write gate; ledger gate vs
bypass deadlock (feas-3/reg-7) → ack exemption; `verify` field = duplicated review-tier with
no consumer (scope-2/feas-6) → dropped; 55-tok description vs 16 validator phrases +
verbatim marketplace/openai.yaml sync (reg-1/5) → ≤150 tok atomic commit; D5 collision with
`harness-feedback`/`clever-jang` gate #5 (scope-1) → prerequisite ordering in §6.

Accepted MAJORs: panel rung opt-in via L2, not a mandatory ladder step (reg-6/8); tier-mix
target token-share not agent-count (cost-3); D3 boundary preserves all anchors (feas-4); D6
renamed token-coverage gate + floor (feas-7/reg-2); D4 acceptance needs `verb_load_estimate.py`
(scope-3, AP-PLAN-1); D2 claim narrowed — verbs routable via cli-command-patterns.md, defect
is SKILL.md-table drift (scope-4); conductor-tier honesty note (reg-10); caching/D1-savings
framing (cost-4/5); per-PR version bumps + DASH-031 amendment record (scope-7/8).

Rejected: reg-3's "fourth missed update site" — rev 1 §3 already listed the
`recipes/orchestrate.md` conductor-line change; the atomic-update requirement it argued for
is accepted, the "missed" claim is not.
