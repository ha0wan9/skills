---
artifact_name: project-board-system-backlog
kind: feature-backlog
project_scope: project-meta Project Board capability + SPLIT-OUT orchestration & review-tier skills
owner: user-reviewed
status: canonical source of truth; rescoped + split (after adversarial critic review, 2026-06-06)
source_reference: design conversation 2026-06-06; independent adversarial critic (verdict RESCOPE→SPLIT)
review_policy: groom + version-assign during /project-meta roadmap (DASH-08); seed instance (dogfooding) — this file is a prose proposal, NOT the JSON store DASH-01 specifies
last_reviewed: 2026-06-06
---

# Feature Backlog — Project Board System

A persistent, CLI-managed, repo-canonical project surface — **Backlog/Issues → Roadmap (versioned) → Plan → Orchestration contract → /workflows**, rendered to a static interactive `dashboard.html` (the *iterated form of user-facing documentation*), with optional Linear mirror.

> **Canonical source of truth.** This file is the only active design source for the Project Board System. Older flow/source proposals have been trimmed; downstream route docs and implementation plans should derive from this backlog, not from retired proposals.
>
> **Reviewed 2026-06-06 (independent adversarial critic) → RESCOPE + SPLIT applied.** See *Review status* below. Headlines: orchestration is **split into its own skill**; review-tier ships as **shared infra inside `project-meta`** (operator decision 2026-06-06, superseding the earlier "review-tier skill" split — see *Skill split*); DASH-22 forecast **downgraded to a non-predictive budget hint**; the async model fixed to **dry-run-first capture + append-only inbox + deferred dedup**; this seed file is a **prose proposal**, not the JSON store it specs.

## Skill split (locked)

| Stream | Home | Entries |
|---|---|---|
| **Project Board** | `project-meta` capability | A Backlog/Issues · B Roadmap · D Dashboard · E cross-cutting |
| **Orchestration** | new **`orchestration` skill** | C — DASH-09/10/11/22 (the `/workflows` contract layer) |
| **Review-tier** | **shared infra in `project-meta`** (`references/review-tier.md` + `scripts/review_tier.py`) | F — DASH-19/20/21 (consumed by project-meta's roadmap review *and* — later — the orchestration skill via the root-skill pointer) |

> **Design change (2026-06-06, operator-confirmed, shipped v0.2 wave 1):** review-tier was originally split into its own `review-tier` skill. It now ships as **shared infra inside `project-meta`** instead — no second top-level skill, no marketplace-install friction, consistent with the derived-design preference. The orchestration skill (still split out) consumes it via the root-skill pointer pattern. Prose below that still says "review-tier skill" predates this change; read it as "review-tier shared infra."

## Architecture

Four cross-cutting planes × a conductor-driven value spine × one engine boundary × a closed feedback loop. After the split, the spine **crosses skill boundaries** (project-meta → orchestration skill → engine); review-tier is a shared plane.

```
          ┌─────────────────────────  CROSS-CUTTING PLANES  ─────────────────────────┐
          │  govern every stage; all policy, left of the engine boundary               │
          │   · Review-tier   L0..L3   (→ project-meta shared infra, DASH-19–21)       │
          │   · Exec-tier     CLI=no-model · Sonnet=worker · Opus=hard   (DASH-15)      │
          │   · Budget-hint   coarse, non-predictive estimate           (DASH-22)       │
          │   · Source-of-truth  store=canonical → dashboard=derived → Linear=mirror    │
          └───────────────────────────────────────────────────────────────────────────┘

  VALUE SPINE   (conductor = main session: drives the spine + delegates side-work per Exec-tier)

   any session
      └─ autonomous capture (headless-Sonnet hook · DASH-02 · dry-run first; opt-in append) ─┐
                                                                             ▼
   ┌──────────────────────────────────────────────────────────┐
   │ ① BACKLOG / ISSUES   append-only inbox · docs/backlog       │◄──── trim / defer ──┐
   │   maturity: fuzzy ──refine(DASH-23)──► refined              │                     │
   └──────────────────────────────────────────────────────────┘                     │  [project-meta]
                       │ joint co-review TX (DASH-08 · L2; dedup here, not at capture) │
                       ▼                                          ▲ refinement-guidance feedback
   ② /project-meta roadmap   versioned milestones · collaborative · review L2 ─────────┘
                       │ pick a milestone (v0.2)
                       ▼
      /project-meta plan   falsifiable build-plan = task × acceptance   (shipped)
   ────────────────────┼──── skill boundary ───────────────────────────────────────────
                       ▼                                                      [orchestration SKILL]
   ③ orchestrate   contract: tier·parallel·effort·human·review-level·budget-hint — signed ahead
                       │ sign → emit (recommend; engine is user-gated, NOT skill-enabled)
   ════════════════════╪════════  engine boundary (AP-COORD-7: contract=policy · engine=mechanism)  ════════
                       ▼
      /workflows (+/loop)  execute ──► run outcomes ──► status ──► (back to ① )

   ┌─ Dashboard  docs/dashboard.html · CLI render=derived · browser edit experimental ─┐  [project-meta]
   │   renders ①②③ + run status   =   user-facing documentation, iterated             │
   └────────────────────────────────────────────────────────────────────────────────────┘
```

## Review status — what the adversarial critic changed

- **DASH-22 (Blocker):** named reuse couldn't back a forecast — `context_cost_estimate.py` is a skill-doc *size* linter (chars/4), `dispatch_ledger.py` has **no** token/cost/runtime fields. → **downgraded to a non-predictive budget *hint***; dropped the "feed `/workflows budget`" AP-COORD-7 overreach and the calibration claim.
- **Async (Major):** "single writer per transition" was false — capture is multi-instance. → **dry-run-first capture, optional atomic append to an inbox, and dedup deferred to the single-writer refine/co-review gate** (DASH-02/24).
- **Store format (Major):** this file is prose MD, not the JSON store DASH-01 specs; DASH-18's source contradicts the comment-ban. → carved out as a one-time prose proposal; DASH-18 must drop the "header comment" wording.
- **DASH-20 (Major):** "deterministic" overstated → **heuristic scorer + mandatory escalation gate**.
- **Merges:** DASH-07 → DASH-08; DASH-14 → DASH-04 (honest count 23).
- **Verbs:** `roadmap`/`orchestrate` reconciled against the Reserved-Commands policy (DASH-17).
- **Gaps:** captured in *Open questions* below.

**Legend** — `kind`: feat · infra · docs · chore. `tier`: CLI=no model · Sonnet=worker · Opus/main=primary. `target`: tentative, set in grooming.

---

## A. Backlog & Issue system  · `project-meta`

### DASH-01 — Repo-canonical backlog/issue/bug store
`infra · target: v0.1 · CLI`
Items live in `docs/backlog/` (repo = source of truth; HTML derived; Linear mirror). **v0.1 store layout is fixed and parseable:**
- `docs/backlog/items.jsonl` — canonical current item records, one JSON object per line; CLI mutations rewrite this file via temp+rename.
- `docs/backlog/inbox.jsonl` — append-only capture inbox for async fuzzy ideas/bugs; no mutation or dedup here.
- `docs/backlog/roadmap.json` — bounded version milestone state (`{"_meta":{"rev":N,...},"milestones":[...]}`).
- `docs/backlog/.provenance.json` — provenance sidecar; **never `#` comments** in parseable stores.
- `docs/backlog/.refine-guidance.md` — small human-readable guidance distilled by co-review; advisory, not a canonical item store.

Item records separate requirement quality from execution state: `maturity: fuzzy|refined`; `status: unscheduled|scheduled|in_progress|done`; `disposition: active|deferred|trimmed|wontfix`; `version: null|"vX"`; plus `id`, `kind`, `title`, `body`, `acceptance_shape`, `rough_size`, `labels`, `links`, optional `linear_id`, `created_at`, `updated_at`, and `source`. Capture lands in `inbox.jsonl` as `maturity:fuzzy`, `status:unscheduled`, `disposition:active`, `version:null`; only `maturity:refined` + `disposition:active` items are roadmap-eligible (ladder in DASH-23). **Note:** *this seed file is a prose proposal, not the runtime store* — the format above governs the store the system manages; the stale dashboard proposal that carried the conflicting "provenance header comment" wording has been trimmed.

### DASH-02 — Autonomous out-of-scope capture via headless Sonnet agent
`feat · target: v0.2 · Sonnet`
When the agent surfaces a feature/bug **out of the current session's scope**, capture it. Mechanism: a `Stop`/`SessionEnd` **command hook** → cheap shell pre-filter (feature/bug-shape only) → **headless Sonnet agent** (`claude -p --model sonnet`, has scoped tools) → candidate capture. **First shipped mode is audit-only/dry-run:** write a dry-run log and require an interactive session to promote candidates into `inbox.jsonl`. Automatic append is a later opt-in profile after observed false-positive rate, approval surface, and scoped-tool policy are acceptable.

When automatic append is enabled, it writes **only** to `docs/backlog/inbox.jsonl` with atomic single-line append (`O_APPEND` or temp+rename). **No dedup at capture** — capture is append-only and multi-instance-safe; dedup/merge is deferred to the single-writer refine/co-review gate (DASH-24), avoiding the multi-session TOCTOU race. Profile-gated (`minimal` off; `standard` dry-run; `strict` may block on policy); `SessionEnd`-tendency to avoid over-fire (AP-VAL-1). Captured items are `fuzzy` — never auto-promoted (refine first, DASH-23).
> Caveat: native `agent`-type hooks are tool-events-only → use *command hook → headless Sonnet*, not an agent-type hook on Stop. Linear mirror never runs from this subprocess.

### DASH-03 — Optional Linear mirror (push-only)
`feat · target: v0.3 · Sonnet`
Reuse the `issue-tracker` Track Loop: repo canonical → Linear; check / write-back / open; body **links back**; mirror `linear_id`. **Push-only** — document reverse-drift (Linear edited directly is not pulled back). The Track Loop is **agent-MCP-only**, so the mirror runs in an *interactive* session, not the headless capture subprocess (see *Open questions*).

### DASH-04 — Backlog CLI (CRUD + render)  *(absorbs DASH-14)*
`infra · target: v0.1 · CLI`
`scripts/board.py` (std-lib, deterministic): `add / refine / move <id> <status> / defer|trim|wontfix / edit / list / render / tx`. `render` = pure CLI injecting the store into the dashboard template's data arrays; **auto-runs after every mutation**; the HTML is always derived, never hand-edited. v0.1 write surface is CLI-only for canonical stores; DASH-02 writes only dry-run logs or the append-only inbox, never `items.jsonl`/`roadmap.json`.

### DASH-23 — Requirement refinement (fuzzy → concrete)
`feat · target: v0.2 · Sonnet`
The ladder's first promotion gate — vague capture → roadmap-eligible requirement:

```
capture(fuzzy) ──refine──► refined ──co-review(DASH-08)──► scheduled@vX ──► in_progress ──► done
     │ raw idea / vague bug   │ scope + acceptance-shape + rough size              ▲
     └──── drop ◄─────────────┴──── defer / trim (stale · off-direction) ◄─────────┘
```

A **Sonnet sub-agent drafts** the concrete requirement (scope · acceptance-shape · rough size), **asks the operator** where ambiguous; `fuzzy→refined` **promotion is confirmed** (async-draft / deliberate-promote, so it can't drift from intent). `refine` ≠ `plan` (item-level vs milestone-level). Optional L1 review (well-formed/testable?).
**Co-review feedback → sharper refinement:** the refine agent reads guidance distilled from DASH-08 co-reviews — current roadmap direction, acceptance-shape patterns that passed, recurring trim/staleness reasons — stored in a **small dedicated guidance file** (e.g. `docs/backlog/.refine-guidance.md`), **not** `repo_memory` (a 30-item-capped entry-point CLI, not a queryable index). Promote lessons there per the Memory Contract; sharpens over time.

### DASH-24 — Backlog↔Roadmap async coupling contract
`infra · target: v0.2 · policy`
Different cadences, kept decoupled: **backlog = async, append-only producer** (real-time capture, any session — DASH-02; never blocks/touches the roadmap); **roadmap = deliberate, periodic consumer/curator** (pulls only in `roadmap` sessions). Model = **async-capture / deliberate-promote** (an inbox). They couple **only** at the DASH-08 joint co-review transaction. **Race-freedom (corrected):** capture is *append-only & multi-instance* (atomic single-line append — no shared-field writes, no capture-time dedup); every **promoting** transition (refine, schedule, dedup/merge) happens at a **single-writer, deliberate gate**. So concurrency is confined to safe appends; all mutation of existing rows is single-writer.

The transaction mechanism is explicit: acquire `docs/backlog/.board.lock`, read `_meta.rev` from `roadmap.json` plus the item file hash, prepare new `items.jsonl` and `roadmap.json` in temp files, abort if rev/hash changed, rename both into place, increment rev, release lock, then run `board render`. If any check fails, leave the old stores untouched and ask the operator to re-open the roadmap snapshot. Co-review also emits the refinement-guidance feedback for DASH-23.

---

## B. Roadmap mode  · `project-meta`

### DASH-05 — `/project-meta roadmap` collaborative mode
`feat · target: v0.2 · Opus/main`
A new recipe `recipes/roadmap.md`, distinct from `plan`. Proposes a roadmap, **asks meaningful questions, co-builds it with the operator** (interactive). New verb → goes through the Reserved-Commands promotion path (DASH-17).

### DASH-06 — Version-milestone model
`feat · target: v0.2 · CLI`
Each milestone ↔ a **version number** (v0.1, v0.2, …); the roadmap is the versioned timeline, rendered as the ArkDisplay `ROAD` (done/now/todo) per version.

### DASH-07 — Roadmap review gate  → **folded into DASH-08**
`feat · target: v0.2`
The roadmap-only review (L2: feasibility/robustness/usefulness/usability) **is the roadmap-side lens-set of the DASH-08 joint co-review** — not a separate transaction. Kept as a pointer to avoid double-counting; the single review is DASH-08.

### DASH-08 — Joint backlog↔roadmap co-review (one transaction)
`feat · target: v0.2 · review-tier L2`
Grooming is **not** "clean backlog, then make roadmap" — it is a **single co-review transaction**: read *both* (roadmap draft + backlog snapshot), decide jointly, **write both back atomically** through the DASH-24 lock/rev/hash protocol so they can't diverge (a `refined` item is assigned to exactly one version or remains unscheduled). Decisions flow **both ways**: refined → versions; over-heavy version → defer back; off-direction → trim; new milestone goal → spawn items. **This is also where capture-time dedup is resolved** (single-writer gate). Reviewed at **L2** (review-tier skill): roadmap lenses (feasibility/robustness/usefulness/usability) + backlog lenses (still-relevant / refined-enough / right-version / staleness). Conflict resolution is operator-final inside the single roadmap session; mechanical conflicts abort and require a fresh snapshot.

---

## C. Orchestration  · **`orchestration` skill (split out)**

### DASH-09 — `orchestrate` mode
`feat · target: v0.3 · Opus/main`
For a chosen milestone: **task decomposition** (reuse the shipped `plan` build-plan) **+ an orchestration plan**. Recipe in the new orchestration skill. (Renamed from `autopilot`; the shipped `plan` `autopilot`/`goal`/`unattended` readiness keyword stays in project-meta.)

### DASH-10 — The orchestration contract artifact
`feat · target: v0.3 · Opus/main`
A **committed, reviewable contract** signed ahead of the run, per task: model tier (Opus hard vs Sonnet broad-parallel), parallelization, orchestrator effort, **human-in-the-loop** checkpoints, **review level** (review-tier skill), and a **budget hint** (DASH-22). The contract is the single owner of this schema.

### DASH-11 — Contract → engine handoff
`infra · target: v0.3 · engine`
The signed contract is **emitted to the engine**. **Opt-in posture (precise):** orchestration is **user-invoked** and its instructions name the tool + its cost surface → it **may legitimately call the Workflow tool** — the sanctioned opt-in ("the user invoked a skill whose instructions tell you to call Workflow" + the two-bar rule's "a recipe that names the tool and its cost surface"). What it still does **not** do: **enable `ultracode` session-mode** (user-only), or call Workflow **autonomously / from a hook / when the user didn't invoke orchestrate**. **Cross-runtime:** emits **Claude Code Workflow** or **Codex Agents-SDK**, and **degrades to an Agent/Task subagent loop** when no scripted engine is available (AP-VAL-1 floor). AP-COORD-7: contract = policy, engine = mechanism — no self-built run loop. The compliant replacement for the KILL'd `autopilot` run-engine.

### DASH-22 — Budget hint (non-predictive)
`feat · target: v0.3 · CLI`
A **coarse, explicitly non-predictive** budget *hint* to set expectations before signing — **not** a reliable forecast (pre-run agentic token/runtime prediction is order-of-magnitude unreliable). Hint = model-tier × fan-out × a per-class token band (heuristic), shown as **wide low/expected/high ranges labeled "estimate, not a guarantee."** It does **not** drive the engine `budget` (skill can't control/enable the engine — AP-COORD-7). No calibration claim until a real cost corpus exists (prereq: add token/runtime fields to `dispatch_ledger.py` + collect actuals — a separate item). Purpose: let the operator eyeball "this contract is Opus-heavy / wide" and adjust tiers/parallelism.

---

## D. Dashboard frontend  · `project-meta`

### DASH-12 — Self-contained interactive `dashboard.html`
`feat · target: v0.1 · CLI`
Zero-dependency static HTML at `docs/dashboard.html`, using the ArkDisplay render idiom (embedded data arrays + render + filter/expand). Sections: roadmap-by-version timeline + backlog/issues kanban. A **derived view** over the `docs/backlog/` store. The *iterated form of user-facing documentation*.

### DASH-13 — In-place edit via File System Access API
`feat · target: v0.3 · CLI · experimental`
Edit issues/status **in the browser** → write back to the store via the **File System Access API** where supported; download-patched-store fallback elsewhere. This is an experimental convenience layer, not a core write path: v0.1/v0.2 canonical writes stay CLI-only because browser file-write support varies by runtime and local-file permission model.

### DASH-25 — Fuse the project's user-facing docs into the dashboard as a wiki
`feat · target: v0.2 read-only index; v0.3+ wiki/edit-back · CLI/Sonnet`
The dashboard is not only a status board — it **hosts the project's user-facing documentation as a navigable wiki**, fused into the **same self-contained HTML panel** (a "Docs/Wiki" section alongside Roadmap + Board). This is what *makes* the dashboard the iterated user-facing documentation (DASH-16): explanation + live status in one surface.
- **Derived, canonical-backed.** Source of truth = the repo's user-facing Markdown (README + `docs/*.md`, per `documentation-delivery.md`: purpose / usage / architecture / reviewed-behavior). `board render` (DASH-04) renders MD→HTML and embeds it; the wiki is a **derived view**, never a second canonical store (same source-of-truth discipline as the rest of the board).
- **v0.2 scope:** read-only docs index + rendered Markdown pages + simple links from docs to backlog/roadmap IDs. No wikilink graph, directives, citations, or browser edit-back.
- **v0.3+ scope:** richer ArkWiki / ArkDisplay render idiom (wikilink / directive / citation) and bidirectional cross-links: wiki pages ↔ backlog items ↔ roadmap versions. A feature's wiki page shows its current version + linked issues; a backlog item links to its wiki page; `[[wikilinks]]` resolve to in-panel navigation.
- **Edit-back (optional, v0.3+):** via the File System Access API (DASH-13), editing a wiki page writes back to its Markdown **source** (canonical), then re-renders — same edit-back model as the board (once-granted repo-root directory handle, persisted in IndexedDB; no per-save path picking).

### DASH-14 — Render pipeline  → **folded into DASH-04**
`infra · target: v0.1`
`board render` is a verb of `board.py` (DASH-04), not a separate component. Kept as a pointer.

---

## E. Cross-cutting & integration  · `project-meta`

### DASH-15 — Conductor / worker tiering doctrine
`infra · target: v0.1 · policy`
Main session = **conductor**; triggered side-work delegated by cost tier: **deterministic → CLI (no model)**; **judgment → Sonnet sub-agent (default)**; **primary/hard/milestone → main/Opus per the orchestration contract**. Ties AP-COORD-1 + multi-agent tier-selection.

### DASH-16 — Positioned as iterated user-facing documentation
`docs · target: v0.1 · n/a`
The board/dashboard is the **iterated form** of project-meta's user-facing documentation (`documentation-delivery.md`) — it **augments**, does not replace, the explanatory docs. v0.1 realizes this as a read-only `docs/dashboard.html` over roadmap/backlog state; DASH-25 then hosts explanatory docs inside the dashboard as a derived docs index/wiki so status + explanation become one living surface (the repo Markdown stays canonical).

### DASH-17 — Harness integration + validate coverage + verb policy
`infra · target: v0.2 · CLI`
`validate_target_harness.py` coverage for new artifacts; provenance on each; `init` scaffolds the board; `status`/`deliver` surface it. **New verbs go through the Reserved-Commands path** (`cli-command-patterns.md`): `roadmap` starts reserved → promoted on demonstrated demand + stable shape; `orchestrate` lives in the **orchestration skill**, not project-meta's route table. Do not bloat the core verb set.

### DASH-18 — Supersede piecemeal proposals into a unified proposal
`chore · target: v0.1 · Sonnet`
Stale source proposals have been trimmed; their surviving project-board/autopilot concepts are consolidated here. This backlog is now the sole source of truth for the board, roadmap, orchestration split, review-tier split, and v0.1-v0.3 sequencing. **Must keep dropped** the "provenance header comment" wording (contradicts DASH-01's comment-ban).

---

## F. Review-tier  · **shared infra in `project-meta`** (`references/review-tier.md` + `scripts/review_tier.py`; SHIPPED v0.2 wave 1)

> Right-sized review: every review **fast** + tokens **proportionate to stakes**. Between AP-COORD-2 (*must* review) and AP-COORD-4 (*don't* over-orchestrate). Consumed by project-meta's roadmap review (DASH-08) **and** — later — the orchestration skill via the root-skill pointer. (Originally split as its own skill; landed as shared infra — see *Skill split* design-change note.)

### DASH-19 — Review levels L0–L3
`feat · target: v0.2 · varies`

| Level | When | Mode | Cost |
|---|---|---|---|
| **L0 self-check** | trivial/mechanical: tiny diff, no behavior change, no MUST-rule, single file | conductor self-review vs checklist + deterministic linters only — no dispatch | ~free |
| **L1 single reviewer** | ordinary bounded change (bug fix, small feature) | one fresh **Sonnet** reviewer on diff+brief, single-vote (AP-COORD-2 default) | 1× Sonnet |
| **L2 multi-expert panel** | design plan / roadmap / cross-subsystem / harness or MUST-rule | **N parallel reviewers, distinct lenses** (feasibility·robustness·usefulness·usability, or correctness·security·repro), synthesized; majority where it gates | 3–4× Sonnet (+opt Opus synth) |
| **L3 adversarial + pressure** | highest stakes: new skill · MUST-rule · security · irreversible · public contract | L2 + adversarial refuters (refute-by-default, majority-kill) + `pressure_test_skill` + full critic suite; loop-until-dry opt | most expensive, reserved |

Reviewers run on **clean context** (diff+brief only — AP-COORD-2); L2/L3 panels **parallel** for speed.

### DASH-20 — Level scorer (heuristic + escalation gate)
`infra · target: v0.2 · CLI`
`review_tier.py` is a **heuristic pre-filter, not a deterministic classifier**: it keys off **mechanical** inputs only (diff size, file count, harness-path match) to suggest a **floor**. Judgment inputs (behavior-change, blast radius, reversibility, `semantic_scope`) are **not** computable from a diff → the conductor **escalates (never silently de-escalates for high stakes) and MUST state the level + why** (visible mis-tier, AP-COORD-5 sibling). `HARNESS_PROFILE` shifts the floor (`minimal` lower, `strict` +1).

### DASH-21 — Integration & reuse
`infra · target: v0.2 · n/a`
Consumed by existing review surfaces, not a parallel system: `audit`/`deliver` pick a level; **DASH-08 = an L2 instance**; the orchestration contract (DASH-10) references levels; the **code-diff path reuses `/code-review`'s effort tiers**. Surface as a `--level` override on review-bearing verbs (auto-derived by default).

---

## Open questions (resolve before the relevant entry ships)

- **Linear creds in headless capture** (DASH-02/03): the Track Loop is agent-MCP-only; a `claude -p` subprocess can't easily reach Linear. Likely: capture writes the **repo only**; the Linear mirror runs in the interactive session. Confirm.
- **Headless-hook promotion threshold** (DASH-02): dry-run is the first shipped mode; define the observed false-positive and approval criteria before enabling automatic append.
- **In-flight items on version-cut** (DASH-08): what happens to `status:scheduled`/`status:in_progress` items when a version closes. *Pre-decided default (v0.2 plan): **carry-over** to the next open version, never silent-drop, logged as a co-review note. Confirm at DASH-08 build.*
- **review-tier packaging** (F): *resolved — ships as **shared infra in `project-meta`** (not a skill).* Remaining: the exact cross-skill pointer shape the orchestration skill uses to consume it (decide when the orchestration skill is built, v0.3).

---

_23 distinct items (DASH-07→08, DASH-14→04 folded). Split: A/B/D/E/F = `project-meta` (F = review-tier shared infra) · C = `orchestration` skill. Tentative `target`s; real version assignment + stale-trim in `roadmap` grooming (DASH-08)._
