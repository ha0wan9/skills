# Citation Graph

A survey that asserts "RAFT-Stereo is the 2021 inflection point" without
showing the inheritance edges leaves the reader to reconstruct the graph
from prose. A 20-paper field has on the order of 30-60 within-survey
edges; rendered as a Mermaid diagram in §3 / §10 / §11 they make the
field's structure visible at a glance.

This skill ships a deliberately small toolchain: one TSV for edges, one
optional TSV for clusters, one renderer. Citation data outside the
survey's paper set is **out of scope** — the graph is meant to make
*indexed* relationships visible, not catalog the literature.

## Contents

- [Edge schema (`citations.tsv`)](#edge-schema)
- [Optional cluster schema (`clusters.tsv`)](#cluster-schema)
- [Four views and when to use each](#four-views)
- [Edge style mapping](#edge-style-mapping)
- [Where the graph goes in `survey.md`](#placement)
- [How to populate the TSV](#populating-the-tsv)
- [Anti-patterns](#anti-patterns)

## Edge schema

`citations.tsv` is tab-separated, header row required:

```
from	to	relation	evidence
```

| Column | Meaning |
|---|---|
| `from` | citing / extending paper (`Pxxx`) |
| `to` | cited / parent paper (`Pxxx`) |
| `relation` | one of seven values (see below) |
| `evidence` | short text pointing to where this is asserted in the citing paper, e.g. `P002 §3.1 "we extend RAFT iterative update"` |

### Relations

| Relation | Meaning | Use for |
|---|---|---|
| `extends` | direct architectural inheritance — the new paper is a successor model | spine of a route lineage |
| `same-team` | same lab / first-author cluster, but no direct inheritance | when reviewers ask about lab-clustering bias |
| `competing-route` | same problem, deliberately different design route (Transformer vs RAFT) | branching points in the timeline |
| `cites` | generic citation, no other relation type fits | only used when `--view cites` is needed for hub-paper detection |
| `critical-review-of` | citing paper specifically argues against cited paper's claims | open-challenge sections |
| `compares-against` | head-to-head experimental comparison in tables | benchmark-driven discussions |
| `dataset-target` | citing paper uses cited paper as evaluation target (typical for benchmark-introducing papers) | bridging method-papers and dataset-papers |

The validator (`scripts/citation_graph.py`) rejects any other relation.

## Cluster schema

`clusters.tsv` is optional. Same TSV style:

```
paper_id	cluster
P001	Iterative-RAFT
P002	Iterative-RAFT
P005	Foundation-VFM
```

Used only by the `lineage` view. Absent → the lineage view falls back
to a flat (no-subgraph) layout. Cluster names appear verbatim as
Mermaid subgraph titles, so prefer short labels.

A paper omitted from `clusters.tsv` renders outside any subgraph in
the lineage view — useful for one-off papers that don't fit a route.

## Four views

| View | Edges | Clustered by | Read this when |
|---|---|---|---|
| `lineage` | extends + same-team + competing-route | `clusters.tsv` (architecture / route) | tracing how the field got from RAFT to FoundationStereo |
| `cites` | cites only | flat | finding hub papers (high in-degree → "everyone cites X") |
| `critique` | critical-review-of + compares-against + dataset-target | flat | identifying which models are under attack and from where |
| `temporal` | all relations | year | seeing route-shift moments (when does the inheritance arrow change route?) |
| `all` | lineage + critique (no raw cites) | `clusters.tsv` if present | the default §3 figure |

Each view answers one question. Mixing them in one figure produces an
unreadable spaghetti graph; keep them separate.

## Edge style mapping

The renderer picks Mermaid arrows so visual semantics match relation
semantics:

| Relation | Mermaid arrow | Label |
|---|---|---|
| `extends` | `-->` solid | (none) |
| `same-team` | `-.->` dotted | `same-team` |
| `competing-route` | `==>` thick | `competing` |
| `cites` | `-->` solid | (none) |
| `critical-review-of` | `-.->` dotted | `critique` |
| `compares-against` | `-.->` dotted | `compare` |
| `dataset-target` | `-.->` dotted | `evals` |

The visual contract is: **solid = inheritance / inclusion; dotted =
external relation; thick = same-problem rivalry**.

## Placement

Recommended placements in `survey.md`:

| Section | View | Why |
|---|---|---|
| §3 Taxonomy + timeline | `lineage` (with clusters) | clusters double as the §3 primary-axis taxonomy made visual |
| §10 Open challenges | `critique` | makes the "X is under attack from {Y, Z, W}" pattern visible |
| §11 Key research teams | `lineage` (with `same-team` highlighted) or `cites` | shows lab-cluster concentration directly, complementing the §11 prose |
| Appendix or §3 alt | `temporal` | route-shift years become subgraph boundaries |

Avoid putting more than one citation graph in a single section. Two
adjacent graphs of the same view feel duplicative; two of different
views invite reader confusion about what's actually being shown.

## Populating the TSV

Three paths, in increasing rigor:

1. **PDF reading** — fastest. Read each ★★★ paper's intro / §2 (related
   work) / experimental tables. Record:
   - `extends` from "we build on / extend / are based on X" sentences
   - `compares-against` from comparison tables (Pxxx in same row as new
     model)
   - `critical-review-of` from "X fails on Y" or "we show X cannot…"
     framings (rare and high-value)
   Most surveys can produce 30-50 edges this way in 1-2 hours.

2. **Semantic Scholar API** — pull `paper/ARXIV:xxxx/references` for
   each paper, intersect with `paper_index.md` paper IDs, get the raw
   `cites` set. Then **manually upgrade** generic `cites` to the
   stronger relation when warranted. Free, ~100 req/5min rate limit.
   Stub the helper as `scripts/citation_fetch.py` if needed; not
   currently shipped because manual review is the binding step.

3. **PDF reference parsing** — last resort. Bib formats vary; expect
   30-50% noise. Only pursue if the survey is large enough (>40
   papers) that 1+2 are infeasible.

`evidence` is for your future self and for audit. When a reviewer asks
"why did you call P021 a critical review of P005?", the evidence cell
points at the paper line that justifies it.

## Anti-patterns

- **Graphs with >40 nodes**. Mermaid renders, but readers stop reading.
  Filter to ★★★ only (`--filter-stars 3`) or split into two views.
- **One graph that mixes lineage and critique**. Solid + dotted at the
  same time confuses the visual contract. Two graphs.
- **Generic `cites` for everything**. The whole point of the relation
  taxonomy is to surface structure. If most edges end up `cites`, the
  graph is just an arxiv-references dump.
- **No `evidence` column**. The relation type without evidence is just
  the surveyor's opinion; stripping evidence makes the TSV
  un-auditable. Treat empty `evidence` like an empty `quote` in
  `claims.jsonl` — never ship it.
- **Putting the graph before the prose**. The graph is a summary of
  prose, not a substitute. The §3 lineage figure should appear after
  the route taxonomy is named in text, not before.
- **Skipping `same-team` edges**. They feel boring but make
  lab-clustering visible — usually the most important non-method
  finding in §11.
