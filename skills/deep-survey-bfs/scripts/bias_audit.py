#!/usr/bin/env python3
"""Run the bias audit on the star-three subset of paper_index.md.

Counts ★★★ paper distribution along institution / country (inferred from
institution column when possible) / year / venue type, and flags any
single bucket exceeding the threshold.

Usage:
  python3 bias_audit.py <paper_index.md> [--threshold 0.6]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


def parse_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    header = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            if cells[0].lower() == "id":
                header = [c.lower() for c in cells]
            continue
        if cells[0].startswith("---"):
            continue
        if not re.match(r"^P\d{3,5}$", cells[0]):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def is_starstarstar(value: str) -> bool:
    return value.count("★") >= 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paper_index", type=Path)
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="Single-bucket dominance threshold (default 0.6).")
    args = parser.parse_args(argv)

    if not args.paper_index.is_file():
        print(f"missing: {args.paper_index}", file=sys.stderr)
        return 2

    rows = parse_rows(args.paper_index.read_text(encoding="utf-8"))
    starred = [r for r in rows if is_starstarstar(r.get("stars", ""))]
    if not starred:
        print("no ★★★ papers; bias audit not applicable")
        return 0

    n = len(starred)
    print(f"★★★ population: {n} papers\n")

    buckets = {
        "institution": [r.get("inst", "?") for r in starred],
        "year": [r.get("year", "?") for r in starred],
        "venue": [r.get("venue", "?") for r in starred],
    }

    triggered = 0
    for name, values in buckets.items():
        c = Counter(values)
        total = sum(c.values())
        top_value, top_count = c.most_common(1)[0]
        share = top_count / total
        flag = "TRIGGER" if share > args.threshold else "ok"
        print(f"  {name:12s}  top: {top_value!r} = {top_count}/{total} ({share:.0%}) [{flag}]")
        if share > args.threshold:
            triggered += 1
        # Also print full distribution if small
        if len(c) <= 10:
            for v, k in c.most_common():
                print(f"      {v!r}: {k}")

    print(f"\nbiases triggered: {triggered}")
    return 1 if triggered else 0


if __name__ == "__main__":
    sys.exit(main())
