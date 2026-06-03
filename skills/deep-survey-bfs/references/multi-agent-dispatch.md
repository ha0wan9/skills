# Multi-Agent Dispatch

How this survey fans out search work across subagents and gates synthesis with
an independent reviewer. Load during `round1` / `roundn` (search fan-out) and
`synthesize` (the claims-adversary gate).

## Dependency & Canon

This dispatch is a domain **specialization** of the canonical Task Dispatch
paradigm owned by **project-meta** (the upstream/root skill):
`project-meta/references/multi-agent-protocols.md`. This skill **declares
project-meta as a dependency**. The section below is a self-contained *floor* so
the skill works if installed alone; project-meta is canonical — on any conflict,
defer to it. (This is the single place the canon path appears; cite the paradigm
by name elsewhere.)

**Floor (works without project-meta installed):**

- **Roles**: Lead (orchestrator, owns source of truth) · Explorer (read-only) ·
  Worker (bounded artifact) · Reviewer (independent check).
- **Context Package** = the fields of the [Delegation Template](#delegation-template):
  goal, read-first, ownership, constraints, output format, review criteria.
- **Reviewer-Between-Subtasks**: brief a fresh worker → a fresh, separate
  reviewer returns a verdict → lead integrates; lead does not edit inside a
  dispatched chain; rotate reviewers.
- **Ordering barrier**: parallelize only across disjoint write-sets; the shared
  write (`paper_index.md`) is a lead-owned barriered step — see
  [Ordering Barrier](#ordering-barrier).
- **Synchronous gates**: a reviewer `block` is a hard STOP-and-return — see
  [Synchronous Gates](#synchronous-gates).

## Role Mapping (paradigm → deep-survey-bfs)

| Paradigm role | deep-survey-bfs role |
|---|---|
| Lead | the survey lead — owns `paper_index.md` IDs, `coverage_matrix.md`, `claims.jsonl`, `survey.md`, and the final answer |
| Explorer / Worker | a **per-cluster search subagent** — searches its assigned sub-questions, scores candidates, returns rows; **never writes `paper_index.md`** |
| Reviewer | the managed `claims-adversary` agent (`agents/claims-adversary.md`) |

The Lead is the only role that assigns paper IDs and writes shared artifacts.
Search subagents are read-only over the index: they *propose* rows, they do not
*commit* them.

## Delegation Template (search subagent)

```text
Role: Explorer/Worker — search subagent
Goal: find + score papers for sub-question cluster <SQ ids>
Read first:
- references/paper-rating-rubric.md   (so scores are comparable across agents)
- references/arxiv-query-patterns.md  (ti:-anchored queries, not all:)
- references/source-coverage.md       (per-source query recipes)
Ownership: read-only — return candidate rows; the lead assigns P-IDs and commits
Constraints:
- score on the SAME 4-dimension rubric every other agent uses
- verify venue/year/author against a primary source; resolve the preprint trap
- do not accept title-only hits
Output format: candidate rows (arXiv id, title, author+institution, year, venue,
  SQs covered, dimensions covered) + a proposed 4-dimension score per paper
Review criteria:
- every returned row has verified metadata and a scope-fit justification
- no title-only inclusions; preprint-vs-published status resolved
```

## Runtime Backings

One contract, per-runtime mechanical backing — behaviorally equivalent, never a
replacement for the prose loop.

| Tier | Claude Code | Codex | Floor |
|---|---|---|---|
| Model-driven dispatch | Agent tool / subagents | native subagents — search agents on a read-only `explorer` base | prose: dispatch one cluster at a time |
| Scripted orchestration | Workflow `parallel()` + barrier | Agents SDK + `codex mcp` (handoffs/gating) | prose: sequential per-cluster search, then manual dedup |

- **Model**: search subagents and the reviewer default to **Sonnet**; escalate a
  single agent to Opus only on a concrete signal (it already returned
  low-quality output at Sonnet tier), not precautionarily.
- The barrier below is mandatory **on every tier**, including the prose floor —
  a scripted `parallel()` does not remove the need for central dedup; it makes a
  missing barrier *more* dangerous.

## Ordering Barrier

This is the centerpiece of survey fan-out and a direct instance of the
paradigm's canonical→barrier→mirror rule. `paper_index.md` is the **single
shared write-set**; independent agents *will* surface the same paper under
different clusters, so the index write must be barriered and lead-owned:

```
parallel search fan-out (3–5 cluster agents, read-only)
        │
     ── barrier ──            ← all agents return before any index write
        │
central dedup/merge           ← merge duplicates into ONE row, UNION the
        │                       SQ + dimension tags
score once, centrally         ← one star rating per paper, after dedup
        │
single lead-owned write       ← lead assigns P-IDs and commits paper_index.md
```

- **Skipping the barrier double-counts papers** and silently inflates the bias
  audit (same lab/paper counted twice). The merge is not optional.
- **Worktree isolation makes this worse, not safer**: isolated agents that each
  append to their own `paper_index.md` produce duplicate P-IDs with no merge
  conflict to signal the violation — exactly the failure the paradigm warns
  about for mirror renders. Keep the index write central.
- Round N fan-out obeys the same barrier: merge new hits into existing P-IDs
  (union the SQ/dimension tags) before appending — never a second row for an
  already-indexed paper.

## Synchronous Gates

- **`claims-adversary` `block` (during `synthesize`)** is the paradigm's
  BLOCKER: a hard STOP before `survey.md` ships. The lead fixes the flagged
  claims (add a backing row, fix the quote, mark N/A, drop the hedge, split the
  aggregation) and re-runs the reviewer; it does **not** ship a survey over an
  open `block`. Under a scripted/background backing, stop on the first `block`
  and return; resume = re-entry after the fix, never running past it.
- **Round-cap scope amendment** is a human gate: if gaps cannot be filled within
  the framed scope after the 4-round cap, escalate to the user (accept the gap
  as a limitation or amend the scope in `index.md`) — a background runner does
  not silently widen scope.

## Reviewer Discipline

- The reviewer is **fresh and separate** from the lead's synthesis context, and
  judges only the supplied artifacts (`survey.md`, `claims.jsonl`,
  `paper_index.md`, cited PDFs) — see `agents/claims-adversary.md`.
- **Lead does not edit inside a dispatched chain** beyond integrating returned
  rows / applying reviewer-driven corrections; search agents propose, the lead
  commits.
- Rotate reviewers across re-runs so a reviewer stays naïve to the prior pass.
