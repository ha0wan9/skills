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
`standard` / `strict`.

## Layout

```
.claude/
  settings.json              # merged from settings.json.fragment
  hooks/
    load-agents-md.sh        # SessionStart
    format-on-edit.sh        # PostToolUse on Edit/Write/MultiEdit
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

### `verify-before-stop.sh` — Stop

Six responsibilities:

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

- `minimal`: hook disabled (the write-back and dispatch gates also
  self-disable on `HARNESS_PROFILE=minimal`)
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
