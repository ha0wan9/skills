---
artifact_name: agentic-infra-v0.6-build-plan
instantiated_from: project-meta/templates/building-plan.md
source_reference: project-meta/references/cli-command-patterns.md
project_scope: this repo only
owner: shared-user-facing
review_policy: user review when goal or readiness changes
last_reviewed: 2026-06-12
readiness: floor
goal: "Project Board v0.6 milestone built and shipped: DASH-046/047/049/050/051/031 implemented per acceptance shapes, all validators green, released as one project-meta minor version"
---

# Agentic-Infra v0.6 Build Plan

Source milestone: `docs/backlog/roadmap.json` v0.6 "Agentic-infra hardening" (groomed 2026-06-12,
L2 co-review applied). Source proposal: `skills/project-meta/proposals/agentic-infra-bottlenecks-2026.md`.
Execution honors `references/execution-policy.md`; this plan is the falsifiable target only.
Critic panel (3 lenses, 2026-06-12): REVISE → all findings folded in below (§9).

## 1. Goal & non-goals

**Goal:** all six v0.6 items implemented per their (panel-hardened) acceptance shapes, the
repo validators green, shipped as project-meta **1.16.0** via the validated-edit → ship →
reload workflow.

**Non-goals (drift fence):** no DASH-048 (Lesson Registry) or DASH-052 (Elastic harness)
work; no v0.4 items; no new orchestration-engine features (AP-COORD-7); no mutation testing
(documented escalation only); no board store schema changes.

## 5. Build order

Line references below are **semantic anchors recorded at planning time — advisory**; every
worker re-reads its target file before editing and anchors on the named construct, never the
raw line number.

- **Phase 1 — parallel fleet (6 worktree workers, disjoint write-sets):**
  - **W1 / DASH-046 (M)** — `skills/project-meta/scripts/dispatch_ledger.py` v2 +
    `references/multi-agent-protocols.md`: (a) Mechanical Enforcement — new subcommands,
    record snippet; (b) Context Package — capsule schema cross-ref; (c) **update the
    "Designed but not yet shipped" PreToolUse paragraph** so it stays truthful once W4's
    destructive-command guard ships (distinguish the still-unshipped read-only-verb and
    pre-commit gates from the now-shipped guard) + `templates/hooks/README.md` Stop-hook
    step description only. The Stop hook already calls `dispatch_ledger.py gate` —
    **no hook-script edit**.
  - **W2 / DASH-047 (S)** — new `skills/project-meta/scripts/memory_staleness.py` +
    `scripts/repo_memory.py` wiring (validate leg: append staleness sub-check to the
    `problems` flow; writeback gate: advisory note only) + `recipes/validate.md` step-2
    entry + `recipes/audit.md` one-line staleness-lint mention (acceptance shape names
    both validate **and** audit).
  - **W3 / DASH-049 (S)** — new `skills/project-meta/scripts/session_receipt.py` +
    `templates/hooks/scripts/verify-before-stop.sh` new step (slot after the board-integrity
    step, before the audit-convergence step) + `templates/hooks/scripts/load-agents-md.sh`
    injection call (inside the `strict|standard` case arm) + `templates/hooks/README.md`
    new section + **`.gitignore` (sole owner)**: add `.harness/session-receipt.json`.
  - **W4 / DASH-051 (S)** — new `templates/hooks/scripts/pre-tool-guard.sh` (PreToolUse,
    matcher `Bash`) + new `templates/hooks/scripts/env-readiness-probe.sh` (second
    SessionStart block — **not** inside `load-agents-md.sh`) +
    `templates/hooks/settings.json.fragment` (two new blocks; board-guard block untouched)
    + `templates/hooks/README.md` new sections.
  - **W5 / DASH-050 (S)** — new `skills/project-meta/scripts/test_integrity_diff.py` +
    `scripts/ship_plugin.sh` wiring: in `cmd_validate`, advisory step **after the
    `cmd_check_version` call and before `info "validate: PASS"`**; in `cmd_land`, hard gate
    (strict profile only) **after the audit-convergence gate block and before the
    `cmd_check_version` call**.
  - **W6 / DASH-031 (S)** — ordered within the branch: (1) draft the trimmed
    `skills/project-meta/SKILL.md` frontmatter description (≤200 tokens at 4 chars/token)
    and confirm it contains all 5 anchor phrases; (2) replace `check_skill_metadata`'s
    16-phrase closed list in `scripts/validate_project_meta.py` with the 5-anchor list;
    (3) re-copy the new description **verbatim** into `.claude-plugin/marketplace.json`
    project-meta `description` (sync check requires it). **No version bump** (lead bumps
    once at ship).
- **Phase 2 — integration pair (after fleet merges):** one Worker+Reviewer dispatch:
  `AGENTS.md` Shared Harness CLIs inventory (+3 lines for the new scripts) + `SKILL.md`
  "When To Load References" routing bullets for staleness/receipt/integrity.
  **Body-only edits — the SKILL.md frontmatter description must not be touched** (it is
  verbatim-synced to marketplace.json by W6; any further description change must re-copy).
- **Phase 3 — gates + ship:** full-validator run happens **only here, after all merges**
  (mid-build runs would spuriously fail W6's paired trim+relax and Phase-2 routing); lead
  review, board moves to done, milestone flip, bump minor, single PR, fresh review, land.

**Write-set table (files with ≥2 writers, or singleton-but-sensitive):**

| File | Writers | Resolution |
|---|---|---|
| `templates/hooks/README.md` | W1, W3, W4 (distinct sections) | pairwise `git merge-tree` precheck; lead owns reconciliation |
| `.gitignore` | W3 only (declared) | no other worker may touch |
| `.claude-plugin/marketplace.json` | W6 only (description field) | lead bumps version at ship |
| `SKILL.md` | W6 (frontmatter desc) then Phase 2 (body only) | sequential by phase |
| all others | single writer | — |

**Landing sequence (land-queue not installed on this repo):** worker branches are
squash-merged **sequentially into the local main tree** by the lead — re-running
`git merge-tree` against *updated* HEAD before each merge, never against the stale fleet
base — then the integrated result ships as **one PR** via `ship_plugin.sh`. Six separate
PRs are not used.

## 6. Per-item verification matrix

**Preconditions:** rows marked *(post-Wn)* reference artifacts created by that worker and
are runnable only after its branch merges; the matrix is executed in full at Phase 3
against the integrated tree. `$T` = a temp fixture dir/repo created by the test run.
All script invocations are `python3 <full path from repo root>` unless shown otherwise.

| Item | Test target (exact command / assertion) | Data | Threshold |
|---|---|---|---|
| DASH-046 claim atomicity *(post-W1)* | `python3 skills/project-meta/scripts/dispatch_ledger.py --target-root $T claim --task T1 --worker w1`, then same with `--worker w2` | tmp dir fixture | 1st exits 0; 2nd exits 1 with "duplicate claim" |
| DASH-046 overlap gate *(post-W1)* | two `record --touch-set a.py,b.py` / `--touch-set b.py,c.py` rows, then `overlap` | tmp dir fixture | exit 1 + pairwise report naming both workers and `b.py` |
| DASH-046 capsule/checkpoint *(post-W1)* | `validate` on a `schema_version: 2` row missing capsule fields; then on a complete row | hand-written JSONL fixture rows | incomplete → exit 1 naming the missing field; complete → exit 0 |
| DASH-046 v1 back-compat *(post-W1)* | `validate` + `gate` against this repo's real `.harness/dispatch-log.jsonl` (v1 rows) | real ledger | exit 0 — legacy rows pass with worker/role/verdict only |
| DASH-046 budget ceiling *(post-W1)* | v2 row `budget_tokens: 100, spent_tokens: 150` → `validate` | fixture row | exceedance named in output (advisory), exit 0 at standard |
| DASH-047 lint *(post-W2)* | `python3 skills/project-meta/scripts/memory_staleness.py --target-root $T` where fixture AGENTS.md cites a deleted path | tmp git repo fixture | exit 1, output has `STALE` row naming the path; clean fixture → exit 0, rows all `OK`/`UNKNOWN` |
| DASH-047 validate wiring *(post-W2)* | `python3 skills/project-meta/scripts/repo_memory.py --target-root . validate` | this repo | exit 0 and output includes a staleness summary line |
| DASH-047 audit wiring *(post-W2)* | `grep -q memory_staleness skills/project-meta/recipes/validate.md skills/project-meta/recipes/audit.md` | this repo | exit 0 (both wired) |
| DASH-049 write+cap *(post-W3)* | `python3 skills/project-meta/scripts/session_receipt.py --target-root $T write --goal g --done d --next n`, then `inject` | tmp dir | receipt file exists; `inject \| wc -l` ≤ 30 |
| DASH-049 profile gate *(post-W3)* | `HARNESS_PROFILE=minimal … session_receipt.py --target-root $T inject` | tmp dir with receipt | empty output, exit 0 |
| DASH-049 hook syntax *(post-W3)* | `bash -n templates/hooks/scripts/verify-before-stop.sh && bash -n templates/hooks/scripts/load-agents-md.sh` | shipped scripts | exit 0 |
| DASH-050 detector *(post-W5)* | `python3 skills/project-meta/scripts/test_integrity_diff.py --repo $T --base HEAD~1` on a fixture commit that removes an assertion + adds a skip | generated tmp git repo | exit 1 listing both findings; no-test-change commit → exit 0 |
| DASH-050 wiring *(post-W5)* | `scripts/ship_plugin.sh validate` on the integrated v0.6 tree (project-meta IS a changed plugin there, so the step fires) | this repo, pre-PR | integrity step visible in output; exit 0 |
| DASH-051 guard blocks *(post-W4)* | `echo '{"tool_input":{"command":"rm -rf /"}}' \| HARNESS_PROFILE=strict bash templates/hooks/scripts/pre-tool-guard.sh` | inline JSON | exit 2 (block); `standard` → exit 0 + stderr warning; `minimal` → exit 0 silent |
| DASH-051 false positives *(post-W4)* | same harness with `rm file.txt`, `git reset --soft HEAD~1`, `grep DROP docs/x.md` | inline JSON | all exit 0, no warning |
| DASH-051 probe *(post-W4)* | `HARNESS_PROFILE=standard bash templates/hooks/scripts/env-readiness-probe.sh` in this repo; secret leg: fixture tree containing `aws_secret_access_key = "AKIA…"` in a tracked file → probe warns | this repo + tmp fixture | exit 0; warns iff a canonical command unresolvable; secret-shaped string produces a warning line |
| DASH-051 fragment wiring *(post-W4)* | `python3 -c "import json;j=json.load(open('skills/project-meta/templates/hooks/settings.json.fragment'));hooks=j['hooks'];assert any('pre-tool-guard' in str(b) for b in hooks.get('PreToolUse',[])) and any('env-readiness-probe' in str(b) for b in hooks.get('SessionStart',[]))"` (adjust key path to fragment's real shape) | shipped fragment | exit 0 — both blocks structurally wired, parse valid |
| DASH-031 ceiling *(post-W6)* | `python3 skills/project-meta/scripts/context_cost_estimate.py skills/project-meta --max-desc-tokens 200` | this repo | no `DESC>200` flag in output |
| DASH-031 validator *(post-W6)* | `python3 scripts/validate_project_meta.py` | this repo | exit 0 (incl. marketplace sync + relaxed 5-anchor metadata check) |
| Milestone gate *(Phase 3)* | `scripts/ship_plugin.sh validate && python3 skills/project-meta/scripts/board.py tx` | integrated tree | both exit 0 before PR |

## 8. Pre-decided defaults

- **Ledger v2 schema:** new fields `schema_version: 2`, `task` (claim key), `claimed_by`,
  `touch_set` (list), `capsule` (object: `goal`, `constraints`, `decisions`, `out_of_scope`),
  `budget_tokens`/`spent_tokens` (ints, optional), `checkpoint` (object: `completed`,
  `touched_files`, `open_decisions`). Validation of new required fields applies **only** to
  rows with `schema_version >= 2`; v1 rows keep the worker/role/verdict floor.
- **Receipt:** `.harness/session-receipt.json`, single file, overwritten per Stop,
  **git-ignored — same rationale as the already-ignored `.harness/dispatch-log.jsonl`:
  session-grained transient evidence, not durable state.** Board state is never duplicated
  into it — it carries a board *pointer* (item ids) only.
- **Profile ladder for all new payloads:** `minimal` = off, `standard` = warn/advisory,
  `strict` = block. Guard exit code on block: 2 (PreToolUse deny convention).
- **Guard patterns (closed list v1):** `rm -rf` on `/`, `~`, `.`, or an unquoted variable;
  `git reset --hard`; `git clean -fdx`; `DROP TABLE|DATABASE`, `TRUNCATE TABLE` in non-doc
  commands. Word-boundary regex, tested against this repo's own scripts for false positives.
- **check_skill_metadata relaxed list (5 anchors):** `/project-meta`, `AGENTS.md`,
  `USER.md`, `multi-agent`, `mirror`. W6 drafts the trimmed wording first, confirms the
  anchors, then swaps the validator list — that order, on one branch.
- **Branches:** `v06/dash-<nnn>` per worker, sequential local squash-merge by the lead
  (merge-tree re-check against updated HEAD each time), one PR for the integrated result.
  No version bumps on branches; lead bumps `project-meta minor` once at ship (→ 1.16.0).
- **Worker tier:** Sonnet (fleet); escalate one agent only on demonstrated shortfall.
- **Review:** lead reviews every diff + validators; fresh L1 re-review for W1 (canon
  reference change) and W6 (MUST-rule-adjacent validator change); ship-time fresh PR review
  per repo workflow (gate 3).
- **New scripts ship in** `skills/project-meta/scripts/` (plugin-shipped), except
  hook payloads in `templates/hooks/scripts/`. `test_integrity_diff.py` is plugin-shipped
  (target repos reuse it); its ship_plugin.sh wiring is dev-repo-only.

## 9. Audit provenance

- 2026-06-12 — critic panel (falsifiability / canon-consistency / execution-risk lenses,
  3× Sonnet, clean context): 3× REVISE, 0 NO-GO. All BLOCKER/MAJOR findings folded in:
  forward-reference preconditions on the matrix, full invocations, W1 truthfulness update
  to the "Designed but not yet shipped" paragraph, fragment-wiring + secret-leg matrix
  rows, audit-verb wiring for DASH-047, Phase-2 body-only constraint, `.gitignore`
  ownership, semantic anchors for W5, W6 intra-branch ordering, sequential-landing rule.
