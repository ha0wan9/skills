#!/usr/bin/env python3
"""Build a sub-question x dimension coverage matrix from paper_index.md and index.md.

Reads:
  - paper_index.md  (Markdown table; column "Sub-questions" comma-sep SQ ids,
                     "Dimensions" comma-sep dim names, "Stars" with star chars)
  - index.md        (parses the "## Sub-Questions" section and the "## Active
                     Evidence Dimensions" table)

Prints a coverage matrix to stdout and exits 0 if all active cells have at
least one star-three paper, else exits 1.

Usage:
  python3 coverage_check.py <paper_index.md> <index.md>
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


DIMENSIONS = ["theory", "experiment", "survey", "critical-review", "dataset"]


def parse_subquestions(index_text: str) -> list[str]:
    """Extract SQ ids from the '## Sub-Questions' section.

    Handles all of these list-item shapes:
        1. SQ1 — ...
        1. **SQ1** — ...
        1. **SQ1**: ...
        - SQ1: ...
        * **SQ1** ...
    The regex tolerates optional leading bullet (digit. or - or *) and
    optional surrounding markdown bold (**...**).
    """
    m = re.search(r"## Sub-Questions\s*\n(.*?)(?=\n## )", index_text, re.S)
    if not m:
        return []
    pattern = re.compile(
        r"^\s*(?:\d+\.|[-*])\s+\*{0,2}(SQ\d+)\*{0,2}\b"
    )
    out: list[str] = []
    for line in m.group(1).splitlines():
        hit = pattern.match(line)
        if hit:
            out.append(hit.group(1))
    return out


def parse_active_dims(index_text: str) -> dict[str, set[str]]:
    """Return SQ -> set of active dimensions, parsed from the markdown table.

    Tolerates `**SQ1**` markdown-bold cells.
    """
    m = re.search(
        r"## Active Evidence Dimensions\s*\n(.*?)(?=\n## )",
        index_text,
        re.S,
    )
    if not m:
        return {}
    active: dict[str, set[str]] = {}
    header = None
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            if cells[0].lower().startswith("sub-question"):
                header = [c.lower() for c in cells[1:]]
            continue
        if cells[0].startswith("---"):
            continue
        sq = re.sub(r"\*+", "", cells[0]).strip()
        dims = set()
        for i, dim_name in enumerate(header):
            value = cells[i + 1] if i + 1 < len(cells) else ""
            if value and value not in {"-", "—"}:
                dims.add(dim_name)
        if sq:
            active[sq] = dims
    return active


def parse_paper_rows(idx_text: str) -> list[dict]:
    """Each tr is a paper row from paper_index.md."""
    rows: list[dict] = []
    header_cells = None
    for raw in idx_text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header_cells is None:
            if cells[0].lower() == "id":
                header_cells = [c.lower() for c in cells]
            continue
        if cells[0].startswith("---"):
            continue
        if not cells[0].startswith("P"):
            continue
        row = dict(zip(header_cells, cells))
        rows.append(row)
    return rows


def is_starstarstar(value: str) -> bool:
    # Count star characters; ★ is U+2605
    return value.count("★") >= 3


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paper_index_md", metavar="paper_index.md",
                        help="Path to paper_index.md")
    parser.add_argument("index_md", metavar="index.md",
                        help="Path to index.md")
    args = parser.parse_args(argv[1:])

    pi_path = Path(args.paper_index_md)
    idx_path = Path(args.index_md)
    if not pi_path.is_file() or not idx_path.is_file():
        print("input files do not exist", file=sys.stderr)
        return 2

    pi_text = pi_path.read_text(encoding="utf-8")
    idx_text = idx_path.read_text(encoding="utf-8")

    sqs = parse_subquestions(idx_text)
    active = parse_active_dims(idx_text)
    rows = parse_paper_rows(pi_text)

    # cell[(sq, dim)] = list of paper ids
    cell: dict[tuple[str, str], list[str]] = defaultdict(list)
    # paper_meta[id] = (normalized_institution, year_int_or_None) — used for
    # the weak-cell scan (single-lab / single-year concentration).
    paper_meta: dict[str, tuple[str, int | None]] = {}
    for r in rows:
        if not is_starstarstar(r.get("stars", "")):
            continue
        paper_id = r.get("id", "").strip()
        inst_raw = ""
        for k in ("inst", "institution", "affiliation", "lab"):
            if r.get(k):
                inst_raw = r[k]
                break
        inst_norm = re.sub(r"\s*\([^)]*\)\s*$", "", inst_raw).strip().lower()
        ymatch = re.search(r"(19|20)\d{2}", r.get("year", ""))
        paper_meta[paper_id] = (inst_norm, int(ymatch.group(0)) if ymatch else None)
        sqs_in = [s.strip() for s in r.get("sub-questions", "").split(",") if s.strip()]
        dims_in = [d.strip().lower() for d in r.get("dimensions", "").split(",") if d.strip()]
        for sq in sqs_in:
            for dim in dims_in:
                cell[(sq, dim)].append(paper_id)

    # render
    print(f"Survey coverage matrix\n  sub-questions: {len(sqs)}  papers (★★★): "
          f"{sum(1 for r in rows if is_starstarstar(r.get('stars','')))}\n")
    header = ["SQ"] + DIMENSIONS
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    open_cells = 0
    closed_cells = 0
    closed_keys: list[tuple[str, str]] = []
    for sq in sqs:
        row = [sq]
        active_dims = active.get(sq, set(DIMENSIONS))
        for dim in DIMENSIONS:
            if dim not in active_dims:
                row.append("N/A")
                continue
            papers = cell.get((sq, dim), [])
            if not papers:
                row.append("**GAP**")
                open_cells += 1
            else:
                row.append(", ".join(papers))
                closed_cells += 1
                closed_keys.append((sq, dim))
        print("| " + " | ".join(row) + " |")

    print(f"\nclosed: {closed_cells}  gap: {open_cells}")

    # Weak-cell scan: a cell can be "closed" yet rest on a single source.
    # The gap audit treats these as `weak` (see references/coverage-matrix.md
    # and bias-audit.md). We surface them here so they don't pass silently:
    #   - single ★★★ paper            -> single-source
    #   - all ★★★ from one institution -> single-lab
    #   - >=3 ★★★ within a 1-year span -> recency-cluster
    # This is advisory and does NOT change the exit code (only true gaps do);
    # the survey author decides whether to harden via a weak-cell Round/version.
    weak: list[str] = []
    for (sq, dim) in closed_keys:
        ids = cell[(sq, dim)]
        insts = {paper_meta.get(i, ("", None))[0] for i in ids if paper_meta.get(i, ("", None))[0]}
        years = sorted(y for i in ids for y in [paper_meta.get(i, ("", None))[1]] if y is not None)
        if len(ids) == 1:
            weak.append(f"{sq}/{dim}: single-source ({ids[0]})")
        elif len(insts) == 1:
            weak.append(f"{sq}/{dim}: single-lab ({next(iter(insts))!r}; {', '.join(ids)})")
        elif len(years) >= 3 and (years[-1] - years[0]) <= 1:
            weak.append(f"{sq}/{dim}: recency-cluster (all {years[0]}–{years[-1]}; {', '.join(ids)})")

    if weak:
        print(f"\nweak cells (closed but concentrated): {len(weak)}")
        for w in weak:
            print(f"  - {w}")
        print("  -> consider a weak-cell hardening pass (a `version` round): add "
              "a ≥1 paper from a different lab/year, or accept+document the "
              "concentration in coverage_matrix.md.")
    else:
        print("\nweak cells: 0 (every closed cell draws on >1 lab)")

    return 0 if open_cells == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
