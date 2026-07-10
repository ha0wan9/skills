# Recipe: refine

Promote a **fuzzy** backlog item into a roadmap-eligible **refined** requirement (DASH-23).
Item-level (scope + acceptance-shape + rough size) — distinct from `plan`, which is
milestone-level. Usually invoked as the item-prep step inside a `roadmap` grooming session,
but runnable on its own.

> **Stability: provisional.** New in Project Board v0.2. Not a core route-table verb — load
> this recipe from `roadmap`, or run the `board.py` steps directly. Promote to a standalone
> verb only on demonstrated demand (DASH-17 "don't bloat the core verb set").

## When to load

- Grooming captured/fuzzy items before a roadmap session.
- A `roadmap` session needs an item made concrete before it can be versioned.

## Mode

**editing** — mutates an item's `maturity` and fields via `scripts/board.py`. The
`fuzzy → refined` promotion is **operator-confirmed** (async-draft / deliberate-promote) so
it cannot drift from intent.

## Required references

**Base** — loaded when the verb runs:

- [`references/cli-command-patterns.md`](../references/cli-command-patterns.md) — shared command rules, including **deliver before commit** for editing recipes.

**Lazy-load** — only when the named step needs it:

- [`references/review-tier.md`](../references/review-tier.md) — step 5: optional **L1** check (is the refined item well-formed / testable?) (load only here)

## Workflow

1. **Get the item into `items.jsonl`.** If the idea is still a capture in `inbox.jsonl`,
   bridge it first: `python3 scripts/board.py promote <inbox-id> --root <repo>` (moves it in
   as `fuzzy`, drains the inbox row — the single-writer gate, DASH-24).
2. **Read the guidance.** Load `docs/backlog/.refine-guidance.md` — the lessons distilled from
   prior DASH-08 co-reviews (current direction, acceptance-shape patterns that passed, recurring
   trim/staleness reasons). This sharpens the draft. (Guidance lives here, **not** in
   `repo_memory` — that is a 30-item-capped entry-point CLI, not a queryable index.)
3. **Draft (fleet-tier sub-agent).** Dispatch a fleet-tier sub-agent (Claude: Sonnet; Codex: Luna) to draft the concrete requirement:
   **scope · acceptance-shape · rough size**. It must **ask the operator** wherever ambiguous —
   never invent missing intent.
4. **Confirm + apply.** On operator confirmation, apply:
   `python3 scripts/board.py refine <id> --acceptance-shape "<...>" --rough-size "<S|M|L>" [--body "<...>"]`
   (sets `maturity: refined`, re-renders the dashboard).
5. **Optional L1 review.** For a non-trivial requirement, one fresh fleet-tier reviewer checks it is
   well-formed and testable before it enters the roadmap pool.

## Output contract

The item advances `fuzzy → refined` with a concrete scope, acceptance-shape, and rough size;
the dashboard is re-rendered. Only `maturity: refined` + `disposition: active` items are
roadmap-eligible. As an editing recipe, the resulting board change is a shared, user-facing
artifact — **deliver it for operator review before any `git commit`** (pre-commit delivery,
per `references/cli-command-patterns.md`).

## Anti-patterns

- **Auto-promoting** `fuzzy → refined` without operator confirmation (intent drift).
- **Refining at capture time** — capture is append-only and multi-instance (DASH-24); all
  mutation of existing rows happens here, at the single-writer gate.
- **Storing guidance in `repo_memory`** (capped) instead of `.refine-guidance.md`.
- **Treating `refine` as a standalone route-table verb** — load it from `roadmap` or run the
  `board.py` steps directly until DASH-17 promotes it on demonstrated demand.
- **Confusing `board.py promote` with the reserved `/project-meta promote`** — they are
  unrelated: `board.py promote` moves an inbox capture into `items.jsonl`; the reserved
  `/project-meta promote` (memory layer) is a different, unbuilt concept.
