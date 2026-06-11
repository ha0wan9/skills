---
name: calendar-crud-workflow
description: Standardize calendar event CRUD from fuzzy requests into stable calendars, title prefixes, searchable description tags, source links, and safe batch create/update/delete workflows. Use when the user asks to schedule, classify, bulk add, migrate, tag, color, or clean up calendar events across Google Calendar, Apple/iOS Calendar, Notion Calendar, or MCP calendar tools, especially when deciding between separate calendars, title labels, event colors, and description tags.
metadata: {version: 1.2.1, compat: [claude-code, codex], published: [claude-marketplace]}
---

# Calendar CRUD Workflow

> **Runtimes:** Claude Code · Codex &nbsp;|&nbsp; **Published:** Claude Marketplace

Turn vague scheduling requests into safe, normalized calendar operations with stable cross-device behavior, searchable metadata, and reversible bulk changes.

## Trigger Decision

Use this skill for any of these request shapes:

- **Schedule / create**: user provides event details (time, topic, link) and wants them on a calendar.
- **Classify / tag**: user has existing events and wants them categorized, prefixed, or tagged.
- **Bulk add**: user provides a list (schedule page, email, spreadsheet) to convert into multiple events.
- **Migrate / move**: user wants events moved between calendars or restructured across categories.
- **Color**: user asks for calendar-level or event-level color assignment across Google/iOS/Apple.
- **Clean up / delete**: user wants events removed, deduplicated, or archived.

Do not use this skill for repo-harness setup or project memory operations — those belong to `project-meta`.

## Bootstrap Order

1. Read the user's request and extract action, scope, and calendar candidate.
2. Read existing events in the target time window before any write.
3. Confirm classification (calendar → prefix → description tags) before acting.
4. Load [`references/crud-procedure.md`](references/crud-procedure.md) for full step-by-step detail when needed.

## Core Rules

- **MUST read existing events before any write.** Search the bounded time window and check for duplicate title/source/link combinations before creating, updating, or deleting.
- **MUST present a batch proposal and get explicit confirmation before executing any batch create, update, or delete.** Do not silently apply bulk changes.
- **MUST NOT silently fall back from a calendar color to an event color.** If the user asked for stable cross-device color and the required calendar cannot be created, ask the user to create it or supply a calendar ID.
- **MUST NOT create a new video-conference link unless the user explicitly asked.** If the source provides a Zoom or Meet link, attach that link instead.
- **MUST dedupe-check before create.** If a matching title/time/source combination already exists, report it and ask before adding a duplicate.
- **MUST NOT delete a recurring-series event without first confirming scope** (this instance / this-and-following / entire series).
- Default: prefer a separate calendar for stable large categories; use description tags for fine-grained labels; use title prefixes only for temporary state or at-a-glance triage when calendar color is insufficient.
- Do not create a calendar for every small topic — use description tags instead.

## Skill Arbitration

| Request shape | Owning skill | This skill's role |
|---|---|---|
| Calendar CRUD (create/update/delete/move/color/tag) | **`calendar-crud-workflow`** | acts |
| Repo-harness setup, project memory, CLAUDE.md writes | **`project-meta`** | dispatches; do not act |
| Mixed: set up a project *and* schedule its events | **`project-meta`** first, then this skill | hand off after harness is ready |

## Gotchas

- **Event color vs. calendar color.** iOS and Apple Calendar only expose calendar-level colors reliably; event colors created in Google often render as the calendar color on Apple. Always classify calendar first; use event color only for Google-local visual distinction.
- **Recurring-event scope.** Editing or deleting a recurring event without scope clarity corrupts the series. Distinguish this instance, this-and-following, and entire series before any write.
- **Description overwrite.** A normalized description update can silently drop existing Zoom links, notes, or attendee instructions. Preserve unrelated fields; merge, don't replace.
- **Missing end time.** Many source pages omit end times. Infer the smallest defensible duration from adjacent events and mark it `(inferred)` in the description — never silently omit.

## Quick Workflow

Full detail for each step is in [`references/crud-procedure.md`](references/crud-procedure.md).

1. **Parse intent** — extract action, scope, title, time, calendar candidate, links, tags.
2. **Read before write** — search time window, check duplicates, read full payload for updates.
3. **Classify calendar first** — calendar → title prefix → description tags → event color (last resort).
4. **Draft write plan** — for batches, show `Date | Time | Calendar | Title | Link | Tags | Confidence | Notes` and wait for confirmation.
5. **Create / Update / Move / Delete** — follow the op-specific rules in the reference; use diff-oriented updates; verify moves before deleting the source.

## When To Load References

| Task class | Reference to load |
|---|---|
| Any create / update / delete / move / classify / recolor | [`references/crud-procedure.md`](references/crud-procedure.md) |
| Classification model, calendar categories, prefix rules, description contract | [`references/crud-procedure.md`](references/crud-procedure.md) |

## Output Footer

End each invocation with:

```text
**Skill**: calendar-crud-workflow  **Status**: <done|blocked|needs-confirmation>  **Next**: <action|done>
```

Report: event count changed, target calendar(s), any inferred durations, unresolved TBD items, link provenance (email / source page / calendar payload), and verification result. Keep URLs out of the summary unless the user asks.
