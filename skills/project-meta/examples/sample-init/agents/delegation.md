---
artifact_name: delegation
instantiated_from: project-meta/templates/delegation.md
source_reference: project-meta/references/multi-agent-protocols.md
project_scope: toy-weather-cli only
owner: agent-facing
review_policy: user review before first behavior-changing commit
last_reviewed: 2026-06-06
---

# Delegation Rules — toy-weather-cli

Multi-agent dispatch context packages for this repo. Load only when explicitly
coordinating parallel or delegated work.

## Worker Context Package

```
Role: Worker
Goal: implement a bounded, well-specified change to weather.py or tests/
Read first:
- AGENTS.md
- agents/pre-commit-delivery.md
Ownership: may edit weather.py, tests/, lib/ (new files require lead approval)
Constraints:
- Keep weather.py ≤200 lines; extract to lib/ if needed
- All HTTP calls via weather.fetch(url, timeout=10)
- No API keys in source; use WEATHER_API_KEY env var
Output format: patch summary (files changed, lines delta, test result)
Review criteria:
- pytest -q passes
- No new secrets in diff
Memory policy: report only; lead agent updates AGENTS.md
```

## Reviewer Context Package

```
Role: Reviewer
Goal: verify the worker's output meets the operating rules
Read first:
- AGENTS.md
- agents/pre-commit-delivery.md
Ownership: read-only
Constraints:
- Return PASS, SUGGEST, or BLOCKER with one-line rationale each
Output format: reviewer-report (verdict + findings list)
Review criteria:
- Tests pass; no secrets; weather.py ≤200 lines; API contract preserved
Memory policy: report only
```
