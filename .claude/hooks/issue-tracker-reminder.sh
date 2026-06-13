#!/usr/bin/env bash
# UserPromptSubmit hook: when the user's prompt has feature-proposal shape,
# remind the agent to run the issue-tracker Track Loop (check for an existing
# ticket → write progress back → open one if missing). Output is injected into
# the agent's context.
#
# ADVISORY ONLY. A shell hook has no MCP access, so it CANNOT query or write the
# tracker — it can only remind. It must never block the turn (that would be
# enforcement it cannot back up). See
# project-meta/references/issue-tracking-integration.md (AP-VAL-1).
#
# Opt-in: ships only with the `issue-tracker` capability, not the default pack.
# Tracker specifics live in agents/issue-tracking.md, not here — this hook is
# generic and points the agent at that doc.
#
# Profile-aware via $HARNESS_PROFILE (minimal | standard | strict):
#   minimal  — disabled (exit 0)
#   standard — advisory reminder on a keyword match
#   strict   — stronger MUST-phrased reminder (still non-blocking)

set -euo pipefail

PROFILE="${HARNESS_PROFILE:-standard}"

# minimal: hook disabled.
if [[ "$PROFILE" == "minimal" ]]; then
  exit 0
fi

# Read the hook payload from stdin. Prefer jq for the prompt field; fall back to
# the raw stdin text so the hook still works without jq.
payload="$(cat 2>/dev/null || true)"
prompt=""
if command -v jq >/dev/null 2>&1 && [[ -n "$payload" ]]; then
  prompt="$(printf '%s' "$payload" | jq -r '.prompt // .user_prompt // empty' 2>/dev/null || true)"
fi
if [[ -z "$prompt" ]]; then
  prompt="$payload"
fi
if [[ -z "$prompt" ]]; then
  exit 0
fi

# Only fire when the issue-tracking workflow is actually installed.
if [[ ! -f agents/issue-tracking.md ]]; then
  exit 0
fi

# Feature-proposal shape — conservative phrase list to avoid over-firing on the
# bare word "feature" (AP-VAL-1). Case-insensitive, English + common Chinese.
lc="$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')"
matched=0
for pat in \
  "premium feature" "new feature" "feature idea" "feature request" \
  "add a feature" "build a feature" "ship a feature" "product idea" \
  "let's build" "let us build" "next idea" "add to backlog" "to the backlog" \
  "新功能" "新 feature" "做一个功能" "加入 backlog"; do
  if [[ "$lc" == *"$pat"* ]]; then
    matched=1
    break
  fi
done

if [[ "$matched" -eq 0 ]]; then
  exit 0
fi

if [[ "$PROFILE" == "strict" ]]; then
  cat <<'EOF'
[harness] feature proposal detected. MUST run the issue-tracker Track Loop per
[harness] agents/issue-tracking.md: (1) check the tracker for an existing ticket
[harness] before creating one, (2) write progress back to the ticket as the
[harness] feature advances, (3) open a ticket if none exists. The repo stays
[harness] canonical; tracker issues summarize and link back.
EOF
else
  cat <<'EOF'
[harness] feature proposal detected — see agents/issue-tracking.md: check the
[harness] tracker for an existing ticket first, write progress back as it
[harness] advances, and open one if none exists (summary + link, repo canonical).
EOF
fi

exit 0
