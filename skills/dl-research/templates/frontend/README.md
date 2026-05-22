# Front-end template (`report.html` + `research_server.py`)

A single self-contained HTML report skeleton (no build step, two CDN deps:
Plotly + Mermaid) and a stdlib HTTP host. Together they give every
`dl-research` study an interactive owner-facing dashboard:

- 9-phase sticky flow bar + scroll-spy
- Fixed left TOC with phase status badges
- Right comment rail (≥ 1500 px viewport) with localStorage persistence,
  JSON export/import, and a `/claude` flag for routing comments to a
  follow-up agent run
- Live goals-tracker block (`/<study-id>/api/objectives/latest`) that
  gracefully degrades when no snapshot exists
- Dark / light theme that re-renders Plotly + Mermaid on toggle
- Three example Plotly charts and one Mermaid diagram, wired to the
  selectors the rest of the report uses

The template is **chrome and shape only** — no project, company, or
metric is referenced in the markup. Placeholders use angle brackets
(`<study-id>`, `<metric-name>`), matching the convention used by the
other templates in this skill.

## Files

| Path | Role |
|---|---|
| `templates/frontend/report.html` | Per-study report skeleton — copy to `agents/research/<study-id>/report.html` and fill in |
| `scripts/research_server.py` | Stdlib HTTP host — copy to `scripts/research_server.py` in the target repo |
| `templates/frontend/README.md` | This file |

## Instantiating a new study report

```bash
# from the target repo root
mkdir -p agents/research/<study-id>
cp <skill-root>/templates/frontend/report.html agents/research/<study-id>/report.html

# search-and-replace the placeholders that live in the markup
sed -i 's|<study-id>|my-study|g; s|<study-title>|My Study Title|g; \
        s|<repo-name>|my-repo|g; s|<status>|drafted|g; \
        s|<YYYY-MM-DD>|'"$(date -u +%F)"'|g' \
       agents/research/<study-id>/report.html
```

Then fill in the per-section placeholders (`<metric-name>`,
`<baseline-run-id>`, etc.) and replace the example Plotly data arrays
(`ANATOMY`, `PRIOR_RUNS`, `HMATRIX`) with measured numbers as they land.

## Running the server

```bash
# from the target repo root
python scripts/research_server.py --port 8765
# open http://127.0.0.1:8765/
```

The landing page reads `agents/research/_registry.json` if present, or
walks `agents/research/*/adapter.yaml` otherwise. Each study card links
to `/<study-id>/`, which serves that study's `report.html`.

To expose to LAN reviewers (read-only):

```bash
python scripts/research_server.py --bind 0.0.0.0 --port 8765
```

The server is read-only. Loopback connections are tagged `owner`;
everything else is `guest`. The HTML treats `/claude`-flagged comments
as a routing hint — comments live in browser localStorage and must be
exported as JSON to leave the client.

## Optional: live goals tracker

`report.html` fetches `/<study-id>/api/objectives/latest`, which the
server reads as the last line of
`agents/research/<study-id>/objectives/snapshots.jsonl`. When the file
is missing the UI shows a "start the server / generate a snapshot"
hint instead of erroring.

Each snapshot is one JSON object per line. Minimal schema:

```json
{
  "id": "obj-2026-05-13-0001",
  "captured_utc": "2026-05-13T15:50Z",
  "triggered_by": "manual_refresh",
  "study_id": "<study-id>",
  "goal_states": [
    {
      "goal_id": "g-latency",
      "type": "gate",
      "title": "Latency ceiling",
      "status": "pending",
      "target": 25.3,
      "target_unit": "ms",
      "leader_variant": null,
      "leader_value": null,
      "headroom": null,
      "reason": "no Wave-2 candidates yet"
    },
    {
      "goal_id": "g-wave1",
      "type": "milestone",
      "title": "Wave 1 probes complete",
      "status": "in_progress",
      "progress_pct": 25,
      "progress_label": "2 / 8 probes finished",
      "due_date_utc": "2026-05-20T00:00Z"
    },
    {
      "goal_id": "g-promote",
      "type": "exit_criterion",
      "title": "Promotable to RCnext",
      "status": "pending",
      "conditions_met": 0,
      "conditions_total": 4
    }
  ],
  "recommended_next_move": {
    "rule_id": "r-wave1-001",
    "headline": "Run remaining 6 Wave-1 probes before scheduling Wave 2."
  }
}
```

The three goal types (`gate`, `milestone`, `exit_criterion`) drive the
three columns of the tracker block. Status values
(`pass`, `achieved`, `in_progress`, `blocked`, `pending`, `fail`, `na`)
map to chip colours via CSS classes.

Generating snapshots is project-specific — the skill ships the renderer,
not the aggregator. A reasonable pattern is a small Python script that
reads a per-study `goals.yaml` + `rules.yaml`, evaluates declared
predicates against ledger / artifact state, and appends one
`snapshots.jsonl` line. The renderer treats the file as append-only,
read-only.

## Files this template assumes per study

The report links / fetches the following files under
`agents/research/<study-id>/`. None are required for the chrome itself
to render, but the deeper UX expects them:

| Path | Used by |
|---|---|
| `adapter.yaml` | linked from the Sources block |
| `index.md` | linked from the Sources block + footer |
| `runs.jsonl` | linked from Sources; ledger for Prepare / Launch |
| `research_graph.mmd` / `.json` | Synthesize phase + audit |
| `objectives/snapshots.jsonl` | goals tracker (optional) |

## Customising the chrome

The CSS theming layer is driven by CSS variables defined in `:root`
and overridden by `body.light`. To change the accent colour, edit
`--accent` + `--accent-dim` in both blocks. To add a new chart, append
a `<div class="chart" id="chart-<name>" style="height: NNNpx;"></div>`
where it belongs, write a `render<Name>()` function in the bottom
`<script>` block, and call it from `rerenderCharts()` so the theme
toggle picks it up.

The comment rail is keyed by the page filename (one localStorage bucket
per HTML file); two studies cannot accidentally cross-contaminate.
Comments are not synced to the server — export the JSON if they matter.
