---
artifact_name: pre-commit-delivery
instantiated_from: project-meta/templates/pre-commit-delivery.md
source_reference: project-meta/references/documentation-delivery.md
project_scope: toy-weather-cli only
owner: agent-facing
review_policy: user review before first behavior-changing commit
last_reviewed: 2026-06-06
---

# Pre-Commit Delivery Checklist — toy-weather-cli

Show this delivery to the user before every commit that modifies `weather.py`,
`tests/`, `lib/`, or any agent-facing file.

## User-Facing Summary

Present in plain language: what changed, why, and what the user should verify.

Example (fill in per commit):
> Added timeout handling to `weather.fetch()` so the CLI exits cleanly on
> network errors instead of hanging. No behavior change for the happy path.

## Agent-Facing Diff Summary

- Files changed: list each file with lines added / removed.
- Tests: `pytest -q` result (pass/fail + count).
- Memory updated: yes/no — if yes, cite the canonical file and the change.

## Gate Checklist

- [ ] User-facing summary shown and acknowledged.
- [ ] `pytest -q` passes (no failures, no errors).
- [ ] No API keys, tokens, or credentials in the diff.
- [ ] `weather.py` ≤ 200 lines (current: __ lines).
- [ ] `AGENTS.md` updated if a durable rule or lesson was learned.
- [ ] `USER.md` is not staged.
