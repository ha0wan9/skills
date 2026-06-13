# Review Tier — right-sized review (L0–L3)

Shared infra inside `project-meta` — **not** a separate skill. Consumed by `audit`/`deliver`, by the roadmap co-review transaction (DASH-08), and by the **orchestration skill** (shipped — its SKILL.md cites this file as the L0–L3 canon; this file stays canonical). It sits between **AP-COORD-2** (you MUST review) and **AP-COORD-4** (don't over-orchestrate): every review is fast, and tokens are proportionate to stakes.

## Levels

| Level | When | Mode | Cost |
|---|---|---|---|
| **L0 self-check** | trivial/mechanical: tiny diff, no behavior change, no MUST-rule, single file | conductor self-review vs a checklist + deterministic linters only — no dispatch | ~free |
| **L1 single reviewer** | ordinary bounded change (bug fix, small feature) | one fresh **Sonnet** reviewer on diff+brief, single-vote (AP-COORD-2 default) | 1× Sonnet |
| **L2 multi-expert panel** | design plan / roadmap / cross-subsystem / harness-path change | **N parallel reviewers, distinct lenses** (feasibility·robustness·usefulness·usability, or correctness·security·repro), synthesized; majority where it gates — this IS the fleet-panel mechanism described in the model-tier canon (`multi-agent-protocols.md#model-tier`); no separate panel system exists | 3–4× Sonnet (+opt Opus synth) |
| **L3 adversarial + pressure** | highest stakes: new skill · MUST-rule change · security · irreversible · public contract | L2 + adversarial refuters (refute-by-default, majority-kill) + `pressure_test_skill` + full critic suite; loop-until-dry opt | most expensive, reserved |

Reviewers run on **clean context** (diff + brief only — AP-COORD-2); L2/L3 panels run **in parallel** for speed.

**Profile × stakes interaction (read before trusting the floor):** `review_tier.py` returns **L3 for a new-skill or MUST-rule change** — the *high-stakes floor* — and `--profile minimal` can **never** lower that. `minimal` *can* lower the ordinary size/scope-derived floor by one (e.g. a harness-path change L2 → L1) to cut ceremony in low-stakes repos; `strict` raises it by one. So a harness-path change is L2 by default but not a protected floor; *changing or adding* a MUST-rule is the protected L3, while merely editing code *governed by* a harness path is L2.

## Scorer — `scripts/review_tier.py` (heuristic floor, NOT a classifier)

`review_tier.py` keys off **mechanical inputs only** — lines changed, file count, harness-path hit, new-skill, MUST-rule — to suggest a **floor**. It cannot see the judgment inputs that actually drive stakes:

- **behavior-change, blast radius, reversibility, `semantic_scope`** are not computable from a diff.

Therefore the conductor **escalates on judgment** (never silently de-escalates for high stakes) and **MUST state the chosen level + why** in the delivery — a visible mis-tier is the AP-COORD-5 sibling. `HARNESS_PROFILE` shifts the floor: `minimal` lowers it (but never below the new-skill/MUST-rule L3 floor), `strict` adds one.

```
python3 scripts/review_tier.py --diff main...HEAD --profile strict
python3 scripts/review_tier.py --files 1 --lines 8            # -> L0
python3 scripts/review_tier.py --harness-hit                  # -> L2
python3 scripts/review_tier.py --new-skill --profile strict   # -> L3
```

It prints the suggested level, the signals it used, and the mandatory "floor — escalate on judgment" caveat. It is advisory (exit 0); the conductor owns the final call.

## Integration (DASH-21) — reuse, don't build a parallel system

- **`audit` / `deliver`** pick a level for their review step (auto-derived by `review_tier.py`, overridable with `--level`).
- **DASH-08 joint co-review is an L2 instance** — roadmap lenses + backlog lenses run as the parallel panel.
- The **code-diff path reuses `/code-review`'s effort tiers** rather than re-implementing reviewer dispatch.
- The orchestration contract (DASH-10 — shipped as the `orchestration` skill) references these levels per task; that skill cites this file as canon and never duplicates it.

Surface as a `--level` override on review-bearing verbs; auto-derived by default.

## Plan-time risk rubric — `scripts/risk_score.py`

`risk_score.py` is the **deriving function** that fills the gap the Scorer section calls out: the judgment inputs (`behavior-change`, `blast-radius`, `reversibility`, `semantic_scope`) are not computable from a diff, so this rubric collects them explicitly at plan time and DERIVES — never replaces — the L0–L3 tier.

**7 dimensions** (each scored 1–3):

| Dim | What it measures |
|---|---|
| `scope` | breadth of change — single component → cross-system |
| `dependencies` | external coupling — none → many/unclear |
| `blocking` | how many downstream tasks this blocks |
| `stability` | maturity of the area — stable/tested → volatile/experimental |
| `ux` | surface area for user-visible breakage |
| `testing` | coverage/observability — well-tested → hard to verify |
| `reversibility` | ease of rollback — trivially reversible → irreversible |

**Bands** (total = sum of 7 dims, range 7–21):

| Total | Band | Review-tier floor | Readiness | Sequencing hint |
|---|---|---|---|---|
| 7–11 | proceed | L1 | floor | no sequencing constraint |
| 12–16 | incremental | L2 | strict | schedule mid-version after dependencies land |
| 17–21 | spike-first | L3 | strict | spike before scheduling; schedule early in its version |

**How it composes with `review_tier.py`:** the output is a **FLOOR recommendation** — take the **max** of the risk-score tier and `review_tier.py`'s mechanical floor. Risk can only raise the tier, never lower it.

**Readiness keyword advisory:** `strict` means elevated attention is warranted; it does NOT override the keyword the plan already carries. The plan keyword is authoritative; risk can raise attention, never lower a keyword-set tier.

```
python3 scripts/risk_score.py --scope 3 --dependencies 3 --blocking 3 --stability 3 \
    --ux 3 --testing 3 --reversibility 3 --json   # -> total=21, band=spike-first, review_tier=L3
python3 scripts/risk_score.py --scope 1 --dependencies 1 --blocking 1 --stability 2 \
    --ux 1 --testing 1 --reversibility 1          # -> total=8, band=proceed, review_tier=L1
python3 scripts/risk_score.py --scope 2 --dependencies 2 --blocking 2 --stability 2 \
    --ux 2 --testing 2 --reversibility 2 --write-context  # writes .harness/risk-context.json
```

Output includes the total, band, the three derived recommendations, dims used, and the mandatory "floor — escalate on judgment" caveat. Advisory: always exits 0 (exit 2 only on bad invocation); the conductor owns the final call.
