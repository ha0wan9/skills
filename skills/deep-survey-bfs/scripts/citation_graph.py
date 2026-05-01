#!/usr/bin/env python3
"""Render paper-to-paper citation edges as a Mermaid graph.

Reads citations.tsv (edge list) + paper_index.md (node metadata) +
optional clusters.tsv (for subgraph grouping) and emits a fenced
``mermaid`` block for one of four views:

    lineage   — extends / same-team / competing-route edges
                clusters by `clusters.tsv` (architecture or route)
    cites     — raw `cites` edges only; useful for hub-paper detection
    critique  — critical-review-of / compares-against / dataset-target
    temporal  — every edge, clustered by year

Usage:
    python3 citation_graph.py CITATIONS PAPER_INDEX [--clusters CLUSTERS]
                              [--view {lineage,cites,critique,temporal,all}]
                              [--filter-stars N]
                              [--orientation {LR,TD}]

Examples:
    # Lineage diagram restricted to ★★★ papers
    python3 citation_graph.py citations.tsv paper_index.md \\
        --clusters clusters.tsv --view lineage --filter-stars 3

    # Critical-review network for §10
    python3 citation_graph.py citations.tsv paper_index.md --view critique

Exit codes:
    0  success; mermaid block on stdout
    1  validation error (unknown relation, missing paper_id)
    2  bad CLI usage / file missing
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


KNOWN_RELATIONS = {
    "extends",
    "same-team",
    "competing-route",
    "cites",
    "critical-review-of",
    "compares-against",
    "dataset-target",
}

VIEW_RELATIONS = {
    "lineage": {"extends", "same-team", "competing-route"},
    "cites": {"cites"},
    "critique": {"critical-review-of", "compares-against", "dataset-target"},
    "temporal": KNOWN_RELATIONS,
    "all": KNOWN_RELATIONS - {"cites"},  # exclude raw cites to avoid clutter
}

# (arrow, label) — None label means no label
EDGE_STYLE = {
    "extends": ("-->", None),
    "same-team": ("-.->", "same-team"),
    "competing-route": ("==>", "competing"),
    "cites": ("-->", None),
    "critical-review-of": ("-.->", "critique"),
    "compares-against": ("-.->", "compare"),
    "dataset-target": ("-.->", "evals"),
}


def parse_paper_index(path: Path) -> dict[str, dict]:
    """Return {paper_id: {title, year, venue, stars}}."""
    text = path.read_text(encoding="utf-8")
    papers: dict[str, dict] = {}
    header: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            if cells and cells[0].lower() == "id":
                header = [c.lower() for c in cells]
            continue
        if cells and cells[0].startswith("---"):
            continue
        if not cells or not re.match(r"^P\d{3,5}$", cells[0]):
            continue
        row = dict(zip(header, cells))
        pid = cells[0]
        title = row.get("title (short)") or row.get("title") or pid
        # Strip trailing parens / formatting noise
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
        # Truncate very long titles for graph readability
        if len(title) > 28:
            title = title[:25].rstrip() + "…"
        papers[pid] = {
            "title": title,
            "year": row.get("year", "?"),
            "venue": row.get("venue", "?"),
            "stars": row.get("stars", ""),
        }
    return papers


def parse_tsv(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            rows.append(line.split("\t"))
    return rows


def parse_citations(path: Path) -> list[dict]:
    rows = parse_tsv(path)
    if not rows:
        return []
    header = [c.strip().lower() for c in rows[0]]
    expected = ["from", "to", "relation", "evidence"]
    if header[: len(expected)] != expected:
        sys.stderr.write(
            f"citations.tsv: header must be {expected!r}, got {header!r}\n"
        )
        sys.exit(1)
    edges: list[dict] = []
    for line_no, cells in enumerate(rows[1:], start=2):
        if len(cells) < 3:
            continue
        edges.append(
            {
                "from": cells[0].strip(),
                "to": cells[1].strip(),
                "relation": cells[2].strip(),
                "evidence": cells[3].strip() if len(cells) > 3 else "",
                "_line": line_no,
            }
        )
    return edges


def parse_clusters(path: Path) -> dict[str, str]:
    rows = parse_tsv(path)
    if not rows:
        return {}
    header = [c.strip().lower() for c in rows[0]]
    if header[:2] != ["paper_id", "cluster"]:
        sys.stderr.write(
            f"clusters.tsv: header must be ['paper_id', 'cluster'], got {header!r}\n"
        )
        sys.exit(1)
    out: dict[str, str] = {}
    for cells in rows[1:]:
        if len(cells) < 2:
            continue
        out[cells[0].strip()] = cells[1].strip()
    return out


def stars_count(value: str) -> int:
    return value.count("★")


def node_label(pid: str, papers: dict[str, dict]) -> str:
    info = papers.get(pid, {})
    title = info.get("title", pid)
    year = info.get("year", "?")
    venue = info.get("venue", "")
    venue_short = re.sub(r"\s+\d{4}$", "", venue).strip()  # strip trailing year
    line2 = f"{year}" + (f" {venue_short}" if venue_short and venue_short != "preprint" else "")
    return f'{pid}["{pid} {title}<br/>{line2}"]'


def render_mermaid(
    edges: list[dict],
    papers: dict[str, dict],
    clusters: dict[str, str],
    view: str,
    orientation: str,
    filter_stars: int,
) -> str:
    allowed = VIEW_RELATIONS[view]
    edges = [e for e in edges if e["relation"] in allowed]

    if filter_stars > 0:
        keep = {pid for pid, info in papers.items() if stars_count(info["stars"]) >= filter_stars}
        edges = [e for e in edges if e["from"] in keep and e["to"] in keep]
    else:
        keep = set(papers.keys())

    # Nodes that actually appear in surviving edges
    nodes: set[str] = set()
    for e in edges:
        nodes.add(e["from"])
        nodes.add(e["to"])
    if not nodes:
        return f"%% no edges to render for view={view!r} (filter-stars={filter_stars})"

    lines: list[str] = [f"graph {orientation}"]

    # Subgraph layout
    if view == "temporal":
        # group by year
        buckets: dict[str, list[str]] = defaultdict(list)
        for pid in sorted(nodes):
            buckets[papers.get(pid, {}).get("year", "?")].append(pid)
        for year in sorted(buckets):
            lines.append(f'  subgraph y{year}["{year}"]')
            for pid in buckets[year]:
                lines.append(f"    {node_label(pid, papers)}")
            lines.append("  end")
    elif view == "lineage" and clusters:
        buckets = defaultdict(list)
        unclustered: list[str] = []
        for pid in sorted(nodes):
            cl = clusters.get(pid)
            if cl:
                buckets[cl].append(pid)
            else:
                unclustered.append(pid)
        for cl in sorted(buckets):
            slug = re.sub(r"\W+", "_", cl).strip("_") or "g"
            lines.append(f'  subgraph {slug}["{cl}"]')
            for pid in buckets[cl]:
                lines.append(f"    {node_label(pid, papers)}")
            lines.append("  end")
        for pid in unclustered:
            lines.append(f"  {node_label(pid, papers)}")
    else:
        for pid in sorted(nodes):
            lines.append(f"  {node_label(pid, papers)}")

    # Edges
    for e in edges:
        arrow, label = EDGE_STYLE[e["relation"]]
        if label:
            lines.append(f"  {e['from']} {arrow}|{label}| {e['to']}")
        else:
            lines.append(f"  {e['from']} {arrow} {e['to']}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=__doc__)
    parser.add_argument("citations", type=Path)
    parser.add_argument("paper_index", type=Path)
    parser.add_argument("--clusters", type=Path, default=None,
                        help="Optional clusters.tsv for lineage subgraphs.")
    parser.add_argument("--view",
                        choices=sorted(VIEW_RELATIONS.keys()),
                        default="lineage")
    parser.add_argument("--filter-stars", type=int, default=0,
                        help="Drop papers with fewer than N stars (default 0 = no filter).")
    parser.add_argument("--orientation", choices=["LR", "TD"], default="LR")
    parser.add_argument("--bare", action="store_true",
                        help="Print only graph syntax without ```mermaid fence.")
    args = parser.parse_args(argv)

    for required in (args.citations, args.paper_index):
        if not required.is_file():
            print(f"missing: {required}", file=sys.stderr)
            return 2

    papers = parse_paper_index(args.paper_index)
    edges = parse_citations(args.citations)
    clusters = parse_clusters(args.clusters) if args.clusters else {}

    # Validate
    errors: list[str] = []
    for e in edges:
        if e["relation"] not in KNOWN_RELATIONS:
            errors.append(
                f"line {e['_line']}: unknown relation {e['relation']!r} "
                f"(known: {sorted(KNOWN_RELATIONS)})"
            )
        for end in ("from", "to"):
            if e[end] not in papers:
                errors.append(
                    f"line {e['_line']}: paper_id {e[end]!r} not in paper_index.md"
                )
    if errors:
        for err in errors:
            sys.stderr.write(err + "\n")
        return 1

    body = render_mermaid(
        edges=edges,
        papers=papers,
        clusters=clusters,
        view=args.view,
        orientation=args.orientation,
        filter_stars=args.filter_stars,
    )

    if args.bare:
        print(body)
    else:
        print("```mermaid")
        print(body)
        print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())
