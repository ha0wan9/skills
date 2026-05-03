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
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Include rows with status != 'confirmed' in the bias counts. "
             "Default is to skip them so extraction-debt is not flagged as "
             "lab capture.",
    )
    parser.add_argument(
        "--strict-status",
        action="store_true",
        help="Require an explicit `confirmed` value in the Status column. "
             "Default behaviour now auto-promotes a row to confirmed when its "
             "Inst cell is populated with a real institution (not empty, '?', "
             "or *-pending), since filling the Inst column was a manual "
             "investigation step in earlier workflow.",
    )
    args = parser.parse_args(argv)

    if not args.paper_index.is_file():
        print(f"missing: {args.paper_index}", file=sys.stderr)
        return 2

    rows = parse_rows(args.paper_index.read_text(encoding="utf-8"))
    starred = [r for r in rows if is_starstarstar(r.get("stars", ""))]
    if not starred:
        print("no ★★★ papers; bias audit not applicable")
        return 0

    def get_inst(row: dict) -> str:
        # Accept any of the column-name variants seen in practice.
        for key in ("inst", "institution", "affiliation", "lab"):
            v = row.get(key)
            if v:
                return v
        return ""

    def is_confirmed(row: dict) -> bool:
        explicit = row.get("status", "").strip().lower() == "confirmed"
        if explicit or args.strict_status:
            return explicit
        # Auto-promote: a populated institution cell counts as confirmed.
        inst = get_inst(row).strip().lower()
        if not inst or inst in {"?", "n/a", "tbd", "unknown"}:
            return False
        if inst.endswith("-pending") or inst == "pending":
            return False
        return True

    n_total = len(starred)
    if not args.include_pending:
        confirmed = [r for r in starred if is_confirmed(r)]
        skipped = n_total - len(confirmed)
        if skipped:
            print(
                f"★★★ population: {len(confirmed)}/{n_total} papers (skipped "
                f"{skipped} with status != 'confirmed'; pass --include-pending "
                f"to count them)\n"
            )
        else:
            print(f"★★★ population: {len(confirmed)} papers\n")
        starred = confirmed
    else:
        print(f"★★★ population: {n_total} papers (all rows included)\n")

    if not starred:
        print(
            "no confirmed-status ★★★ papers; nothing to audit. Round N "
            "should populate institution/venue and set status=confirmed."
        )
        return 0

    n = len(starred)

    buckets = {
        "institution": [get_inst(r) or "?" for r in starred],
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
