# Manual worker invocation, evidence, and monitoring fallback

The worker is started **explicitly by the upstream host, one task at a time**. This release has
no launcher, no scheduler, and no background worker — never imply one.

## 1. Invocation (pi)

Flags below were checked against `pi --help` for `--print/-p`, `--mode`, `--model`,
`--session-id`, `--session-dir`, `--tools`, `--no-mcp`, `--no-extensions`, `--no-skills`,
`--no-prompt-templates`, `--no-themes`, `--offline`. Substitute **your own** configured
provider/model; this document deliberately ships no private model name, no credential, and no
absolute path to a developer's machine.

```bash
pi --print --mode json \
  --model <user-configured provider/model> \
  --session-id <UUID> \
  --session-dir <explicit, scoped session directory for this task/project> \
  --tools read,bash,edit,write,grep,find,ls \
  --no-mcp --no-extensions --no-skills --no-prompt-templates --no-themes --offline \
  "<scoped task text>"
```

- `--session-id <UUID>` + `--session-dir` give a **re-usable explicit session**; reuse the same
  id and directory for corrections on the same task. Use a fresh session with a bounded
  handoff for unrelated work or when elapsed delay / repeated rediscovery appears — decide on
  time and upstream load, not on worker token counts. No unconditional global `--continue`.
- The `--no-*` flags and `--tools` are a **task-local, optional** resource trim, **not** a
  global settings change. Do not edit global config to "apply" them.
- `--offline` disables **startup network operations only**. It is *not* a claim that the model
  request runs without network.
- The tool allowlist **includes `bash` and is not an OS sandbox**. An allowlist does not
  confine arbitrary code; never claim isolation from it.
- Invoking the worker must not silently enable **external write actions** the task did not
  authorize (no surprise MCP servers, credentials, or publishing paths). Keep writes inside
  the target repo's allowed files.
- The worker edits the working tree, so treat it as an **implementation worker**, not a
  read-only reader, when stating its blast radius.

## 2. Task envelopes (fill in, keep scoped)

Initial task — send scope and references, never the whole repo or thread:

```text
TASK-ID: <id>
Objective: <one sentence>
Collaboration tier: <eco|balanced|boost|full> (source: user|inherited|default — default is provisional)
Allowed files: <paths the worker may edit>
Acceptance checks: <focused tests/gates that must pass — fixed; not reduced by tier>
Known facts / refs: <artifact paths, prior findings — no full paste>
Budget (starting heuristic, soft): <turns / stop-and-report trigger>
Constraints: <the TARGET REPO's commit/branch/dirty-tree rules>
```

Correction — reuse the same session id and path:

```text
CORRECTION for TASK-ID: <id> (session: <UUID / path>)
Issue ID: <n>
Observed: <what happened>
Expected: <what must happen>
Reproduction / evidence: <command + minimal output>
Remaining checks: <focused tests to re-run>
```

Worker report (pi → upstream):

```text
TASK-ID: <id>
Changed files: <paths + one-line intent each>
Checks run: <command → result excerpt>
Blockers / limitations: <honest list>
Status: implementation ready — SUPERVISOR REVIEW PENDING
```

Efficiency discipline: batch cohesive edits into one worker turn; prefer a bounded read plus a
local edit over a full rewrite; review the **changed delta plus relevant invariants**, not the
whole tree; run focused tests first and do not re-run already-green checks without a stated
reason. Required acceptance checks are never trimmed.

## 3. Evidence packet rules

The worker returns a compact packet: key changed paths, the exact test command plus a small
actual result excerpt, artifact paths, and unresolved questions/risks. Full logs stay local
and are inspected **on demand** for high-risk work. Independent upstream review decides
acceptance; the worker's `Status` line never claims acceptance.

## 4. Monitoring fallback (no monitor is bundled here)

**Nothing in this skill provides timing or token tooling.** The optional recorder lives in the
LICP source environment as `tools/task_monitor.py` (module `TaskMonitor`, plus `build_report`
and `render_html`) and is **not** shipped with this plugin. Cite it only when it genuinely
exists in your environment, at that exact relative path. Never add an import of a module that
is not installed, and never claim a script was delivered when it was not.

Without a monitor, fall back to data you can observe directly:

- **Elapsed time**: record explicit UTC timestamps per stage (dispatch, execution, review,
  feedback, acceptance) around the invocations; total elapsed is task end − start, kept
  **separate** from overlapping stage durations, which are never summed into a total.
- **Worker tokens**: read the worker's own session/usage records if the harness exposes them,
  and report the **native** counters separately. If not exposed → **unknown**, not zero.
- **Upstream tokens**: the same rule for the frontier host's own session records; otherwise
  **unknown** plus a labeled proxy (interventions, round-trips, evidence size).

Counter semantics to preserve when you do read native logs:

- Codex-style counters **include** cached input in `input_tokens` — do not add cache reads on
  top.
- Pi-style native input **excludes** `cacheRead`/`cacheWrite`; a gross input figure is a
  derived value, so label it.
- **Reasoning tokens are a subset of output**, never re-added.
- Reported usage is **provider metadata, not verified billing**; a reported zero cost does not
  prove the call was free.
- Snapshot timestamps can **lag** wall-clock; a delta is the interval between two *observed*
  snapshots, not exact billing and not exact task-boundary attribution.

## 5. Reuse first, without inventing an interface

Before delegating new *model* work in either direction, consider an existing deterministic
script. If a Script-Dispatcher library/registry is actually present, use **its** real
discovery and registration surface and extend rather than duplicate. If it is not present,
**record that discovery is unavailable and continue the authorized workflow** — do not block,
do not invent commands or flags, and do not stand up a second registry.
