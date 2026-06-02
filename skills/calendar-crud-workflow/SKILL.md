---
name: calendar-crud-workflow
description: Standardize calendar event CRUD from fuzzy requests into stable calendars, title prefixes, searchable description tags, source links, and safe batch create/update/delete workflows. Use when the user asks to schedule, classify, bulk add, migrate, tag, color, or clean up calendar events across Google Calendar, Apple/iOS Calendar, Notion Calendar, or MCP calendar tools, especially when deciding between separate calendars, title labels, event colors, and description tags.
---

# Calendar CRUD Workflow

Use this skill to turn vague scheduling requests into safe, normalized calendar operations. The goal is stable cross-device behavior, searchable metadata, and reversible bulk changes.

## Core Model

Each event has four independent classification layers:

| Layer | Purpose | Stable across Google/iOS/Apple? |
|---|---|---|
| Calendar | Large category, calendar-level color, show/hide control | Yes |
| Title prefix | Temporary status or workflow marker | Yes |
| Title | Human-readable event name | Yes |
| Description tags | Fine-grained searchable labels and provenance | Mostly yes |

Prefer separate calendars for large stable categories, title prefixes for temporary status, and description tags for fine-grained semantics.

## Category Rules

Use a separate calendar when the category needs stable color, independent visibility, or reliable iOS/Apple sync:

- `Work`: company, client, recruiting, operational, administrative work
- `Personal`: life, health, family, errands, personal plans
- `Research`: papers, experiments, academic talks, reading groups, research planning
- `Teaching`: courses, TA duties, office hours, educational delivery
- Project calendars such as `Neuromatch`: recurring program-specific schedules that need their own stable color and on/off control

Do not create a calendar for every small topic. Use description tags instead.

## Prefix Rules

Use title prefixes for workflow state, not taxonomy:

- `[Hold]`: placeholder, not confirmed
- `[Tentative]`: time or commitment uncertain
- `[Prep]`: preparation block
- `[Admin]`: administrative task
- `[Paper]`: paper reading or discussion
- `[NMA]`: Neuromatch marker only when no dedicated Neuromatch calendar exists

If the event is already on a dedicated project calendar, avoid redundant prefixes unless the prefix expresses state.

## Description Contract

Normalize descriptions with stable fields:

```text
Tags: neuromatch, neuroai, course, professional-development
Source: https://...
Links:
- Zoom: https://...
- Reference: https://...
Notes:
...
```

Use lowercase tags. Prefer `kebab-case` for multi-word tags. Keep source links and meeting links distinct.

## CRUD Workflow

### 1. Parse Intent

Extract:

- action: create, read, update, delete, move, copy, classify, recolor
- scope: single event, batch, recurring series, time window
- category/calendar candidate
- title and optional prefix
- start/end/timezone, or duration if end time is missing
- location and meeting links
- attendees, reminders, transparency, recurrence
- tags, source, confidence, unresolved fields

Normalize relative dates into absolute dates before writing.

### 2. Read Before Write

Before create/update/delete/move:

- Search the bounded time window.
- Check duplicate title/source/link combinations.
- Read full event payload when preserving attendees, recurrence, reminders, location, or description matters.
- For recurring events, distinguish this instance, this-and-following, and entire series.

### 3. Classify Calendar First

Choose calendar before color:

```text
Need stable iOS/Apple color? -> use/create a separate calendar.
Need only Google-local visual distinction? -> event color is acceptable.
Need searchable small labels? -> description tags.
Need temporary state? -> title prefix.
```

If the required calendar does not exist and the tool cannot create calendars, ask the user to create it or provide a calendar ID. Do not silently fall back to event color when the user asked for stable cross-device color.

### 4. Draft Write Plan

For batch operations, show a compact proposal before writing unless the user has already given explicit, low-risk instructions:

```text
Date | Time | Calendar | Title | Link | Tags | Confidence | Notes
```

Proceed directly only when time, target calendar, and source are clear and duplicate checks pass.

### 5. Create Events

Create events with:

- target calendar ID
- normalized title
- start/end with timezone
- location set to the primary join/register link when useful
- description contract fields
- reminders preserved or defaulted intentionally
- `add_google_meet: false` unless the user asks to create a new Meet

If a page gives a start time but no end time, infer the smallest defensible duration from adjacent events or local precedent and mark it as inferred in the description.

### 6. Update Events

Use a diff-oriented update:

```text
Title: old -> new
Calendar: primary -> Neuromatch
Location: tracking link -> Zoom registration link
Tags: add neuroai, course
```

Preserve unrelated fields. Do not replace rich descriptions unless the normalized description includes all important source, link, and notes fields.

### 7. Move Between Calendars

Prefer a native move operation if available. If not:

1. Read full source event.
2. Create a clone in the target calendar.
3. Verify the clone exists with matching title/time/link.
4. Delete the source event only after verification.
5. Report old and new event IDs.

Preserve attendees, recurrence, reminders, transparency, location, and description unless the user asked to change them.

### 8. Delete Events

Deletion is high impact:

- Single explicit event: confirm identity by title/time before deleting.
- Batch delete: list the exact events first.
- Recurring event: require scope clarity before deleting.

## Output Style

For a completed operation, report:

- event count changed
- target calendar(s)
- any inferred durations or unresolved TBD items
- whether links came from email, source page, or calendar payload
- verification result

Keep the final answer concise. Do not paste long tracking URLs unless the user asks.

## Common Failure Modes

- Using event color for categories that must sync to Apple/iOS colors.
- Creating many tiny calendars for tags.
- Losing Zoom links by overwriting descriptions with source-only notes.
- Creating Google Meet links accidentally when the source provides Zoom.
- Updating a recurring instance as if it were a one-off event.
- Bulk writing without checking duplicates.
