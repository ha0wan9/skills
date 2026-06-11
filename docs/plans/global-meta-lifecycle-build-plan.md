---
artifact_name: global-meta-lifecycle-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: docs/backlog/project-board-system.md; skills/project-meta/proposals/global-meta.md
project_scope: this repo only
owner: shared-user-facing
review_policy: user review when goal or readiness changes; per-PR fresh-context review before land
last_reviewed: 2026-06-11
readiness: strict
goal: "Ship the v0.5 milestone: global-meta gains read-only status+audit (config_root_audit.py + snapshot ledger) and audit --emit-fix; the marketplace slimming question gets a sandboxed GO/NO-GO verdict; the scope-aware reload lands; the proposal records the verdict. DASH-042 (slimming implementation) is checkpoint-gated and NOT built in this run."
---

# global-meta lifecycle (v0.5) — Build Plan

**Milestone:** v0.5 "global-meta lifecycle + marketplace hygiene" — DASH-039/034/035/036/037/038
(board rev 43). Executed as dependency-ordered waves, one PR per item, fresh-context review
before every land, sequential lands by the Lead (manifest-collision avoidance).

## §1 Goal & non-goals

**Done =** DASH-039, -034, -035, -037, -038 land on main with green gates; DASH-042 has a
recorded spike verdict and stays checkpoint-gated.

**Non-goals (drift fence):**
- NO dotfiles-git `track` verb (deferred — the snapshot ledger covers rollback).
- NO standalone `drift` / `reconcile` / `settings` verbs (folded into `audit` / `--emit-fix` / cut).
- NO Codex-side write paths — Codex legs of audit are read-only inventory only.
- NO marketplace slimming *implementation* this run (DASH-042 is 🔴-gated).
- NO autonomous application of emitted fix scripts to the real config root.
- NO `claude plugin marketplace add/remove` against the real config root — sandbox via
  `CLAUDE_CONFIG_DIR` only (multiclaude-marketplace-guard; the 2026-06-10 registry wipe is the precedent).

## §2 Run discipline

- **Gate command:** `scripts/ship_plugin.sh validate` (manifest sanity + version gate + dev
  validators) **plus**, for any `skills/*` change: `python3
  skills/project-meta/scripts/skill_architecture_lint.py .` (0 FAIL) and `python3
  skills/project-meta/scripts/trigger_collision_check.py .` (0 findings). Excludes: advisory
  critics (report-only by design — promoted separately).
- **Branch rule:** one feature branch + PR per item; never commit to main. Workers build in
  `.claude/worktrees/*`; the Lead reviews, lands sequentially, reruns gates post-merge.
- **Push rule:** push only via `ship_plugin.sh open`; merge only after a fresh-context review
  agent returns no blocking findings (gate 3); `land` enforces version + mergeability + audit-ledger gates.
- **Post-merge rerun (exact):** after every land, from updated main run all three:
  `scripts/ship_plugin.sh validate` && `python3 skills/project-meta/scripts/skill_architecture_lint.py .`
  && `python3 skills/project-meta/scripts/trigger_collision_check.py .` — same thresholds as pre-merge.
- **Lockstep checklist (silent red-gate traps):**
  - SKILL.md `description` changed → re-copy **verbatim** into `marketplace.json` (validator checks version, not description — drift here is silent).
  - New verbs in global-meta → update SKILL.md Trigger Decision + When-To-Load + AGENTS.md/README routing rows in the same PR.
  - Every PR bumps its changed plugin(s) (`ship_plugin.sh bump`); root-only changes bump `marketplace`.
  - `/bin/bash -n` any touched shell script under **bash 3.2** (no mapfile/assoc arrays).

## §3 Tiers

| Item | Tier | Why |
|---|---|---|
| DASH-043 scope-aware reload | 🟢 autonomous — **DONE** (PR #43 landed 2026-06-11, main e4bd7c3) | chip-authored diff; gates were mechanical |
| DASH-044 proposal write-back | 🟢 autonomous | docs-only; collision check is the gate |
| DASH-039 status+audit | 🟡 fixture-bound | built against the committed seeded fixture (§4 F1–F4) |
| DASH-040 emit-fix | 🟡 fixture-bound | converge-the-fixture-copy loop is the acceptance |
| DASH-041 slimming spike | 🟡 autonomous-against-a-specced-fixture (runtime-generated per §4, not committed) | sandboxed `CLAUDE_CONFIG_DIR`; read-only intent on the real root — see §7.2 caveat |
| DASH-042 slimming impl | 🔴 checkpoint | distribution-semantics change; needs spike GO + operator approval |

## §4 Preflight & fixtures

Preflight (all must pass before Wave 1):
```bash
python3 --version            # 3.x present
/bin/bash --version | head -1  # 3.2 — the compat target
gh auth status               # push/merge capability
claude --version             # plugin CLI present
python3 skills/project-meta/scripts/worktree_audit.py --target-root . --base main  # clean slate
```

Fixtures:
- **F-audit (COMMITTED):** `skills/global-meta/examples/audit-fixture/` (seeded findings
  F1 `stale-enablement` · F2 `wrong-scope` · F3 `dup-scope-records` · F4 `cache-version-mismatch`)
  and `skills/global-meta/examples/audit-fixture-clean/` (zero findings). The fixture
  `README.md` is the contract: layout mapping, JSON schemas, and path-resolution rules
  (relative `installPath` = fixture-root-relative; `--home-dir` for the local-scope spec;
  `--spec-marketplace test-mkt`). `config_root_audit.py` itself is DASH-039's deliverable —
  built against this pre-committed data, so the §6 rows are falsifiable before the run.
- **F-spike (specced, /tmp, not committed):** `/tmp/gm-spike-home/` (throwaway
  `CLAUDE_CONFIG_DIR`) + `/tmp/gm-spike-mkt/` (minimal marketplace). Marketplace manifest shape:
  ```json
  {"name": "gm-spike", "owner": {"name": "spike"},
   "plugins": [
     {"name": "scoped-test", "version": "0.0.1", "source": "./plugins/scoped-test", "skills": ["./"]},
     {"name": "root-test",   "version": "0.0.1", "source": "./",                    "skills": ["./skills/root-test"]}
   ]}
  ```
  Each skill dir carries a minimal `SKILL.md` (`name` + `description` frontmatter); the repo
  root carries decoy files so the copy boundary is observable. Generated by the spike, deleted after.
- **Real-root read-only checks:** hash `~/.claude-shared/plugins/installed_plugins.json` and
  `~/.claude-shared/enabled-plugins.local.json` before/after any real-root audit run; hashes must be identical.

## §5 Build order

1. **Wave 0 (Lead, inline) — DONE 2026-06-11:** DASH-043 shipped as PR #43 (chip-authored
   branch `ship-reload-scope-aware`, fresh review APPROVE, landed; main `e4bd7c3`).
2. **Wave 1 (parallel, Sonnet workers):** DASH-039 (worktree; owns ALL `skills/global-meta/` edits
   incl. its arbitration row) ∥ DASH-041 (read-only spike, no repo edits) ∥ DASH-044 (worktree;
   owns `skills/project-meta/proposals/` + `skills/meta-debug/` rows — never touches `skills/global-meta/`).
3. **Land sequence:** 038 → 033 (Lead rebases second land if manifest hunks collide).
4. **Wave 2 (after 033 lands):** DASH-040 (worktree; builds on the landed `config_root_audit.py`).
5. **Wave 3 (🔴, not this run):** DASH-042 — only after spike GO + operator approval.

## §6 Per-item verification matrix

| Item | Test target (exact command / assertion) | Data | Threshold |
|---|---|---|---|
| DASH-043 ✅ | `/bin/bash -n scripts/ship_plugin.sh` && `scripts/ship_plugin.sh validate`; fresh review of PR #43 | live repo + `~/.claude-shared/plugins/installed_plugins.json` | **met 2026-06-11**: both exit 0; review APPROVE (0 blocking); PR #43 MERGED |
| DASH-039 | `python3 skills/global-meta/scripts/config_root_audit.py audit --config-home skills/global-meta/examples/audit-fixture --home-dir /Users/HaoranWang --spec-marketplace test-mkt` → report; same command against `skills/global-meta/examples/audit-fixture-clean`; `cp -R skills/global-meta/examples/audit-fixture /tmp/gm-fixture-copy && … snapshot --config-home /tmp/gm-fixture-copy --snapshot-root /tmp/gm-snapshots && … restore --dry-run --config-home /tmp/gm-fixture-copy --snapshot-root /tmp/gm-snapshots`; real-root run with before/after hashing | F-audit (committed at `skills/global-meta/examples/audit-fixture{,-clean}/`) + `/tmp/gm-fixture-copy` | seeded run: exit 1 **and** all four codes F1–F4 in the report **and** ≥1 capture line matching the §8 format; clean run: exit 0, 0 findings; snapshot: exit 0 + timestamped dir under `/tmp/gm-snapshots` holding the three store files; restore --dry-run: exit 0, lists files, writes nothing (fixture-copy hashes unchanged); real-root: exit ∈ {0,1}, store hashes unchanged; lint 0 FAIL, collision 0 |
| DASH-041 | preflight `[[ -n "$CLAUDE_CONFIG_DIR" ]]` asserted in every claude invocation, e.g. `CLAUDE_CONFIG_DIR=/tmp/gm-spike-home claude plugin marketplace add /tmp/gm-spike-mkt` then `CLAUDE_CONFIG_DIR=/tmp/gm-spike-home claude plugin install scoped-test@gm-spike`; `find /tmp/gm-spike-home -name SKILL.md` | F-spike (/tmp, schema in §4) | a written verdict: GO/NO-GO + cache `find` listing as evidence + recommended mechanism + measured current context-tax (SKILL.md copy count, est. duplicated tokens); real-root stores untouched (shasum before == after); verdict recorded via `board.py edit DASH-041 --body` |
| DASH-044 | after the item lands: `grep -c "2026-06-11" skills/project-meta/proposals/global-meta.md` ≥1; verb table shows drift→audit, reconcile→emit-fix, settings→cut, track→deferred; `grep -ci "config-root" skills/meta-debug/SKILL.md` ≥1 (arbitration row phrased by capability, not the literal slug, to keep `trigger_collision_check` symmetric until DASH-039 lands the reciprocal row); `trigger_collision_check.py .` | live repo | all greps non-empty post-land; collision check 0 findings; validate green |
| DASH-040 | `cp -R skills/global-meta/examples/audit-fixture /tmp/gm-fixture-copy && python3 skills/global-meta/scripts/config_root_audit.py audit --config-home /tmp/gm-fixture-copy --home-dir /Users/HaoranWang --spec-marketplace test-mkt --emit-fix /tmp/fix.sh && /bin/bash -n /tmp/fix.sh && /bin/bash /tmp/fix.sh --apply && python3 skills/global-meta/scripts/config_root_audit.py audit --config-home /tmp/gm-fixture-copy --home-dir /Users/HaoranWang --spec-marketplace test-mkt` | `/tmp/gm-fixture-copy` (copy of committed F-audit) | emitted script: bash-3.2-clean, contains a snapshot call **before** the first mutation, refuses to run without `--apply`, never targets the real root by default; final re-audit: exit 0, 0 findings |
| DASH-042 | (not built this run) spike verdict + operator approval recorded in §9 | — | 🔴 gate satisfied before any build starts |

## §7 🔴 Checkpoints (halt-and-log)

1. **DASH-042 build start** — halt until spike GO **and** explicit operator approval.
2. **Any `claude plugin marketplace add/remove` aimed at the real config root** — forbidden; sandbox only. **Spike-verified caveat (2026-06-11):** `CLAUDE_CONFIG_DIR` does NOT isolate the shared plugin store — marketplace/install ops land in `~/.claude-shared/plugins/` regardless (registry round-trips; `known_marketplaces.json` touched). Treat every marketplace op as a real-store write: hash-verify the three stores after ANY spike-class work, and prefer pure-filesystem inspection over CLI installs where possible.
3. **Applying an emitted fix script to the real config root** — operator-run only this milestone.
4. **Readiness audit returns NO-GO or BLOCKER** — fix and re-audit (convergence loop, ≤3 re-audit rounds) before any wave starts.

## §8 Pre-decided defaults

- Workers: Sonnet, in git worktrees, one item each; Lead (this session) reviews + lands sequentially.
- Version bumps: DASH-039 → global-meta **1.1.0**; DASH-040 → **1.2.0**; DASH-043 already carries marketplace 2.0.2; DASH-044 → project-meta patch + meta-debug patch.
- `config_root_audit.py` exit codes: 0 clean · 1 findings · 2 error. Stdlib only. Findings print as ready-to-run `board.py inbox-add` lines (capture, not auto-write). **Exact capture-line contract** (the §6 assertion greps for the prefix `python3 skills/project-meta/scripts/board.py inbox-add --title `): `python3 skills/project-meta/scripts/board.py inbox-add --title <shlex-quoted '<code>: <one-line finding>'> --source config_root_audit` — one line per finding, `<code>` ∈ {F1..F4 classes or future codes}; the title is shell-escaped via `shlex.quote` because registry keys are untrusted input (review finding, PR #47).
- Snapshot ledger location: `~/.claude-shared/snapshots/<UTC-ts>/` — never inside a git repo, never auto-pruned.
- Spike verdict storage: board item body (DASH-041) + §9 of this plan; no new doc file.
- The audit treats `claude doctor` overlap as delegation: report "covered by doctor" instead of re-checking.

## §9 Audit provenance

- 2026-06-11 — **Round 1** (fresh-context auditor, Goal-readiness dimension): **NO-GO**.
  Blockers: F-audit fixtures absent/circular; DASH-040 §6 test target was an ellipsis.
  Majors: DASH-043 premise stale (PR #43 was already open; landed during the fix window);
  §9 unfilled; `agents/project-artifacts.md` missing. Minors: F-spike schema underspecified,
  DASH-044 pre-state note, sandbox fence not asserted in §6, post-merge rerun commands
  unlisted, capture-line format unpinned. Recorded in `.harness/audit-ledger.jsonl`.
- 2026-06-11 — **Fixes applied** (this revision): fixtures committed (`audit-fixture{,-clean}/`),
  manifest created, §§2/3/4/5/6/8 amended as listed above; DASH-043 marked done (PR #43 merged).
- 2026-06-11 — **Round 2** (fresh-context auditor): **GO** — 0 BLOCKER, 0 MAJOR, 2 MINOR
  (M1 snapshot placeholder path, M2 tier label) — both fixed in this revision. Gates green
  (validate PASS, lint 0 FAIL, collision 0). Convergence recorded in `.harness/audit-ledger.jsonl`; transaction closed.
- 2026-06-11 — **Renumber:** a parallel session landed code-graph as DASH-033 (PR #44,
  project-meta 1.14.0) while this plan was in flight; this milestone's items were renumbered
  DASH-033..038 → **DASH-039..044** during the merge (board re-added via `board.py`, roadmap rev 44+).
- 2026-06-11 — **DASH-041 spike verdict: GO.** Scoped sources work natively
  (`source: "./skills/<name>"` + `skills: ["./"]` materializes only the skill subtree).
  Measured tax: 256 SKILL.md copies across 33 cached version dirs (~31k redundant tokens).
  Compensating change required: broaden the project-meta resolver glob (cache root = skill root
  under scoped sources) and bake `PROJECT_META_DIR` at init. Safety lesson folded into §7.2.
  DASH-042 remains 🔴 — awaiting operator approval.
- 2026-06-11 — **PR #47 review round** (fresh adversarial reviewer): BLOCKER — capture-line
  shell injection via untrusted registry keys → fixed with `shlex.quote` (§8 contract amended).
  Non-blocking NB-1 (malformed store JSON must exit 2, not 1/silent) and NB-2 (`claude-shared`
  misdetected as a profile) fixed in the same round. Acceptance battery re-run green.
