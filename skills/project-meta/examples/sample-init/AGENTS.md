# toy-weather-cli — Agent Memory

> **Canonical entrypoint.** Primary consumer: Codex. Mirror: `CLAUDE.md`.
> Read this file first; load `agents/*.md` only for the relevant task.

## Project Scope

`toy-weather-cli` is a single-file Python CLI (`weather.py`) that fetches
current conditions from a public API. One maintainer; no CI yet.

## Memory Index

| File | Purpose | Load when |
|---|---|---|
| `agents/delegation.md` | Multi-agent delegation rules | multi-agent work |
| `agents/pre-commit-delivery.md` | Pre-commit review checklist | before any commit |

## Operating Rules

- Keep `weather.py` under 200 lines; extract helpers to `lib/` if it grows.
- All external HTTP calls go through `weather.fetch(url, timeout=10)`.
- Tests live in `tests/`; run `pytest -q` before every commit.
- Do not commit API keys; use `WEATHER_API_KEY` env var.

## Harness Profile

`HARNESS_PROFILE=minimal` — no hooks, no phase-lock, no issue-tracker wired.
