# Project Board CRUD Contract

How agents add / read / update / delete Project Board items. This is the **operating
contract**; the design rationale lives in the repo's canonical
`docs/backlog/project-board-system.md`, and the executor is `scripts/board.py`. Load this
when mutating a repo's board, or when wiring board enforcement during `/project-meta init
--board`.

## Stores and their roles

| File | Role | Editable by hand? |
|---|---|---|
| `docs/backlog/items.jsonl` | **canonical** items — one JSON object per line | No — `board.py` only |
| `docs/backlog/roadmap.json` | **canonical** milestones + `_meta` (`rev`, `items_sha256`) | No — `board.py` only |
| `docs/backlog/inbox.jsonl` | append-only fuzzy **captures** (pre-promotion) | Append-only; never rewrite |
| `docs/dashboard.html` | **derived** view (CLI injects `BOARD_DATA`) | **Never** — regenerate |
| `docs/backlog/.provenance.json`, `.refine-guidance.md`, `.board.lock` | store metadata / lock | No |

## The one rule

**`scripts/board.py` is the only writer.** Never hand-edit the JSONL/JSON store or the
rendered `docs/dashboard.html`. The CLI holds `.board.lock`, writes atomically, bumps
`roadmap._meta.rev`, recomputes `items_sha256`, and re-renders the dashboard on every
mutation. A hand edit silently breaks those invariants (stale hash → `tx` fails; a clobbered
`dashboard.html` is overwritten on the next render anyway).

This rule extends to roadmap milestones and blocking decisions: use `milestone-add`,
`milestone-edit`, `decision-add`, and `decision-resolve` rather than editing `roadmap.json`
directly. Items writes go through `mutate_items`; roadmap-only writes (milestones, decisions)
go through `mutate_roadmap` — a separate atomic write path that re-stamps `items_sha256` from
the current items file without modifying it.

The dashboard is *iterated user-facing documentation*: humans read it, the store is the
source of truth, and the HTML is always reproducible from the store.

## CRUD → verb map

All verbs accept `--root <repo>` (defaults to cwd) and auto-render after a mutation.

- **Create** — `add` (direct, refined or fuzzy), or the capture ladder
  `inbox-add` → `promote` (a fuzzy capture becomes a real item). `promote` is the
  single-writer gate where a multi-instance capture first becomes mutable.
- **Read** — `list [--json] [--status|--kind|--maturity|--disposition|--version <v>]` for
  agents; `docs/dashboard.html` for humans. Read-only; never the place to mutate.
- **Update** — `refine <id>` (fuzzy → refined; set `--acceptance-shape/--rough-size/--body`),
  `move <id> <status> [--version <v>]`, `edit <id> --<field> …`, and the disposition verbs
  `defer` / `trim` / `wontfix`. Issue mirror: `mirror-linear` (dry-run/export) then record the
  returned id with `edit <id> --linear-id <LIN-…>`.
  Milestone CRUD: `milestone-add <version> --title T [--detail D] [--status todo|done]`,
  `milestone-edit <version> [--title T] [--detail D] [--status todo|done]`.
  Decision CRUD: `decision-add <version> --question Q --options "a | b" --recommendation R
  [--blocks DASH-x,DASH-y]` (omit `--blocks` to block the whole milestone),
  `decision-resolve <version> <DEC-id> --option CHOSEN --resolver WHO`.
- **Delete** — **deliberately friction-ful: there is no hard-delete verb.** Prefer a
  *disposition* (`wontfix` / `trimmed` / `defer`) so the item stays auditable. The dashboard's
  browser edit-back can splice a row out of `items.jsonl`, but the CLI stays canonical:
  after a browser save you MUST review the diff, then `board.py tx`, then `board.py
  render`. True removal = edit `items.jsonl` by hand only as last-resort surgery, immediately
  followed by `board.py tx` to re-hash and re-validate.

## Scheduling gate

`board.py` enforces a **final-state rule** on every item mutation (add, move, edit, refine,
disposition): an item whose status would become (or remain) `"scheduled"` in milestone vX is
**blocked** if vX exists with `status != "done"` AND has at least one unresolved decision
(resolution is null) whose `blocks` list is empty (whole-milestone block) or contains that item's
id.

- **Done milestones are exempt** — decisions on a `done` milestone are retro records, not gates.
- **No `--force` / bypass flag.** The only path past a gate is `decision-resolve`.
- The gate runs inside `mutate_items` (covering add/move/edit/refine/disposition/promote) and
  inside `mutate_roadmap` (covering milestone-edit that marks a milestone done while items remain
  scheduled into it via blocking decisions).
- `board.py tx` also calls the gate as a backstop, so a hand-edit that bypasses the CLI will
  fail `tx` before the turn ends.

**Recovery path**: if the store is stuck (e.g. a hand edit left it in violation), the last-resort
path is hand surgery on `docs/backlog/roadmap.json` (resolve the decision or remove the block),
immediately followed by `board.py tx` to re-hash and re-validate. `board.py tx` is the Stop-hook
check and will catch any remaining violation.

## Integrity invariants

- Every mutation is **atomic, locked, auto-rendered**, and re-stamps
  `roadmap._meta.{rev, items_sha256, updated_at}`.
- `board.py tx` validates the whole store: item schema, duplicate ids, roadmap→item
  references, and `items_sha256` freshness. Run it after *any* out-of-band change; it is also
  the Stop-hook check (see Enforcement).
- `items.jsonl` is split on `"\n"` only (never `splitlines()`), so U+2028/U+2029 and other
  separators round-trip — another reason not to hand-edit with arbitrary tools.
- `inbox.jsonl` is append-only and multi-instance-safe (`O_APPEND`, one short line < PIPE_BUF);
  concurrent captures cannot interleave. All dedup/mutation happens later at the `promote`/
  `refine` single-writer gate.

## Derived surfaces (read-only mirrors of canonical state)

- **Dashboard tabs** (roadmap / backlog / docs-wiki) render from `BOARD_DATA`; the Harness
  tab renders `BOARD_DATA.harness`, which `board.py collect_harness()` *derives* from the real
  artifacts (`.claude/settings.json`, hooks, `agents/…`, mirrors). There is no
  `.harness/settings.json` — settings are derived, never a new state file (AP-VAL-2). The
  canonical writer for harness settings is `/project-meta settings`, not the dashboard.
- **Browser edit-back** (backlog cards, harness profile write) is optional and Chromium-only.
  It patches in memory and writes the store files directly through a once-granted repo-root
  directory handle (File System Access API; the handle persists in IndexedDB, so no path
  picking after the first grant — non-Chromium falls back to patched-file downloads). The
  CLI re-renders the truth: after a browser save, review the diff, `board.py tx`, `render`.

## Enforcement (optional, profile-laddered)

`/project-meta init --board` can install the **`board-guard`** PreToolUse hook
(`templates/hooks/scripts/board-guard.sh`) and the `board.py tx` leg of the Stop hook:

- `HARNESS_PROFILE=minimal` — guards off.
- `standard` — block hand-edits to the **derived** `docs/dashboard.html` (always regenerate);
  Stop runs `board.py tx` advisory.
- `strict` — also block hand-edits to `docs/backlog/*.jsonl|*.json` (steer to `board.py`
  verbs); Stop `tx` failure blocks the turn.

This is what makes board work *fixed and stable*: the store can only move through the CLI, the
dashboard is never edited by hand, and a corrupt/stale store is caught before the turn ends.

## See also

- `docs/backlog/project-board-system.md` — canonical design (store layout, conductor doctrine).
- [`recipes/roadmap.md`](../recipes/roadmap.md) — milestone grooming; [`recipes/refine.md`](../recipes/refine.md) — fuzzy → concrete.
- [`references/linear-mirror.md`](linear-mirror.md) — push-only issue mirror.
- [`recipes/settings.md`](../recipes/settings.md) — harness settings (the Harness tab's canonical writer).
