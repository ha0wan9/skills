# Marketplace Skills Audit — 2026-06-06

Full-repo audit of all 8 skills, run in ultracode mode (parallel multi-agent
fan-out → independent verification → synthesis), followed by remediation.

- **Method:** deterministic floor (the repo's own validators/linters) → 9 parallel
  audit agents (8 per-skill + 1 cross-cutting) → independent verification of every
  load-bearing claim → remediation via 8 per-skill editing agents + hand-owned
  manifest/docs/tooling fixes → re-validation + script smoke tests.
- **Rubric:** `skills/project-meta/references/writing-skills.md`,
  `references/anti-patterns.md` (AP-XXX-N catalog), `recipes/audit.md`.

## Deterministic floor (post-fix)

| Check | Result |
|---|---|
| `scripts/validate_project_meta.py` | 15 / 15 PASS |
| `ship_plugin.sh validate` (manifest + version gate + project-meta) | PASS |
| `skill_architecture_lint.py` (all 8) | 0 FAIL, 0 WARN |
| `cross_skill_redundancy.py` | 0 candidates |
| `trigger_collision_check.py` | 0 unmitigated collisions |
| `context_cost_estimate.py` | 0 over the always-on ceiling* |
| `validate_target_harness.py` | 7 PASS / 0 WARN / 0 FAIL |
| All SKILL.md ≤ 250 lines | ✅ (max 249) |

\* project-meta's description is intentionally over the soft 200-token ceiling: its
content is hard-mandated by `validate_project_meta.py::check_skill_metadata` (which
requires specific phrases such as `existing agent-facing documentation framework`,
`user-facing documentation delivery`, `canonical templates`, the full `/project-meta`
verb list). The hard contract wins; this is a documented, accepted exception.

## Findings & remediation

### 🔴 BLOCKERs (all fixed)

1. **openclaw-devops wrote runtime state into its own install dir** (`AP-SKL-6`).
   `scripts/openclaw_devops.py` hardcoded `STATE_DIR = SKILL_ROOT/"state"` → a
   marketplace update would wipe the rollback anchor; a shared install bled state
   across hosts. **Fixed:** resolver `--state-dir` › `$OPENCLAW_DEVOPS_STATE_DIR` ›
   `<nearest .git>/.harness/openclaw-devops/` (mirrors meta-debug's pattern); added
   `--state-dir` flag and a `.gitignore` for `state/`.

2. **calendar-crud-workflow was a "prompt fragment"** (`AP-SKL-1` + `AP-SKL-2`).
   Whole CRUD procedure inline; destructive batch ops ungated. **Fixed:** procedure
   moved to `references/crud-procedure.md`; SKILL.md trimmed 192→84 lines; added
   `## Core Rules` with MUST gates (read-before-write, batch-confirm, no silent
   color fallback, no uninvited video links, dedupe, recurring-series scope), plus
   Trigger Decision / Bootstrap Order / Skill Arbitration / Output Footer.

3. **profile-creator was a "prompt fragment"** (`AP-SKL-1/2/5`). **Fixed:** added
   `scripts/create_profile.py` (argparse, name validation, prereq checks,
   remediation messages, `--dry-run`); launcher bodies → `templates/`; procedure →
   `references/create-profile.md`; `## Core Rules` MUST block (incl. never run
   `claude plugin marketplace add/update` from a new profile); example added.

### 🟠 MAJORs (fixed)

- **3 SKILL.md had no `metadata:` block** (meta-debug, openclaw-devops,
  sketch-asset-generator) → added (version + compat + published).
- **Version drift** (SKILL.md vs manifest) → all reconciled and bumped to **1.2.0**;
  added a SKILL↔manifest version check to `ship_plugin.sh`'s `_validate_marketplace`.
- **Description drift** (meta-debug, openclaw-devops) → manifest re-synced verbatim
  to the canonical SKILL.md descriptions.
- **AGENTS.md routing omitted meta-debug & openclaw-devops** → added to intro + table.
- **README compat table omitted sketch-asset-generator and over-claimed OpenClaw ✅**
  for calendar/deep-survey/dl-research → sketch row added; unbacked OpenClaw set ❌.
- **Unbacked `openclaw` compat** (`AP-VAL-1`) on calendar-crud-workflow,
  deep-survey-bfs, dl-research → `openclaw` dropped from compat (honest over fabricated).
- **openclaw-devops "phantom peer"** — Skill Arbitration referenced a non-existent
  `openclaw-ops-audit` → removed.
- **meta-debug missing `## Shared Harness Delegation`** → added (resolver + thin floor)
  so lesson-promotion no longer silently no-ops when project-meta is absent.
- **Missing Trigger Decision / Bootstrap Order** sections → added across the skills
  that lacked them.
- **project-meta hub:** Core-Rules tier-selector restatement collapsed to a one-line
  MUST pointer; `## Output Footer` added; skill-audit routing now also points at
  `skill-critics.md`; heuristics marked `Default:`; `examples/sample-init/` added.
- **examples/ gaps** → added for dl-research, project-meta, sketch READMEs, profile-creator.
- **deep-survey-bfs scripts** `claims_validate.py` / `coverage_check.py` migrated to
  argparse (`--help` now exits 0).

### 🐛 Tooling bug fixed

`determinism_gap_scan.py` matched hooks via `**/hooks/*.sh` but hook scripts live at
`**/hooks/scripts/*.sh`, so it false-flagged `phase_lock_check.py` (which
`verify-before-stop.sh` does invoke). Added `**/hooks/scripts/*.sh` to the patterns.

## Accepted / deferred (advisory only)

- `determinism_gap_scan.py` still lists several "rule names a script, no enforcing
  hook" entries (e.g. `create_profile.py`, `validate_asset_pack.py`,
  `validate_ledger.py`). These are **on-demand, agent/user-invoked tools** expressed
  as MUST-prose gates — not Stop/PostToolUse-hook-enforceable — so the advisory scan
  flags them by design. Left as MUST gates, not hooks.
- project-meta always-on description over the 200-token soft ceiling (see note above).

## Candidate new anti-patterns (for project-meta to assign IDs)

- Trigger Decision section absent (distinct from AP-SKL-1).
- Bootstrap Order section absent.
- Phantom peer reference in Skill Arbitration (peer doesn't exist).
- Critic glob/path mismatch → false-positive gaps (the determinism_gap_scan bug class).
- Unrouted design artifacts in skill install dir (`project-meta/proposals/`).
