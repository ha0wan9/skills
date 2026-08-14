---
artifact_name: harness-tier-fit-ab-note
project_scope: this repo only
owner: agent-facing
produced_by: "DASH-083a (W1.2) under docs/plans/harness-tier-fit-v0.8-orchestration-contract.md"
status: "evidence — awaiting 🔴 operator evidence gate before DASH-083b (W1.3) dispatches"
last_reviewed: 2026-08-14
---

# Phase-Lock A/B Evidence Note (DASH-083a)

Tests A-2 (build plan §0, WORKING): "hard gates under `standard` provide enforcement
margin a Fable-class session no longer needs." Default on ambiguous evidence is
**keep-hard** (§8). Evidence only — no gate/hook/template/reference was edited.
Fixtures and softened script copies live under `.abnote-scratch/` in this worktree
(untracked, not committed); baselines for `implement.sh`/`finish.sh` run the real,
unmodified scripts against this live repo (read-only: `ship_plugin.sh validate` /
`check-version` write nothing) since both hardcode their target to the repo root
via `BASH_SOURCE` traversal — no state-file override exists for them, so a "wrong"
case is built with the env var they already support (`BASE_BRANCH=HEAD`, which
forces "no version bump since base" without touching any file).

## 1. Per-gate table

| Gate | Trigger | Standard baseline (today) | Strict baseline (today) | Softened simulation (standard) |
|---|---|---|---|---|
| `brainstorm.sh` | phase=brainstorm | exit 0 always — stub, no check exists | exit 0 always (identical) | n/a — nothing to soften |
| `plan.sh` | phase=plan | pass: exit 0 · fail (no/absent `build_plan`): **exit 1, hard, no WARN** | byte-identical output+exit to standard | fail → `WARN (softened-sim): ...` + exit 0; pass unchanged |
| `implement.sh` | phase=implement | pass (live repo): exit 0 · fail (`BASE_BRANCH=HEAD`): **exit 1, hard** | fail case identical (exit 1); pass case has a confound, §4 | fail → WARN + exit 0; pass unchanged |
| `review.sh` | phase=review | pass: exit 0 · fail (missing file / empty `review_tier`): **exit 1, hard, no WARN** | byte-identical to standard | fail → WARN + exit 0; pass unchanged |
| `finish.sh` | phase=finish | pass (live repo): exit 0 · fail (`BASE_BRANCH=HEAD`): **exit 1, hard** | byte-identical to standard | fail → WARN + exit 0; pass unchanged |

All 10 fixture runs (5 gates × pass/fail) plus their strict counterparts and softened
re-runs were executed directly; none of the 5 scripts reference `$HARNESS_PROFILE` today
(confirmed by full read), so standard and strict are identical everywhere in column 2 vs 3.

## 2. What's already soft today (scoping finding)

The "hard, no-WARN" row above is **not** what a Fable session hits on a normal turn.
`.claude/hooks/verify-before-stop.sh` (the actual `Stop` hook) already wraps its
phase-lock call in `advisory_exit()` (lines 45-54): standard → warn + exit 0, strict →
exit 1 (line 98's call site; the "Invariant/core gates read raw HARNESS_PROFILE only"
comment at line 86 documents the intent). So **the routine, every-turn enforcement path
is already advisory under standard**, with zero change needed. The genuinely-hard
surface found in §1 is reached only via two secondary paths, neither profile-aware:
(a) direct/manual `bash .harness/gates/<phase>.sh` or a bare `phase_lock_check.py`
call (no `os.environ.get("HARNESS_PROFILE"...)` anywhere in that 183-line script —
confirmed by full read), and (b) `/project-meta validate`'s
`phase_lock_check.py --require-pass` call (`skills/project-meta/recipes/validate.md:33`).

## 3. Evidence from history (SAVE vs FRICTION)

- `.harness/lessons.jsonl` — **does not exist** in this repo (untracked, absent on disk) → 0 hits.
- `.harness/bypass-log.jsonl` — **does not exist** (untracked, absent on disk) → the
  documented escape hatch (§ Bypass, `agents/phase-lock-contract.md`) has 0 logged uses.
- `git log --all --grep` (`phase-lock`/`phase_lock_check`/`gate fail`, case-insensitive)
  → 11 unique commits total; only **two** ever touched gate logic: `14120b2`
  (2026-06-13, "Enable 4 harness capabilities" — installs *dormant, passing stubs*)
  and `92cc776` (2026-07-07, DASH-064, "real phase-lock gates" — the only commit that
  ever wrote the current plan/implement/review/finish check logic). Both are
  feature-build commits; neither message, nor the DASH-064 board item
  (`docs/backlog/items.jsonl`, status=done, no delta note), documents a caught mistake
  or a blocked/forced-workaround.
- `AUDIT.md:85` mentions `phase_lock_check.py` once, but it is a *different* tool's
  false positive (`determinism_gap_scan.py` matching `**/hooks/*.sh` instead of
  `**/hooks/scripts/*.sh`) — not a phase-lock gate event. Not counted.
- **Tally: SAVE = 0, FRICTION = 0.** No git-visible incident in the ~5.5 weeks the
  gates have carried real logic (2026-07-07 → today 2026-08-14), nor in the ~2
  months since phase-lock was enabled at all (2026-06-13, dormant stubs at first).

## 4. Confound observed while testing

Running `implement.sh` for real with `HARNESS_PROFILE=strict` (default `BASE_BRANCH=main`,
project-meta genuinely changed on this branch) fails **for an unrelated reason**:
`ship_plugin.sh validate` → `validate_project_meta.py`'s `check_review_tier()`
(`scripts/validate_project_meta.py:1388-1411`) shells out to
`review_tier.py --files 1 --lines 5` expecting `"L0"`, but `review_tier.py` defaults
its profile from the ambient `$HARNESS_PROFILE`
(`skills/project-meta/scripts/review_tier.py:115-116`), so
under strict the floor shifts to `L1` and the hardcoded self-check fails. This is
real and reproducible, but orthogonal to phase-lock — it shows `HARNESS_PROFILE` is
already a shared dial with independent consumers, which is why §1's `implement.sh`
fail case uses the confound-free `BASE_BRANCH=HEAD` fixture instead.

## 5. Analysis

Doctrine (A-1) favors de-prescription in general, but this repo's own history gives
this specific hypothesis (A-2) nothing to confirm it *or* deny it: the gates are
mechanically real, not rubber stamps (§1 shows correct pass/fail discrimination on
both isolated and live-repo fixtures), the main enforcement path is already soft
under standard (§2), and the narrow remaining hard surface has a clean 0/0
SAVE/FRICTION record for the entire ~5.5 weeks it has run real checks (§3) —
textbook ambiguous evidence.
DASH-083b is independently gated at L3 (gate-authority MUST-rule floor) precisely
because a silent weakening here is expensive if wrong, and §4 shows the obvious
implementation shortcut (a raw `if $HARNESS_PROFILE == strict` in the gate scripts)
would add a second consumer to an already-overloaded dial. Weak-to-no upside plus a
real downside path argues for the plan's own pre-decided tie-breaker.

## 6. Verdict

**VERDICT: keep-hard**

Exception: `brainstorm.sh` is moot, not "kept hard" — it is already an unconditional
`exit 0` stub with no check to soften. DASH-083 completes as "evidence rejected
softening" per build plan §8; the 🔴 operator gate decides whether W1.3 dispatches at all.
