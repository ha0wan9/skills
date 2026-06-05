# Proposal — Persistent per-project `dashboard.html` + Plan dual-publish

- **Status:** proposal (2026-06-05).
- **Applies to:** the `project-meta` skill — `plan` + `init` recipes.
- **Tracked:** Linear `hw-skills/ARK-52` (project "hw-skills"). Repo is the source of truth; Linear summarizes + links back.
- **Reference implementation:** ArkDisplay `public/dashboard.html` (the "ArkOS System Dossier" — a self-contained static HTML with embedded data arrays, served at `/dashboard.html`).

## Idea

Every project that uses this skill carries a **persistent, interactive `dashboard.html`**, and `/project-meta plan` publishes a plan's task content to **two synced surfaces**:

1. **Linear** — issues (as today).
2. The project's **`dashboard.html`** — continuously updated by subsequent workflows (updated in place, not regenerated from scratch each run).

So the operator gets a durable, self-explaining project surface — not just a Linear list — that they can open and read at a glance.

## Why

The operator wants an at-a-glance, interactive grasp of a project that a Linear list does not give: live **progress**, the current **persistent-state explanation** (what the system *is* right now and why), **branch purposes & usage** (what each branch is for, its status), and **roles** (agents/owners). Keeping it a committed artifact in the repo (the source of truth) means it survives, diffs, and is served live.

## The dashboard contract (required sections)

A conforming `dashboard.html` must cover, at minimum:

- **Progress** — phased roadmap / task state (done · now · todo), like the ArkDisplay `ROAD` array.
- **Persistent-state explanation** — what the system currently is: subsystems, data/persistence model, the "honest read" (strengths/weaknesses), API/contract surface.
- **Branches** — each active branch's purpose + status (what it's for, what's landed, what's pending).
- **Roles** — agents/owners and who governs/serves what.

It is a **derived view** over repo state, self-contained (no build step required to open), and incrementally updated.

## Integration with `project-meta`

- **`init`** — bootstrap a `dashboard.html` into the project from a template (`templates/dashboard.html`), parameterized with the project name + initial sections. Make it a per-project standard.
- **`plan`** — after writing Linear issues, write/refresh `dashboard.html` with the same task content (the Progress section), so Linear and the dashboard stay in sync.
- **subsequent workflows** — update the relevant section in place as state changes (branch lands, role added, phase flips), rather than regenerating the whole file.
- Surface it in **`status`/`deliver`** where relevant.

## Scope (mirrors `hw-skills/ARK-52`)

- (a) `plan` flow writes/refreshes `dashboard.html` alongside the Linear publish.
- (b) Define + ship the dashboard contract (the four sections above) as a template.
- (c) Per-project standard, bootstrapped on `init`.
- (d) Subsequent workflows update it incrementally (a durable, append-friendly format).

## Open questions

- **Template shape** — one `templates/dashboard.html` with placeholder data arrays vs. a small generator that reads a project manifest. The ArkDisplay dossier hand-rolls embedded JS arrays (`CARDS`/`ROUTES`/`ROAD`/`SKILLS`); a template could expose just those arrays as the edit surface.
- **Update mechanism** — how "continuously updated by workflows" is enforced: a `plan`/`deliver` step that patches the data arrays, vs. a dedicated recipe (`/project-meta dashboard`).
- **Source-of-truth boundary** — repo state → `dashboard.html` (derived) → Linear (summarizes + links back). Avoid three diverging copies.
- **Cross-runtime** — must stay dependency-free static HTML so it opens anywhere (Claude Code · Codex · OpenClaw), consistent with the skill's runtime support.
