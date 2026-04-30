# Phase: synthesize

Use after evaluation to answer the research question and decide what knowledge
should persist.

## Steps

1. Read `index.md`, evaluation notes, and decision rules.
2. State the answer to the original research question in one paragraph.
3. Record:
   - confirmed findings;
   - rejected hypotheses;
   - unresolved questions;
   - reusable lessons;
   - follow-up studies that are out of scope.
4. Apply complexity and cost penalties before recommending adoption.
5. Generate or update the research graph next to `05-synthesis.md`:
   - `research_graph.mmd` for human-readable Mermaid diagrams;
   - `research_graph.json` for machine-readable graph data.
   The JSON shape is defined by `templates/research-graph.schema.json`.
6. The graph must include nodes for the study root, hypothesis tracks,
   experiments, major evidence/results, and final decisions. Use edge labels
   from: `tests`, `supports`, `contradicts`, `depends-on`, `supersedes`,
   `promotes`, `forks-from`.
7. Write or append `05-synthesis.md` with a "Research Graph" section that cites
   the graph nodes used to justify the final route choice. The winning route
   must be understandable from `index.md`, `runs.jsonl`, and the graph without
   reading every nested artifact.
8. If the result changes durable project practice, update the project's
   appropriate memory file only when the user or repo policy asks for it.

## Hand Off

Set status to `synthesized`, `closed`, or `needs-next-round`. Run `audit`
before broad adoption or when claims are important.
