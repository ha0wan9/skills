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


# Map of common country signals -> canonical country. Keys are matched
# case-insensitively against (a) a dedicated Country column, or (b) a
# trailing parenthetical in the institution cell, e.g. "Tsinghua (CN)".
_COUNTRY_CODES = {
    "us": "USA", "usa": "USA", "united states": "USA",
    "uk": "UK", "gb": "UK", "united kingdom": "UK",
    "fr": "France", "france": "France",
    "de": "Germany", "germany": "Germany",
    "cn": "China", "china": "China",
    "jp": "Japan", "japan": "Japan",
    "ch": "Switzerland", "switzerland": "Switzerland",
    "nl": "Netherlands", "netherlands": "Netherlands",
    "ca": "Canada", "canada": "Canada",
    "il": "Israel", "israel": "Israel",
    "kr": "South Korea", "es": "Spain", "it": "Italy", "au": "Australia",
}

# Country tokens inferred from well-known institutions when no explicit
# country signal is present. Intentionally small and conservative — when a
# row carries no country signal at all the bucket reports "?" so the gap is
# visible rather than guessed.
_INST_COUNTRY_HINTS = {
    "mit": "USA", "stanford": "USA", "harvard": "USA", "princeton": "USA",
    "berkeley": "USA", "nyu": "USA", "cmu": "USA", "carnegie": "USA",
    "caltech": "USA", "ucsf": "USA", "uc davis": "USA", "purdue": "USA",
    "minnesota": "USA", "salk": "USA", "rochester": "USA", "emory": "USA",
    "georgia tech": "USA", "baylor": "USA", "ibm": "USA", "intel": "USA",
    "deepmind": "UK", "ucl": "UK", "oxford": "UK", "bristol": "UK",
    "manchester": "UK", "gatsby": "UK",
    "tsinghua": "China", "peking": "China", "casia": "China",
    "epfl": "Switzerland", "tübingen": "Germany", "tubingen": "Germany",
    "mpi": "Germany", "max planck": "Germany", "helmholtz": "Germany",
    "donders": "Netherlands", "radboud": "Netherlands", "osnabrück": "Germany",
    "mila": "Canada", "montréal": "Canada", "montreal": "Canada", "toronto": "Canada",
    "oist": "Japan", "atr": "Japan", "riken": "Japan", "osaka": "Japan", "nict": "Japan",
    "ens": "France", "inria": "France", "cnrs": "France", "neurospin": "France",
    "collège de france": "France", "meta ai paris": "France",
}

_PAREN_RE = re.compile(r"\(([^)]*)\)\s*$")


def infer_country(row: dict, get_inst) -> str:
    """Best-effort country for a row.

    Priority: explicit Country column -> trailing parenthetical in the
    institution cell (e.g. "(CN)") -> known-institution hint -> "?".
    Returns "?" when there is no signal, so missing-country shows up as an
    explicit data gap rather than a silent default.
    """
    explicit = (row.get("country") or "").strip().lower()
    if explicit:
        return _COUNTRY_CODES.get(explicit, row["country"].strip())
    inst = get_inst(row)
    m = _PAREN_RE.search(inst)
    if m:
        token = m.group(1).strip().lower()
        if token in _COUNTRY_CODES:
            return _COUNTRY_CODES[token]
    low = inst.lower()
    for hint, country in _INST_COUNTRY_HINTS.items():
        if hint in low:
            return country
    return "?"


def get_method_route(row: dict) -> str | None:
    """Return the method-route cell if such a column exists, else None.

    Recognized column names: 'method route', 'method-route', 'route',
    'method'. Absent column -> None so the bucket is reported as
    'not available (add a Method-route column)' rather than fabricated.
    """
    for key in ("method route", "method-route", "route", "method"):
        v = row.get(key)
        if v and v not in {"-", "—"}:
            return v
    return None


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

    # Method-route is only audited when the index carries a column for it.
    method_values = [get_method_route(r) for r in starred]
    have_method = any(v is not None for v in method_values)

    buckets = {
        "institution": [get_inst(r) or "?" for r in starred],
        "country": [infer_country(r, get_inst) for r in starred],
        "year": [r.get("year", "?") for r in starred],
        "venue": [r.get("venue", "?") for r in starred],
    }
    if have_method:
        buckets["method route"] = [v or "?" for v in method_values]

    triggered = 0
    for name, values in buckets.items():
        c = Counter(values)
        total = sum(c.values())
        top_value, top_count = c.most_common(1)[0]
        share = top_count / total
        # A bucket dominated by "?" is a data gap, not a real bias signal:
        # report it as such instead of triggering on missing data.
        unknown_share = c.get("?", 0) / total if total else 0
        if name in {"country", "method route"} and unknown_share > 0.5:
            print(f"  {name:12s}  top: '?' = {c.get('?',0)}/{total} "
                  f"({unknown_share:.0%}) [DATA-GAP: add a Country/Method-route "
                  f"column or country tags like 'Lab (CN)' to enable this audit]")
            continue
        flag = "TRIGGER" if share > args.threshold else "ok"
        print(f"  {name:12s}  top: {top_value!r} = {top_count}/{total} ({share:.0%}) [{flag}]")
        if share > args.threshold:
            triggered += 1
        # Also print full distribution if small
        if len(c) <= 10:
            for v, k in c.most_common():
                print(f"      {v!r}: {k}")

    if not have_method:
        print("  method route  not audited (no 'Method route' column in "
              "paper_index.md; add one to enable method-bias detection)")

    print(f"\nbiases triggered: {triggered}")
    return 1 if triggered else 0


if __name__ == "__main__":
    sys.exit(main())
