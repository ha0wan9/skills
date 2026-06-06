---
name: openclaw-devops
description: >-
  OpenClaw maintenance DevOps skill: a sanity/health probe, bounded self-repair,
  transactional auto-update across all npm copies with post-update integrity
  verification + automatic rollback, an ops lessons journal, and a bugs
  panel/backlog any agent or cron can log to and track to resolution — driven by
  an OpenClaw cron or on demand. Runtime-agnostic (Claude Code, Codex, OpenClaw).
  Delegates systematic debugging to the meta-debug skill and supplies the OpenClaw
  reproduce/verify/rollback mechanics its phases call. Use when health-checking,
  repairing, upgrading, rolling back, or scheduling maintenance for an OpenClaw
  gateway/node install, when logging or tracking bugs in the backlog, or when
  OpenClaw is broken / out of date / crash-looping / failing config validation.
metadata: {version: 1.2.0, compat: [claude-code, codex, openclaw], published: [claude-marketplace]}
---

# OpenClaw DevOps

Action-oriented maintenance for an OpenClaw install: **observe → repair → update
→ verify → roll back**, done by a deterministic stdlib engine
(`scripts/openclaw_devops.py`). The agent invokes the right verb, relays the
structured result, and stops — the engine encodes the safe, ordered procedure.

For *systematic debugging* of a hard/recurring bug, this skill is **not** the
pipeline — it **defers to `meta-debug`** (the gated repro→test→hypotheses→top-k
sandbox fixes→validate→canary→lesson flow) and supplies the OpenClaw mechanics
that pipeline calls: `rollback` (phase-0 mitigate / phase-8 revert) and `verify`
(phase-8 integrity gate).

## Trigger Decision

- **Health/sanity**: "is OpenClaw healthy?", services down, gateway not
  responding, config validation failing, version skew across copies.
- **Self-repair**: restart dead services, normalize stale plugin/cron config,
  re-align version skew.
- **Update**: "update OpenClaw", "is there a newer version?", scheduled upgrade.
- **Rollback**: an upgrade went bad, "revert OpenClaw", restore last-good.
- **Schedule**: set up / change an OpenClaw cron that runs maintenance.
- **Ops lessons**: record/recall an OpenClaw maintenance lesson.
- **Bugs backlog**: log a bug hit during any agent/cron run, triage it, track its
  fix status, link it to a meta-debug session, or view the panel.

## Bootstrap Order

1. Confirm the engine + `config.json` exist in this skill dir.
2. Identify the host (config defaults target a primary gateway host). For a
   different host, override `config.json` (`copies`, `services`, paths) — never
   hard-code paths into the prompt.
3. Pick the verb (below). Prefer `sanity` first when state is unknown.
4. Load `references/runbook.md` only when you need the manual procedure, the
   failure-mode catalog, the cron recipe, the sudoers setup, or cross-runtime
   install details. For a debug *session*, switch to the `meta-debug` skill.

## Core Rules

- **MUST run `sanity` before any mutating verb when current state is unknown.**
  Reason: repair/update decisions are driven by the sanity report; acting blind
  risks restarting healthy services or updating a degraded host.
- **MUST keep all npm copies version-aligned.** Reason: a system-vs-user version
  skew crash-loops the gateway. `update` and the skew branch of `repair` install
  every copy to the same version.
- **MUST treat update as transactional.** Reason: integrity over freshness. The
  engine snapshots config + records the prior version, updates, gates on `verify`
  (config validate + health + cron + alignment), and auto-rolls-back on failure.
  Never bypass the verify→rollback path.
- **MUST NOT take unbounded or destructive repair actions.** Reason: self-repair
  runs unattended on a cron. Allowed: service restart/reset-failed, daemon-reload,
  `doctor --fix` config normalization, version re-align. Anything else is out of
  scope — surface it as a recommendation for a human.
- **MUST use the `meta-debug` skill for systematic debugging, not improvise.**
  Reason: a hard/recurring bug needs the gated pipeline (reproduce → red test →
  confirmed root cause → top-k sandbox fixes → validate → reversible ship).
  openclaw-devops only supplies the OpenClaw `rollback`/`verify` mechanics that
  pipeline calls; it does not own the debug workflow.
- **Default:** auto-update follows the `latest` stable dist-tag and holds major
  jumps (`hold_major`) until a human passes `--allow-major`.
- **Any agent or cron that hits a bug it can't fix inline SHOULD log it to the
  backlog** (`bugs --add --source <self>`), and a debug session that fixes a
  backlog bug SHOULD close the loop (`bugs --update <id> --status fixed --session
  <dbg-id> --lesson …`). Reason: a shared backlog only helps if bugs land in it
  and resolutions are recorded against them.
- **Default:** report by relaying the engine's rendered summary; `--json` when a
  tool will consume it. Record a one-line ops lesson after a non-trivial fix
  (`lessons add`); a full debug session records its own lesson via meta-debug.

## Skill Arbitration

| Request shape | Owning skill | This skill's role |
|---|---|---|
| Maintain/repair/update/roll back/health-check an OpenClaw install; schedule a maintenance cron | **openclaw-devops** | acts |
| Systematic debugging of a hard/flaky/recurring bug (gated repro→fix→ship) | **meta-debug** | openclaw-devops **defers** to it as the debug base layer, and provides the OpenClaw `rollback`/`verify` mechanics its phases invoke. |
| Observe-only audit of OpenClaw skill/cron quality or tool-failure reporting (no mutations) | out of scope for this skill | This skill *acts*; pure-observation auditing is not a capability it ships. |

## Gotchas

- **State is written to the project repo, not the skill install dir** — the
  install dir is wiped on marketplace updates and is shared across repos.
  Resolution order: `--state-dir` CLI flag › `$OPENCLAW_DEVOPS_STATE_DIR` env
  var › `<nearest .git ancestor of cwd>/.harness/openclaw-devops/` › CWD
  fallback. Pass `--state-dir` or set the env var when running outside a git
  repo or to direct multiple repos to separate state paths.
- **System `/usr/lib` copy needs sudo; the engine only acts if `sudo -n` works.**
  Without passwordless sudo it updates the user copy, marks the system copy
  `skipped`, and warns about skew. Scope a sudoers rule for full automation
  (runbook), or run the system step by hand.
- **The OpenClaw cron should be a thin agentTurn that just runs the engine and
  posts its summary.** Maintenance determinism must live in the script, not a
  flaky LLM turn.
- **`cycle` holds a flock** (`<state-dir>/devops.lock` — default `.harness/openclaw-devops/devops.lock` under the project repo, or `$OPENCLAW_DEVOPS_STATE_DIR`/`--state-dir` when overridden); overlapping fires exit cleanly.
- **Version "major" is calendar-based** (`version_major_index`, default 0 = year).
- **Restart order matters**: gateway → chloe → node (node dials the gateway).

## Quick Workflow

```bash
ENG=<skill>/scripts/openclaw_devops.py
python3 $ENG sanity                 # health probe (read-only)
python3 $ENG repair --dry-run       # plan repairs
python3 $ENG update --dry-run       # plan an upgrade (snapshot+verify+rollback when real)
python3 $ENG rollback               # restore recorded previous version + config
python3 $ENG cycle --json           # full orchestrated run (cron entry)
python3 $ENG lessons --list         # ops maintenance journal
python3 $ENG lessons --title "…" --bug "…" --cause "…" --fix "…" --tags "…"

# bugs panel / backlog — any agent or cron can log a bug it hit:
python3 $ENG bugs --add --title "…" --severity sev2 --source "<agent/cron>" --detail "…" --tags "…"
python3 $ENG bugs --panel                       # backlog summary (cron-friendly)
python3 $ENG bugs --list --status open          # filter; --show BUG-3 for one
python3 $ENG bugs --update BUG-3 --status fixed --session dbg-… --lesson "…" --note "…"
# systematic debugging → use the meta-debug skill (debug_session.py + debug-pipeline.md)
```

## When To Load References

- Need the upgrade/rollback procedure, the repair-action catalog, the failure
  modes (version skew, stale plugins, headless browser), the OpenClaw cron
  recipe, the sudoers setup, or how to drop this skill into Claude/Codex roots:
  - load [`references/runbook.md`](references/runbook.md).
- Running a debug *session* (the gated pipeline): switch to the **`meta-debug`**
  skill and load its `references/debug-pipeline.md`.

## Output Footer

End every invocation with: the verb run, overall status (`ok/warn/fail`), any
mutating actions taken (or "none / dry-run"), and — for `update` — whether it
applied, held, or rolled back, with the from→to versions.
