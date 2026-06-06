---
artifact_name: project-board-v0.2-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: docs/backlog/project-board-system.md
project_scope: this repo only
owner: shared-user-facing
review_policy: per-wave fresh-context review before land (AP-COORD-2); milestone groom in DASH-08
last_reviewed: 2026-06-06
---

# Project Board v0.2 — Build Plan

**Milestone:** v0.2 "Roadmap and review layer" (11 items). Built in **3 dependency-ordered waves**, each shipped as its own reviewable PR (the v0.1 cadence), with a fresh-context review gate before every land.

> v0.1 shipped the store + CLI + dashboard. v0.2 adds the *grooming* layer: right-sized review, fuzzy→refined refinement, a collaborative roadmap mode, the joint co-review transaction, and dry-run autonomous capture — plus the docs-as-wiki fusion.

## Decisions locked (pre-decided defaults — drift fence)

1. **review-tier = shared infra in `project-meta`**, not a standalone skill (`references/review-tier.md` + `scripts/review_tier.py`, cited by the future orchestration skill via the root-skill pointer). *(operator-confirmed)*
2. **DASH-08 conflict resolution** = v0.1's mechanism: single-writer `board_lock` + optimistic `roadmap._meta.items_sha256` check. A stale snapshot aborts ("stale board snapshot") and requires a fresh read. No new locking machinery.
3. **In-flight items on a version cut** = **carry-over** to the next open version (re-tag `version`, keep `status`), never silent-drop. Logged as a co-review note. *(flag if you prefer auto-defer-to-pool)*
4. **DASH-02** ships **dry-run / audit-only** this milestone: a hook writes a candidate log; promotion to `inbox.jsonl` requires an interactive session. Automatic append is a later opt-in profile.
5. **Capture writes the repo only**; the Linear mirror (DASH-03, v0.3) runs interactively, never from the headless subprocess.

## Tiers (conductor/worker doctrine, DASH-15)

- **CLI (no model):** `review_tier.py` scorer, `board.py` mutations, validator checks.
- **Sonnet sub-agent:** refinement drafting (DASH-23), capture classification (DASH-02), per-wave review.
- **Opus / main (conductor):** roadmap co-build (DASH-05), co-review synthesis (DASH-08), wave sequencing.

---

## Wave 1 — Foundation: review-tier + async-coupling  *(this PR)*

| Item | Deliverable | Acceptance (falsifiable) |
|---|---|---|
| **DASH-19** | `references/review-tier.md` — L0–L3 levels (when · mode · cost), clean-context + parallel-panel rules | reference exists, linked from SKILL.md, validator green |
| **DASH-20** | `scripts/review_tier.py` — heuristic floor scorer from mechanical signals (lines, files, harness-path hit, new-skill, MUST-rule) + `HARNESS_PROFILE` shift + mandatory escalation caveat | `review_tier.py --files 1 --lines 5` → L0; `--harness-hit` → ≥L2; `--new-skill --profile strict` → L3; always prints the "floor, escalate on judgment" caveat |
| **DASH-21** | Integration: `audit`/`deliver` recipes reference levels; `--level` override documented; code-diff path reuses `/code-review` effort tiers (pointer) | recipes cite review-tier; no parallel review system introduced |
| **DASH-24** | Async-coupling policy: confirm the contract is documented (project-board-system.md) + mechanically backed; add a multi-instance inbox-append concurrency test | a test appends N rows concurrently to `inbox.jsonl` with zero loss/corruption |

**Wave-1 gate:** `validate_project_meta.py` green (new `check_review_tier`), fresh-context review CLEAN, version bump `project-meta` → 1.5.0.

## Wave 2 — Roadmap layer  *(next PR)*

| Item | Deliverable | Acceptance |
|---|---|---|
| **DASH-23** | `recipes/refine.md` + refine sub-agent flow reading `.refine-guidance.md`; `board.py refine` exists | a fuzzy inbox item → `refined` with scope/acceptance-shape/size; guidance file read; promotion confirmed |
| **DASH-05** | `recipes/roadmap.md` collaborative mode; promote `roadmap` from reserved → route table | `/project-meta roadmap` routes; asks meaningful questions; co-builds versioned milestones |
| **DASH-06** | Version-milestone model — close out (roadmap.json + dashboard render already ship it) | dashboard renders ROAD by version; acceptance recorded |
| **DASH-08** | **folded into `recipes/roadmap.md`** as its core transaction (no separate `co-review.md` — co-review IS the roadmap session): read both, write both atomically (board.py mechanism), resolve dedup, emit refine-guidance; L2 via review-tier | one transaction updates items+roadmap atomically; `refined` item is in one version XOR pool; L2 panel runs |

## Wave 3 — Capture + integration + wiki  *(later PR)*

| Item | Deliverable | Acceptance |
|---|---|---|
| **DASH-02** | `Stop`/`SessionEnd` command hook → shell prefilter → `claude -p --model sonnet` → **dry-run log**; interactive promote via `board.py inbox-add`; profile-gated | hook writes a candidate log, never auto-writes the store; `minimal` profile off |
| **DASH-17** | `validate_target_harness.py` coverage for board artifacts; `init` scaffolds the board; `status`/`deliver` surface it | validator covers board files; init creates the store; status shows it |
| **DASH-25** | MD→HTML at CLI render time (std-lib `md_to_html`+`collect_docs` in `board.py` — **not** `extract_doc_context.py`, which does bounded extraction, not rendering; keeping `board.py` self-contained) embedded as a Docs/Wiki dashboard section | `board render` embeds README + docs/*.md as navigable HTML; `[[wikilinks]]` resolve in-panel; zero client-side deps. **Shipped:** render + heading index + wikilink nav. **Deferred to v0.3:** deep item↔wiki↔version cross-links + edit-back (DASH-13) |

---

*Build order is dependency-driven, not item-number order. Each wave lands independently behind a fresh review. v0.2 closes when all three waves are merged and the dogfood board shows the v0.2 milestone `done`.*
