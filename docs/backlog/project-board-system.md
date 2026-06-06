---
artifact_name: project-board-system-backlog
kind: feature-backlog
project_scope: project-meta — Roadmap / Orchestration / Dashboard system
owner: user-reviewed
status: proposed (untriaged into versions)
source_reference: design conversation 2026-06-06; unified proposal (to supersede proposals/persistent-project-dashboard.md + proposals/autopilot.md)
review_policy: groom + version-assign during /project-meta roadmap (DASH-08); this is the seed instance (dogfooding)
last_reviewed: 2026-06-06
---

# Feature Backlog — Project Board System (Roadmap · Orchestration · Dashboard)

The persistent, CLI-managed, repo-canonical project surface — **Backlog/Issues → Roadmap (versioned) → Orchestration contract → /workflows**, rendered to a static interactive `dashboard.html` (the *iterated form of user-facing documentation*), with optional Linear mirror.

> **Dogfooding note.** This file is itself the first backlog the system would manage. Per the design, **version assignment + stale-trimming is deferred to `roadmap` grooming (DASH-08)** — the `target` fields below are tentative, set during roadmap review, not here.

**Legend** — `kind`: feat (capability) · infra (plumbing) · docs · chore. `tier`: which model executes (CLI = no model · Sonnet = dispatched worker · Opus/main = primary). `target`: tentative version, TBD in grooming.

---

## A. Backlog & Issue system (the capture pool)

### DASH-01 — Repo-canonical backlog/issue/bug store
`infra · target: v0.1 · CLI`
Features/issues/bugs live in `docs/backlog/` (repo = source of truth; HTML derived; Linear mirror). **Parseable format** — first-line `{"_meta":…}` object or a sidecar `.provenance`, **never `#` comments** (they break JSON/JSONL — board-review Blocker #1). Statuses include an `untriaged` holding state.

### DASH-02 — Autonomous out-of-scope capture via headless Sonnet agent
`feat · target: v0.1 · Sonnet`
When the agent surfaces a feature/bug **out of the current session's scope**, capture it autonomously. Mechanism: a `Stop`/`SessionEnd` **command hook** → cheap shell pre-filter (only on feature/bug-shape language) → **headless Sonnet agent** (`claude -p --model sonnet`, has tools) → dedup-check `docs/backlog/` → record. Keeps main context clean. Profile-gated (`minimal` off); `SessionEnd`-tendency to avoid over-fire (AP-VAL-1). Captured items land **`untriaged`** — never auto-promoted to a roadmap/version.
> Caveat: native `agent`-type hooks are tool-events-only, so capture uses *command hook → headless Sonnet*, not an agent-type hook on Stop.

### DASH-03 — Optional Linear mirror (push-only)
`feat · target: v0.2 · Sonnet`
Reuse the existing `issue-tracker` Track Loop: repo canonical → Linear; check / write-progress-back / open-if-missing; body **links back** to the repo entry; mirror `linear_id` into the row. **Push-only** — document the reverse-drift caveat (a human editing Linear directly is not pulled back; board-review Major #6).

### DASH-04 — Backlog CLI (CRUD + render trigger)
`infra · target: v0.1 · CLI`
`scripts/board.py` (std-lib, deterministic): `add / move <id> <status> / edit / list / render`. The write surface the Sonnet capture agent (DASH-02) and humans both use. Every mutation auto-triggers render (DASH-14).

---

## B. Roadmap mode

### DASH-05 — `/project-meta roadmap` collaborative mode
`feat · target: v0.2 · Opus/main`
A new recipe `recipes/roadmap.md`, distinct from `plan`. Proposes a roadmap, **asks meaningful questions, co-builds it with the operator** (interactive, not one-shot).

### DASH-06 — Version-milestone model
`feat · target: v0.2 · CLI`
Each milestone ↔ a **version number** (v0.1, v0.2, …). The roadmap is the versioned timeline; the dashboard renders it as the ArkDisplay-style `ROAD` (done/now/todo) per version.

### DASH-07 — Roadmap review gate
`feat · target: v0.2 · Sonnet (panel)`
Each built/revised roadmap passes a **review**: feasibility · robustness · usefulness · usability (per feature). Reuse the skill-critic / multi-agent review machinery; GO/NO-GO style, no gamed numeric score. **This is an L2 instance of DASH-19's tiered review.**

### DASH-08 — Backlog grooming coupled to roadmap
`feat · target: v0.2 · Sonnet`
On roadmap build/review, **groom the backlog together**: assign items to versions, **trim stale/unneeded** features & bugs → keep the backlog clean. This is where DASH-02 captures get triaged out of `untriaged`.

---

## C. Orchestration mode (formerly "autopilot")

### DASH-09 — `/project-meta orchestrate` (mode: orchestration)
`feat · target: v0.3 · Opus/main`
For a chosen milestone (e.g. v0.2): produce a **task decomposition** (reuse the shipped `plan` falsifiable build-plan) **+ an orchestration plan**. New recipe `recipes/orchestrate.md`. (Renamed from `autopilot`; the shipped `plan` `autopilot`/`goal`/`unattended` readiness keyword stays.)

### DASH-10 — The orchestration contract artifact
`feat · target: v0.3 · Opus/main`
A **committed, reviewable contract** signed ahead of the run, per task: model tier (**Opus** for hard tasks vs **Sonnet** for broadly-parallel ones), which tasks parallelize, the **orchestrator's effort level**, **human-in-the-loop** checkpoints, and where **multi-agent critical review** is required (review intensity per the DASH-19 levels).

### DASH-11 — Contract → engine handoff
`infra · target: v0.3 · engine`
Emit the contract to **`/workflows`** (+ `/loop`). AP-COORD-7: **contract = policy, engine = mechanism — no self-built run loop**. This is the AP-COORD-7-compliant replacement for the KILL'd `autopilot` run-engine.

---

## D. Dashboard frontend

### DASH-12 — Self-contained interactive `dashboard.html`
`feat · target: v0.1 · CLI`
Zero-dependency static HTML using the ArkDisplay render idiom (embedded data arrays + render + filter/expand). Sections: **roadmap-by-version timeline** + **backlog/issues kanban**. A **derived view** over the store. The *iterated form of user-facing documentation*.

### DASH-13 — In-place edit via File System Access API
`feat · target: v0.2 · CLI`
Edit issues/status **in the browser** and write back to the store via the **File System Access API**; download-patched-store fallback. Zero server, stays static + cross-runtime (board-review Major #7's missed middle option).

### DASH-14 — Deterministic render pipeline
`infra · target: v0.1 · CLI`
`board render`: pure CLI injects the store into the HTML template's data arrays; auto-runs after every mutation. The HTML is **always derived, never hand-edited**.

---

## E. Cross-cutting principles & integration

### DASH-15 — Conductor / worker tiering doctrine
`infra · target: v0.1 · policy`
Main session = **conductor**; all triggered side-work is delegated by cost tier: **deterministic mechanics → CLI (no model)**; **judgment-bearing side-tasks → Sonnet sub-agent (default tier)**; **primary/hard/milestone work → main agent / Opus per the orchestration contract**. Ties AP-COORD-1 + the existing multi-agent tier-selection.

### DASH-16 — Positioned as iterated user-facing documentation
`docs · target: v0.1 · n/a`
The board/dashboard is the **iterated form** of project-meta's user-facing documentation (`documentation-delivery.md`) — it **augments**, does not replace, the explanatory user-facing docs (board-review Major #5).

### DASH-17 — Harness integration + validate coverage
`infra · target: v0.2 · CLI`
Add `roadmap` / `orchestrate` to the route table (`cli-command-patterns.md`); `validate_target_harness.py` coverage for the new artifacts; provenance on every artifact; `init` scaffolds the board; `status`/`deliver` surface it.

### DASH-18 — Supersede piecemeal proposals into one unified proposal
`chore · target: v0.1 · Sonnet`
Fold `proposals/persistent-project-dashboard.md` + `proposals/autopilot.md` into a single unified proposal; mark the originals superseded.

---

## F. Tiered review system (right-sized `review` levels)

> **Core idea:** every review should be **fast** and spend **tokens proportionate to the change's stakes**. A one-line bug fix gets a light check; a design plan gets a many-sided review. The level is **derived from the change, not guessed** — sitting exactly between AP-COORD-2 (*must* review) and AP-COORD-4 (*don't* over-orchestrate). Consumed by DASH-07 and DASH-10, not a parallel system.

### DASH-19 — Review levels L0–L3 (per-level modes)
`feat · target: v0.2 · varies`
Four cost-proportionate levels; each fixes *who reviews and how*:

| Level | When (derived) | Mode | Cost |
|---|---|---|---|
| **L0 · self-check** | trivial/mechanical: tiny diff, no behavior change, no MUST-rule, single file | conductor self-review vs a checklist + the deterministic linters/validators only — **no dispatch** | ~free, instant |
| **L1 · single reviewer** | ordinary bounded change: a bug fix, small feature, recipe edit | one fresh **Sonnet** reviewer on diff+brief, single-vote (the AP-COORD-2 gate default) | 1× Sonnet |
| **L2 · multi-expert panel** | design plan / roadmap / cross-subsystem / harness or MUST-rule touched | **N parallel reviewers, each a distinct lens** (feasibility · robustness · usefulness · usability — or correctness · security · repro), synthesized; majority where it gates | 3–4× Sonnet (+ optional Opus synth) |
| **L3 · adversarial + pressure** | highest stakes: new skill · MUST-rule · security · irreversible migration · public contract | L2 panel **+ adversarial refuters** (refute-by-default, majority-kill) **+ `pressure_test_skill`** on MUST-rules **+ the full deterministic critic suite**; loop-until-dry optional | most expensive, reserved (Opus on hard lenses) |

Reviewers always run on **clean context** (diff + brief only, never the conductor's context — AP-COORD-2); L2/L3 panels run **in parallel** for speed.

### DASH-20 — Deterministic level derivation (the scorer)
`infra · target: v0.2 · CLI`
`scripts/review_tier.py` maps change characteristics → a **suggested level**: diff size, file count, harness-file touched?, behavior-change?, MUST-rule touched?, artifact class (code / design-plan / skill / memory / config), blast radius / reversibility, semantic_scope. The conductor **may escalate (never silently de-escalate for high-stakes)** and **MUST state the chosen level + why in the delivery** — visible mis-tier, the read-pattern-derivation analog (AP-COORD-5 sibling). `HARNESS_PROFILE` shifts the floor: `minimal` caps lower, `strict` bumps up one.

### DASH-21 — Integration & reuse (no new review machinery)
`infra · target: v0.2 · n/a`
Levels are consumed by existing review surfaces, not a parallel system: `audit`/`deliver` pick a level via DASH-20; **DASH-07 roadmap review = an L2 instance**; **DASH-10 orchestration contract references these levels** for "where multi-agent critical review is needed"; the **code-diff path reuses `/code-review`'s effort tiers** (low/med/high/max/ultra). Surface as a `--level` override on the review-bearing verbs (auto-derived by default), or a standalone `/project-meta review` verb (TBD).

---

_21 entries. Tentative `target`s are placeholders; real version assignment + stale-trim happens in `roadmap` grooming (DASH-08)._
