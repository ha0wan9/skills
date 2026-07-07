---
template_name: hooks
description: "Seed for Claude Code and Codex hooks: SessionStart bootstrap, PostToolUse formatting, Stop verification. Profile-aware via HARNESS_PROFILE."
source_reference: references/harness-engineering.md
intended_project_path: .claude/hooks/ + .claude/settings.json, or ~/.codex/hooks.json
owner: agent-facing
secure_derivation: required
review_policy: user-review-when-hooks-change-behavior
---

# Hooks Template Pack

Three-hook starter pack for Claude Code project hooks and Codex global
hooks. Hooks are bash for portability — no Python venv, no npm dependency.
Each hook is profile-aware: `HARNESS_PROFILE` toggles between `minimal` /
`standard` / `strict`. Optional elastic bounds (`HARNESS_PROFILE_FLOOR` /
`HARNESS_PROFILE_CEILING`) may derive `.harness/effective-profile` for elastic
advisory legs only; invariant core gates always read `HARNESS_PROFILE` directly.

## Layout

```
.claude/
  settings.json              # merged from settings.json.fragment
  hooks/
    load-agents-md.sh        # SessionStart
    format-on-edit.sh        # PostToolUse on Edit/Write/MultiEdit
    provenance-on-edit.sh    # PostToolUse on Edit/Write/MultiEdit (D5; agents/*.md)
    verify-before-stop.sh    # Stop
    issue-tracker-reminder.sh # UserPromptSubmit (optional; issue-tracker capability)

~/.codex/
  hooks.json                  # merged by install_codex_hooks.py
  hooks/project-meta/
    load-agents-md.sh
    format-on-edit.sh
    verify-before-stop.sh
```

## Installation

`/project-meta init --hooks` installs hooks for the primary host.

For Claude Code, it performs:

1. Copy `templates/hooks/scripts/*.sh` to `<target>/.claude/hooks/`,
   preserving execute bits.
2. Merge `templates/hooks/settings.json.fragment` into
   `<target>/.claude/settings.json`. If `settings.json` does not exist,
   create it; if hooks are already configured, merge keys instead of
   overwriting.
3. Set `HARNESS_PROFILE=standard` as the default; the user can change
   this in `settings.json` per project.
4. Update `agents/<topical>.md` with a note that hooks are active and
   what each enforces.

For Codex, install globally with:

```bash
python3 ~/.codex/skills/project-meta/scripts/install_codex_hooks.py
```

The installer copies the scripts into `~/.codex/hooks/project-meta/`,
merges `SessionStart`, `PostToolUse`, and `Stop` entries into
`~/.codex/hooks.json`, injects `PROJECT_META_DIR` so hooks resolve the
Codex-installed skill, and preserves existing hooks. It does not pre-seed
`config.toml` `[hooks.state]` trust hashes; Codex may ask the user to trust
the new commands on first run. Use `--dry-run` to preview, `--profile` to
choose `minimal` / `standard` / `strict`, and `--codex-home` for non-default
Codex homes.

## What Each Hook Does

### `load-agents-md.sh` — SessionStart

Surfaces the canonical project-memory file's name (and topical-routing
hint) at session start so the agent has the routing context without
being prompted. Output is short (≤30 lines) to preserve context budget.

- `minimal`: prints just the canonical filename
- `standard`: prints filename + reads-before-substantive-work reminder + topical-routing hint if AGENTS.md uses the loader pattern
- `strict`: adds an explicit "MUST cite the rule justifying any harness edit" reminder

### `format-on-edit.sh` — PostToolUse on Edit / Write / MultiEdit

Reformats files the agent just touched, dispatching by extension. Missing
formatters are skipped silently. Built-in support for: ruff/black (py),
prettier (ts/tsx/js/jsx/json), rustfmt (rs), gofmt (go), shfmt (sh).
Markdown is intentionally off by default — opinions on `.md` formatting
vary too much.

- `minimal`: hook disabled; exits 0 immediately
- `standard`: runs formatter; exit code ignored (best-effort)
- `strict`: exits non-zero if the formatter changed the file (forces
  re-staging)

The hook reads the edited path from `$CLAUDE_TOOL_USE_PATH`, falling back
to `$TOOL_USE_PATH` and `$EDITED_PATH` for compatibility with other host
conventions.

### `provenance-on-edit.sh` — PostToolUse on Edit / Write / MultiEdit (D5)

Advisory provenance pass on a freshly-edited `agents/*.md` topical file (the
artifacts that carry provenance frontmatter); a no-op for any other path.
Resolves `project-meta`'s `provenance.py` the same way the Stop hook resolves
its scripts.

- **new (untracked) file** → `provenance.py auto-stamp` — **never blocks** a
  first draft: it refreshes `last_reviewed` when lineage is present and warns
  (without failing) when `instantiated_from`/`source_reference` are missing.
  The hard provenance check for new files lives at `deliver`/`validate`.
- **pre-existing (tracked) file** → `provenance.py check` — a tracked artifact
  must keep its provenance: advisory at `standard`, blocking at `strict`.
- `minimal`: disabled; exits 0 immediately.

### `verify-before-stop.sh` — Stop

Responsibilities (each self-skips when its artifact is absent):

1. **Phase-lock check** when `.harness/phase-state.json` exists. Invokes
   `phase_lock_check.py` from the installed `project-meta` skill (path
   resolves via `$PROJECT_META_DIR`, `~/.codex/skills/project-meta/`, or
   `~/.claude/skills/project-meta/`).
2. **Project verifier** when `.harness/verify.sh` exists. The user
   defines what verification means for the project (test runner,
   linter, type-checker, integration suite — whatever is fast enough
   for a per-turn check).
3. **Memory write-back gate** via `repo_memory.py writeback` (same
   resolved `project-meta` path). Flags a pending write-back decision
   when the turn changed substantive files but no memory file was
   updated and no `.harness/writeback-ack` marker exists. This is the
   write leg of the Memory Contract (`references/repo-memory-crud.md`).
4. **Mandatory-dispatch gate** via `dispatch_ledger.py gate` (same
   resolved path). Flags the AP-COORD-1 pattern — the turn edited
   **≥2 harness files** without an acknowledged dispatch. Self-skips
   when <2 harness files changed or `.harness/dispatch-ack` exists
   (one-shot). The enforcement leg of the Task Dispatch paradigm
   (`references/multi-agent-protocols.md#mandatory-subagent-dispatch`).
   For v2 ledger rows (`schema_version >= 2`), `dispatch_ledger.py
   validate` additionally checks capsule completeness (`goal`,
   `constraints`, `decisions`, `out_of_scope`) and checkpoint
   completeness (`completed`, `touched_files`, `open_decisions`), and
   reports `budget_tokens`/`spent_tokens` exceedance as advisory text.
5. **Project Board store integrity** via `board.py tx` (same resolved
   path) when `docs/backlog/items.jsonl` exists — item schema,
   duplicate ids, roadmap references, `items_sha256` freshness — so a
   hand-edited or stale store is caught before the turn ends. The
   Stop-side enforcement leg of the board CRUD contract
   (`references/project-board-crud.md`); `board-guard.sh` is the
   PreToolUse leg.
6. **Audit convergence gate** via `audit_ledger.py gate` (same resolved
   path) when `.harness/audit-ledger.jsonl` exists. Final audits are
   multi-round (`recipes/audit.md`, Convergence loop): an open
   release-gated audit transaction whose last round is still red
   (BLOCKER/MAJOR > 0, or the Round-4 cap) flags the turn. Per-round
   acks (`record --ack`) cover fix-in-progress turns; at the cap only
   a persistent operator override row (`record --final
   --accept-residuals`) passes. The ledger is branch-scoped and a red
   round auto-expires after 72h, so a stale transaction never blocks
   unrelated work. Self-skips when no ledger exists — the gate
   enforces that a *claimed* audit converges; it never forces audits.
7. **Lesson registry gate (D6)** via `lesson_registry.py` (elastic leg) —
   see the lesson_registry section below.
8. **Last-turn-meta gate (D5)** via `last_turn_meta.py check` (same resolved
   path). The machine counterpart to the prose Output Footer: an editing recipe
   must leave a valid `.harness/last-turn-meta.json` (keys `verb`, `review_tier`,
   `read_pattern`, `files_written`, `files_read`, `memory_updated`,
   `delivery_shown`). Fires only when the turn changed **≥1 harness file** (it
   reuses the dispatch gate's harness-file definition), so read-only verbs are a
   no-op. File-derived — it never greps the transcript. The write side is the
   `last_turn_meta.py write` call editing recipes make at completion (SKILL.md
   Output Footer).

- `minimal`: invariant/core checks are disabled on raw `HARNESS_PROFILE=minimal`
  (the write-back and dispatch gates also self-disable there); elastic D6 lesson
  validation may still run when `.harness/effective-profile` is `standard` or `strict`.
- `standard`: runs all checks; warns on failure but exits 0 (advisory)
- `strict`: exits non-zero on failure (blocks the agent's turn end)

If none of the artifacts are present (no phase-state, no verifier, not a
git repo / nothing changed / <2 harness files), the hook is a no-op — the
harness can ship it without forcing every repo to install phase-locks,
define a verifier, or adopt the write-back / dispatch gates.

### session_receipt — Stop + SessionStart payload

`session_receipt.py` (in `skills/project-meta/scripts/`) is the backing CLI for
a lightweight per-session context capsule stored at `.harness/session-receipt.json`.
It is **git-ignored** (same rationale as `.harness/dispatch-log.jsonl`: session-grained
transient evidence, not durable state) and is **never** used to duplicate board state —
it carries a board *pointer* (item ids) only.

**Two subcommands:**

- `write` — write or overwrite the receipt. Accepts `--goal`, `--done`, `--blocked`,
  `--next`, `--memo` (all optional strings) and `--items` (comma-separated board item ids).
  Also accepts `--auto` for the Stop-hook auto-write mode (see below).
- `inject` — print the latest receipt as a compact human block, hard-capped at **30 lines**
  (truncated with `...truncated` if needed). Prints nothing and exits 0 when
  `HARNESS_PROFILE=minimal` or when no receipt file exists.

**Auto-write vs semantic write:**

The Stop hook (`verify-before-stop.sh`, step 5.5) calls `write --auto`, which records
only the UTC timestamp, current git branch, and changed-file count. Auto mode is a
**no-op** when an existing receipt is younger than 24 hours *and* contains at least one
semantic field (`goal`, `done`, `blocked`, `next`, or `memo`) — ensuring that a richer
receipt written earlier in the turn by the agent is preserved, not clobbered.

The agent (or another hook/script) can write a semantic receipt at any point during a
turn by calling `write` with named fields. That receipt will survive the Stop-hook auto
pass for up to 24 hours.

**Profile gating:**

- `minimal`: `inject` prints nothing and exits 0. The Stop-hook auto-write step is still
  executed (it only writes to the local `.harness/` transient store), but `inject` in the
  SessionStart hook suppresses output entirely.
- `standard` / `strict`: `inject` prints the receipt block on SessionStart.

The `.harness/session-receipt.json` gitignore line lives in the repo's `.gitignore`.
Add it with:

```
.harness/session-receipt.json
```

### lesson_registry — Stop + SessionStart (D6)

`lesson_registry.py` (in `skills/project-meta/scripts/`) is the backing CLI for a durable
per-repo learned-policy store at `.harness/lessons.jsonl`. Unlike session-grained transient
artifacts (receipt, dispatch log), this file is **git-TRACKED** — it is durable learned policy
that survives session boundaries and is intended to be code-reviewed alongside code.

**Store:** `.harness/lessons.jsonl` — one JSON row per lesson. Single writer; full-file
atomic rewrite on each mutation (board.py-style O_EXCL lock + temp-file rename).

**Row schema:**
```
{id, statement, status, target, target_path, applies_below,
 helpful_count, harmful_count, notes, created_at, updated_at,
 source_session, last_validated}
```

- `target`: `null | "memory" | "hook" | "linter"` — where the lesson is wired
- `target_path`: `null | str` — repo-relative path to the file that implements/enforces the lesson
- `applies_below`: `null | "haiku" | "sonnet" | "opus" | "fable"` — tier filter; a lesson with
  `applies_below=sonnet` is shown only when the session tier is BELOW sonnet (tier order:
  haiku < sonnet < opus < fable). `null` = always show.

**Status ladder (legal transitions only):**

```
candidate → recorded → promoted → enforced
any → retired
enforced → promoted   (demotion; requires --note)
promoted → recorded   (demotion; requires --note)
```

- `promoted` and `enforced` REQUIRE `target` AND `target_path` to be set (on transition or supplied now).
- Upward skips (e.g. `candidate → enforced`) are illegal — exit 1 with a clear message.
- Demotions are legal but require `--note` to record the cause.

**Subcommands (all accept `--target-root`, default cwd):**

- `add --statement S [--source-session X] [--applies-below T]` — allocates LES-NNN
  (`candidate`, counts 0). Prints the id.
- `status <id> <to> [--target T] [--target-path P] [--note N]` — enforces the legal ladder.
- `outcome <id> --helpful | --harmful [--note N]` — increments the ACE-style effectiveness count.
- `validate` — hard gate: checks row structure, legal status fields, required fields for
  `promoted`/`enforced`, and whether `target_path` resolves in the repo tree. Warns (exit 0)
  on `applies_below` + universal-keyword mismatch; exits 1 on hard errors.
- `watermark` — advisory visibility: candidate count + stale targets. **Always exits 0.**
  Hook legs call this for informational output only.
- `inject [--model-tier T]` — SessionStart reminder: lists unprocessed candidates + stale
  promoted/enforced lessons, hard-capped at **20 lines**. Filtered by `applies_below` if
  `--model-tier` is given. Prints nothing + exits 0 when `HARNESS_PROFILE=minimal` or store
  absent/empty.
- `effectiveness` — print helpful/harmful table per lesson.
- `trim-candidates [--apply]` — identify zero-value or stale-target promoted/enforced lessons;
  with `--apply`, write board inbox captures for operator review. Does NOT hard-delete.
- `promote-draft <id>` — run `trigger_collision_check.py` + `cross_skill_redundancy.py` over
  the statement (degrade gracefully if not resolvable), then print a board inbox draft for
  operator approval. Does not auto-promote.

**validate vs watermark — the split:**

| Subcommand | Purpose | Exit on error | Called by |
|---|---|---|---|
| `validate` | **Hard gate** — structural + path resolution correctness | exit 1 | Stop hook (D6, step 7) |
| `watermark` | **Visibility** — candidate count + stale targets | exit 0 always | Stop hook (advisory) |

`validate` is the enforcement leg. `watermark` is the observation leg. They are separate
subcommands so a stale target that is merely advisory (not yet classified) doesn't wedge a
turn — but once a lesson is `promoted` or `enforced`, its `target_path` resolving is a hard
requirement.

**Fail directions:**

- Direct CLI invocation → **fail CLOSED** (exit 1 on bad input, bad transition, missing fields).
- Hook legs (`watermark`, `inject`) → **fail OPEN** (corrupt/missing store → warn to stderr + exit 0;
  never wedge a turn).

**Profile gating:**

- `minimal`: `inject` prints nothing and exits 0. When elastic profile derivation is enabled,
  SessionStart passes the derived effective profile into `inject`, and the Stop hook gates only
  the D6 lesson step on `.harness/effective-profile`; invariant core checks still use raw
  `HARNESS_PROFILE`.
- `standard`: `validate` failure emits a warning but exits 0 (advisory).
- `strict`: `validate` failure exits non-zero (blocks the turn end).

**Hook wiring:**

- **Stop** (`verify-before-stop.sh`, step 7, delimited `# --- D6: lesson registry ---`):
  When `.harness/lessons.jsonl` exists, resolve `lesson_registry.py` via `resolve_project_meta`,
  run `validate` (the hard gate, routed through `advisory_exit`), then run `watermark` (advisory
  output to stderr). Self-skips when the store is absent.
- **SessionStart** (`load-agents-md.sh`, delimited `# --- D6: lesson inject ---`):
  After the session receipt inject, resolve `lesson_registry.py` and run `inject` (passes
  `--model-tier` when `$CLAUDE_MODEL` is discoverable from the environment). Self-gates (prints
  nothing when store absent or `minimal`).

**git-TRACKED rationale:** unlike `.harness/session-receipt.json` and `.harness/dispatch-log.jsonl`
(session-grained transient evidence), `lessons.jsonl` records durable operator-approved policy.
It belongs in version history so the team can audit when lessons were promoted, who approved them,
and what the current enforcement state is. Add it to `.gitignore` only if you intentionally want
lessons to be ephemeral (not recommended).

### derive_profile — Elastic Advisory Profile (D7)

`derive_profile.py` (in `skills/project-meta/scripts/`) derives an **effective** profile
for elastic advisory hook legs. It is opt-in and bounded:

- With neither `HARNESS_PROFILE_FLOOR` nor `HARNESS_PROFILE_CEILING` configured, it prints
  the configured `HARNESS_PROFILE` unchanged. `load-agents-md.sh` deletes any stale
  `.harness/effective-profile` in this static mode.
- With either bound configured, SessionStart runs `derive_profile.py --root .` and writes
  `.harness/effective-profile` when the result is `minimal`, `standard`, or `strict`.
- `HARNESS_PROFILE_FLOOR > HARNESS_PROFILE_CEILING` fails static: the script emits the
  configured profile and a stderr error.

Inputs are external evidence only:

- model tier from `--model-id`, `$CLAUDE_MODEL`, or `$ANTHROPIC_MODEL` (unknown → static unless
  other evidence escalates);
- `.harness/risk-context.json` from `risk_score.py --write-context`;
- `.harness/dispatch-log.jsonl` verdict history;
- `.harness/lessons.jsonl` helpful/harmful counts.

Derivation rules:

- scale **up** one step, bounded by ceiling, when risk band is `spike-first` or the last
  ten dispatch records have a BLOCKER rate ≥20%;
- scale **down** one step, bounded by floor, only for `opus`/`fable` tier with at least ten
  dispatch records and zero BLOCKERs in the last ten, and no harmful lesson-effectiveness signal;
- unreadable or absent inputs fail static, with a warning.

Elastic legs resolve `cat .harness/effective-profile 2>/dev/null || $HARNESS_PROFILE`. Current
elastic legs are SessionStart verbosity (`load-agents-md.sh`, including receipt and lesson
inject) and the D6 lesson-registry Stop step.

**Invariant core exclusion:** these gates deliberately do **not** read
`.harness/effective-profile`: `pre-tool-guard.sh` destructive-command guard,
`board-guard.sh`, `verify-before-stop.sh` steps 4–6 (dispatch gate, board `tx`,
audit convergence), and the `ship_plugin.sh land` / test-integrity gates. They read
`HARNESS_PROFILE` directly so elasticity cannot weaken blast-radius or ship blockers.

The derived state is transient and git-ignored:

```gitignore
.harness/effective-profile
```

### `issue-tracker-reminder.sh` — UserPromptSubmit (optional)

Ships **only** with the `issue-tracker` capability (`/project-meta init
--issue-tracker <tracker>` or `/project-meta settings`), not the default
three-hook pack. When the user's prompt has feature-proposal shape, it reminds
the agent to run the Track Loop in `agents/issue-tracking.md` (check the tracker
for an existing ticket → write progress back → open one if missing).

**Advisory only.** A shell hook has no MCP access, so it cannot query or write
the tracker — it only reminds, and never blocks the turn. Self-skips when
`agents/issue-tracking.md` is absent or the prompt has no feature-proposal shape.
Tracker specifics live in that doc, not in the hook. See
`references/issue-tracking-integration.md`.

- `minimal`: disabled (exit 0)
- `standard`: advisory reminder on a keyword match
- `strict`: stronger MUST-phrased reminder (still non-blocking — a hook cannot
  verify tracker state, so it must not fail the turn)

Wire it under `UserPromptSubmit` in `settings.json` (the install step merges
this; it is not in `settings.json.fragment` because it is opt-in):

```json
"UserPromptSubmit": [
  {
    "matcher": "*",
    "hooks": [
      { "type": "command", "command": "bash .claude/hooks/issue-tracker-reminder.sh" }
    ]
  }
]
```

### `capture-out-of-scope.sh` — SessionEnd (optional, Project Board DASH-02)

Autonomous out-of-scope capture for the **Project Board** — **dry-run first**. On session
end it records a *candidate* capture so out-of-scope features/bugs are not lost. Opt-in: not
in `settings.json.fragment`.

**Dry-run is the only shipped mode** (`BOARD_CAPTURE_MODE=dryrun`, default): it appends a
marker to `docs/backlog/.capture-dryrun.log` and **never** calls a model or writes the store
(`items.jsonl` / `roadmap.json` / `inbox.jsonl`). `BOARD_CAPTURE_MODE=append` is a documented
**not-yet-implemented** opt-in that would classify via `claude -p --model sonnet` and atomically
append a `fuzzy` row to `inbox.jsonl` only — gated on a false-positive/approval story (see
`docs/backlog/project-board-system.md` Open questions). Promote captured items with
`board.py promote` → `refine` (DASH-23). Capture is append-only and multi-instance-safe
(DASH-24); all mutation of existing rows happens later at the single-writer refine gate.

- `minimal`: disabled (exit 0)
- `standard` / `strict`: dry-run logging (append mode stays opt-in regardless of profile)

Always exits 0 — a capture hook must never fail a session. Wire under `SessionEnd`:

```json
"SessionEnd": [
  {
    "matcher": "*",
    "hooks": [
      { "type": "command", "command": "bash .claude/hooks/capture-out-of-scope.sh" }
    ]
  }
]
```

### `pre-tool-guard.sh` — PreToolUse on Bash (DASH-051)

Intercepts shell commands before execution and blocks or warns on patterns that can
irreversibly destroy repo or system data. Fires only on the `Bash` tool (matcher
`Bash`); it does not parse file paths from Edit/Write events — that is `board-guard.sh`'s
domain.

**Closed pattern list v1** (word-boundary, tested against this repo's own scripts for
false positives):

| Pattern | What it catches |
|---|---|
| `rm -rf` / `-fr` / `-r -f` on `/`, `~`, `.`, or `$var` | Recursive force-remove of root, home, cwd, or an unquoted variable expansion |
| `git reset --hard` | Discards all uncommitted changes |
| `git clean` with `-f` and `-d` or `-x` combined | Permanently removes untracked files / ignored files |
| `DROP TABLE` / `DROP DATABASE` / `TRUNCATE TABLE` (case-insensitive) | Destructive SQL in non-doc commands |

**False-positive policy** — the following are explicitly allowed (exit 0, no warning):

- `rm file.txt` — no recursive flag
- `rm -rf /tmp/something` — concrete absolute subpath under `/tmp`
- `git reset --soft HEAD~1` — not `--hard`
- `grep DROP docs/x.md` — grep/cat/echo/head/tail commands are excluded from the SQL check

**Profile ladder:**

- `minimal`: silent pass-through; exit 0 always. No check runs.
- `standard`: emits a warning to stderr; exit 0 (advisory, never blocks the turn).
- `strict`: emits a message to stderr; exit 2 (blocks the tool call — PreToolUse deny
  convention).

Fails open — any payload it cannot parse yields exit 0. It never wedges the session.

### `dispatch-tier-guard.sh` — PreToolUse on Task|Agent

Advisory dispatch-tier guard. Fires on the `Agent` tool (`Task` is the historical
alias — a dead regex alternative, harmless, covers older runtimes) and surfaces
silent session-model inheritance at dispatch time, per
[`docs/plans/model-tier-routing-build-plan.md`](../../../../docs/plans/model-tier-routing-build-plan.md)
§2 decision #4.

**Branches (first match wins; all exit 0):**

| # | Condition | Result |
|---|---|---|
| 1 | `model` present, haiku/sonnet-class (substring match) | silent |
| 2 | `model` present, opus-class | one-line notice — escalation-tier dispatch (sanctioned ≤2/run) |
| 3 | `model` present, fable/conductor-class | one-line notice — conductor-tier dispatch (≤1 unblock call/run) |
| 4 | `model` absent, `subagent_type` ∈ {general-purpose, claude} or absent/empty | WARN — dispatch inherits the session model |
| 5 | `model` absent, any other `subagent_type` (Explore/Plan/custom/plugin) | short notice — the type likely pins its own model in frontmatter |

A present-but-non-string `model`, or a non-string `subagent_type`, is treated as
custom/unknown and routed down the same notice/WARN paths above (never a crash).
An unrecognized non-empty model string (no haiku/sonnet/opus/fable/conductor
substring) gets its own one-line "unrecognized model tier" notice.

**Advisory-only rationale (no deny path in v1):** the PreToolUse payload for
`Agent`/`Task` is `{prompt, description, subagent_type, model?}` only — it cannot
see the agent-definition frontmatter `model:` field or the session-default
resolution chain the tool falls back to when `model` is omitted. A hard deny would
false-positive on legitimate flows, including the built-in `Explore`/`Plan` agent
types, which may resolve a model internally without ever surfacing it here. A
strict deny is a possible v2, but only behind evidence that `tool_input.model` is
a reliable signal (tracked as a backlog item, not built).

**Coverage gap — Workflow-internal fan-out is invisible:** `agent()` calls made
*inside* a Workflow script do not pass through the PreToolUse `Agent`/`Task`
matcher — only the top-level `Workflow` tool call is hook-visible. This hook
therefore covers direct Agent-tool dispatch only; the scripted-engine path is
governed by the orchestration contract's per-task tier table and `budget_hint`
tier-mix, not by this hook (see `skills/orchestration`).

The hook is **stateless** — it never queries `dispatch_ledger.py`; the "≤2/run"
and "≤1/run" figures in the notice text are contract-reviewed conventions, not
counts this hook tracks.

- `minimal`: silent pass-through; exit 0 always. No check runs.
- `standard` / `strict`: emits the matched branch's message to stderr; exit 0
  always (advisory at every profile — there is no block path in v1).

Fails open — any payload it cannot parse yields exit 0. It never wedges the session.

### `env-readiness-probe.sh` — SessionStart (DASH-051)

Runs at session start and reports two classes of environment problems. **Always exits 0**
— a SessionStart hook must never block.

**(a) Command-resolvability leg:** when `.harness/verify.sh`, a `Makefile`, `package.json`,
`pyproject.toml`/`setup.py`, `Cargo.toml`, or `go.mod` is present at the repo root, the
implied canonical toolchain entrypoints (`make`, `node`, `python3`, `cargo`, `go`, etc.)
are checked for resolvability via `command -v`. Unresolvable tools are reported with a
warning. Heuristics are simple and conservative — a missing optional tool (e.g. yarn when
only npm is installed) is the expected false-positive trade-off.

**(b) Secret leg:** scans TRACKED files only (`git ls-files`, capped at 2000 files; binary
files skipped by null-byte heuristic) for credential-shaped strings:

| Pattern | What it finds |
|---|---|
| `aws_secret_access_key\s*[=:]\s*\S` | AWS secret key assignments |
| `AKIA[0-9A-Z]{16}` | AWS access key IDs |
| `-----BEGIN (RSA \|EC )?PRIVATE KEY-----` | PEM private keys |
| `ghp_[A-Za-z0-9]{36}` | GitHub personal access tokens |
| `(api[_-]?key\|secret\|token)\s*[:=]\s*['"][A-Za-z0-9+/]{20,}` | Generic API key/token assignments |

**The secret value itself is never printed.** Only the file path and pattern class are
reported, so the warning is safe to display in a shared transcript.

**Profile ladder:**

- `minimal`: silent exit 0; no checks run.
- `standard`: warnings emitted for both legs.
- `strict`: same as standard (exit 0 is fixed; SessionStart must not block regardless of
  profile — unlike PreToolUse there is no deny convention here).

### `board-guard.sh` — PreToolUse on Edit / Write / MultiEdit (optional, Project Board)

Keeps board work **fixed and stable** by steering every write through `scripts/board.py` (the
only sanctioned writer — see [`references/project-board-crud.md`](../../references/project-board-crud.md)).
Installed with `/project-meta init --board`; in `settings.json.fragment` but **drop the
`PreToolUse` block if the repo has no Project Board.**

- `minimal`: disabled (exit 0).
- `standard`: blocks hand-edits to the **derived** `docs/dashboard.html` (always regenerate via
  `board.py render`). Returns the guidance to the agent (exit 2).
- `strict`: also blocks hand-edits to the CLI-managed store
  (`docs/backlog/items.jsonl | roadmap.json | inbox.jsonl`); use `board.py` verbs instead.

Fails open — any payload it cannot parse → exit 0, never wedges the session. It guards the
Edit/Write/MultiEdit *tools*; it does not parse `Bash` commands (a `>>`/`rm` against the store
is out of scope by design). The matching Stop check is `verify-before-stop.sh` step 5, which
runs `board.py tx` to catch a stale/corrupt store before the turn ends.

## Profile Selection Guidance

| Profile | When to use |
|---|---|
| `minimal` | Throwaway prototypes, exploratory notebooks, single-author repos where review burden outweighs harness benefit |
| `standard` | Default for most repos. Catches obvious problems without blocking turns. |
| `strict` | Production codebases with regression cost > minute-level friction. Only enable after `standard` has been running cleanly for at least a week. |

Switch profiles by editing `settings.json` `env.HARNESS_PROFILE`. No
script changes required.

To enable bounded elasticity for advisory legs, add one or both bounds to
`settings.json` `env`:

```json
{
  "env": {
    "HARNESS_PROFILE": "standard",
    "HARNESS_PROFILE_FLOOR": "standard",
    "HARNESS_PROFILE_CEILING": "strict"
  }
}
```

If both bounds are absent, the hook pack is fully static. Use a floor equal to the
minimum profile you are willing to run for advisory friction and a ceiling equal to the
maximum advisory friction you want the evidence resolver to choose.

For Codex installs, switch profiles by re-running
`install_codex_hooks.py --profile <minimal|standard|strict>` or by editing
the injected `HARNESS_PROFILE=...` prefix in `~/.codex/hooks.json`.

## Anti-patterns

- **Hooks that always pass silently.** A standard-profile hook that
  never warns is dead code. Either tighten checks or delete the hook.
  AP-VAL-1.
- **Strict profile turned on too early.** Strict blocks turns. If the
  team isn't ready for that friction, agents start working around the
  hooks instead of fixing the underlying problem. Roll out in standard
  first.
- **Hard-coded paths in hook scripts.** Hooks shipped with paths
  specific to one repo break when the pack is reused. Keep paths
  relative to the repo root, with env-var overrides where needed.
- **Hooks doing the agent's job.** A hook that re-runs the work
  the agent should have done (e.g. running tests the agent skipped) is
  papering over a different problem. Fix the agent's procedure
  instead. AP-COORD-3.

## Custom Hooks

Add new hooks by:

1. Drop the script into `.claude/hooks/<name>.sh` and `chmod +x`.
2. Wire it into `.claude/settings.json` under the appropriate event
   (`PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`).
3. Make the script profile-aware (`$HARNESS_PROFILE`) so it inherits
   the project's enforcement dial.
4. Keep it std-Unix (bash, posix tools); if it needs Python, gate the
   import on availability and exit 0 cleanly when missing.
5. Document it in `agents/<harness-topic>.md` so the team can audit.
