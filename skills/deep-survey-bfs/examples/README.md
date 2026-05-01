# Examples

Reference runs of the `deep-survey-bfs` skill, end-to-end. Each example is a
self-contained survey directory: the same files a fresh run would produce.

| Example | Topic | Scope | Papers | Claims | Output |
|---|---|---|---|---|---|
| [`stereo-matching-edge-fm/`](stereo-matching-edge-fm/) | Stereo matching for edge devices and foundation models | 2020-2026 | 26 indexed (18 ★★★) | 67 | [`artifacts/survey.html`](stereo-matching-edge-fm/artifacts/survey.html) (99 KB single-file interactive) |

Examples serve three purposes:

1. **Smoke tests** for the skill's scripts (`claims_validate.py`,
   `bias_audit.py`, `citation_graph.py`, `synthesize_self_check.py`,
   `render_html.py`). Every script in `scripts/` should produce sensible
   output against every example here.
2. **Pattern templates** — the schema of `paper_index.md`, the prose tone
   of `survey.md`, the relation taxonomy in `citations.tsv` are easier to
   imitate than to derive from `references/`.
3. **Regression catches** — when the skill evolves, examples re-render to
   confirm the change didn't break shape.

Examples are point-in-time snapshots. The underlying literature keeps moving
(new papers land, repos change, leaderboards update). Re-render rather than
edit by hand if you want a current view of any topic.
