#!/usr/bin/env bash
# dispatch-tier-guard.sh — PreToolUse advisory dispatch-tier guard
# (matcher Task|Agent|Workflow).
#
# Surfaces silent session-model inheritance at Agent-dispatch time. `Agent` is the
# current tool name; `Task` is the historical alias — a dead regex alternative is
# harmless and covers older runtimes. See
# docs/plans/model-tier-routing-build-plan.md §2 decision #4.
#
# Workflow extension (local, 2026-08-14): the Workflow tool's internal agent()
# fan-out never passes through the Task|Agent matcher, so a script whose agent()
# opts omit `model:` silently inherits the session model for EVERY spawned
# subagent — the exact leak this guard exists to surface, multiplied by the
# fan-out. For a Workflow payload the guard scans the script text (inline
# `script`, or the file behind `scriptPath`) and WARNs when it finds more
# `agent(`/`workflow(` call sites than explicit `model:` keys. Heuristic and
# advisory by design (meta.phases model rows overcount in our favor); exit 0
# always.
#
# Branches evaluated in order, first match wins. ALL branches exit 0 (advisory —
# the PreToolUse payload cannot see agent-definition frontmatter `model:` or the
# session-default resolution chain, so a deny would false-positive on legitimate
# flows). The hook is stateless — it never queries the ledger.
#
#   1. model present, haiku/sonnet/luna-class (substring match) → silent
#   2. model present, opus/terra-class                          → notice
#   3. model present, fable/sol/conductor-class                 → notice
#   4. model absent, subagent_type generic/unset                → WARN
#   5. model absent, subagent_type other (Explore/Plan/custom)  → short notice
#
# Non-string `subagent_type`/`model` values are treated as "custom/unknown" —
# routed down the notice path, never a crash. An unrecognized (non-empty) model
# string that doesn't match any known tier substring gets its own one-line notice.
#
# Profile-aware via $HARNESS_PROFILE:
#   minimal  — silent pass-through; exit 0 always
#   standard — emit the matched branch's message to stderr; exit 0 (advisory)
#   strict   — same as standard; this hook has no deny path in v1 (see plan §1)
#
# Fails open — any payload that cannot be parsed → exit 0 (never wedge the session).
set -uo pipefail

profile="${HARNESS_PROFILE:-standard}"
[ "$profile" = "minimal" ] && exit 0

input="$(cat 2>/dev/null || true)"
[ -z "$input" ] && exit 0

# Extract .tool_input.model and .tool_input.subagent_type from the PreToolUse JSON
# payload via python3. python3 is a harness prerequisite; if unavailable, or if the
# payload cannot be parsed, we fail open (silent exit 0).
#
# Output protocol (two lines): line 1 = branch tag, line 2 = detail (model or
# subagent_type string, best-effort, may be empty).
parsed="$(printf '%s' "$input" | python3 -c '
import sys, json

def classify(model):
    if not isinstance(model, str) or not model.strip():
        return None
    m = model.lower()
    if "haiku" in m or "sonnet" in m or "luna" in m:
        return "silent"
    if "opus" in m or "terra" in m:
        return "opus"
    if "fable" in m or "sol" in m or "conductor" in m:
        return "fable"
    return "unknown-model"

try:
    d = json.load(sys.stdin)
except Exception:
    print("parse-error")
    sys.exit(0)

ti = d.get("tool_input")
if not isinstance(ti, dict):
    ti = {}

# Workflow payloads carry a script (inline or by path), never model/subagent_type.
if d.get("tool_name") == "Workflow" or "script" in ti or "scriptPath" in ti:
    import re
    script = ti.get("script")
    if not isinstance(script, str):
        script = ""
    if not script:
        sp = ti.get("scriptPath")
        if isinstance(sp, str) and sp.strip():
            try:
                with open(sp, "r", encoding="utf-8") as fh:
                    script = fh.read()
            except Exception:
                print("parse-error")
                sys.exit(0)
    if not script:
        print("parse-error")  # resume-only / named-workflow payload — nothing to scan
        sys.exit(0)
    calls = len(re.findall(r"\bagent\(", script)) + len(re.findall(r"\bworkflow\(", script))
    models = len(re.findall(r"\bmodel\s*:", script))
    if calls > models:
        print("warn-workflow")
        print(f"{calls} agent() call(s), {models} explicit model key(s)")
    else:
        print("silent")
        print("")
    sys.exit(0)

model = ti.get("model")
subagent_type = ti.get("subagent_type")

model_str = model if isinstance(model, str) else None

if model_str is not None and model_str.strip():
    tag = classify(model_str)
    print(tag if tag else "parse-error")
    print(model_str)
    sys.exit(0)

# model absent (or present-but-non-string/empty) — branch on subagent_type.
if isinstance(subagent_type, str):
    st = subagent_type.strip()
else:
    st = ""  # non-string subagent_type treated as unset/custom

GENERIC = {"general-purpose", "claude", ""}

if st.lower() in GENERIC:
    print("warn-generic")
    print(st)
else:
    print("notice-other-type")
    print(st)
' 2>/dev/null || true)"

[ -z "$parsed" ] && exit 0

tag="$(printf '%s\n' "$parsed" | sed -n '1p')"
detail="$(printf '%s\n' "$parsed" | sed -n '2p')"

case "$tag" in
  silent|"")
    exit 0
    ;;
  opus)
    echo "[dispatch-tier-guard] NOTICE: escalation-tier dispatch (sanctioned <=2/run — see model-tier canon); this notice also fires on legitimate escalations (model=$detail)" >&2
    exit 0
    ;;
  fable)
    echo "[dispatch-tier-guard] NOTICE: conductor-tier dispatch — canon allows at most one unblock call per run (model=$detail)" >&2
    exit 0
    ;;
  unknown-model)
    echo "[dispatch-tier-guard] NOTICE: unrecognized model tier (model=$detail)" >&2
    exit 0
    ;;
  warn-workflow)
    echo "[dispatch-tier-guard] WARN: Workflow script has $detail — agent() calls without an explicit model inherit the SESSION model for every spawned subagent; fleet default is sonnet: pass {model:'sonnet'} per call, escalate only with a stated reason" >&2
    exit 0
    ;;
  warn-generic)
    echo "[dispatch-tier-guard] WARN: dispatch inherits the session model — fleet default is sonnet/luna; pass model:'sonnet' (Claude) or model:'luna' (Codex), or confirm the agent definition pins a model (invisible to this hook)" >&2
    exit 0
    ;;
  notice-other-type)
    echo "[dispatch-tier-guard] NOTICE: subagent_type='$detail' dispatched without an explicit model — the type likely pins its own model in frontmatter (invisible to this hook)" >&2
    exit 0
    ;;
  parse-error|*)
    # Unparseable payload or any unrecognized tag — fail open, silent.
    exit 0
    ;;
esac
