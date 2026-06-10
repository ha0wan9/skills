# Review Tier — right-sized review (L0–L3)

Shared infra inside `project-meta` — **not** a separate skill. Consumed by `audit`/`deliver`, by the roadmap co-review transaction (DASH-08), and — later — by the orchestration skill (the exact cross-skill pointer shape is an open question in `docs/backlog/project-board-system.md`). It sits between **AP-COORD-2** (you MUST review) and **AP-COORD-4** (don't over-orchestrate): every review is fast, and tokens are proportionate to stakes.

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
- The orchestration contract (DASH-10, future skill) references these levels per task.

Surface as a `--level` override on review-bearing verbs; auto-derived by default.
