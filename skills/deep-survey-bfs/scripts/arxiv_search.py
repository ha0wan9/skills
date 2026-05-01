#!/usr/bin/env python3
"""Light arXiv API wrapper for Round 1 / Round N keyword searches.

Uses arxiv.org/api/query with stdlib only. Prints title / authors / abstract
snippet / arXiv ID / submission date for each result. Designed to feed the
inclusion decision step in 01-round1.md.

Usage:
  python3 arxiv_search.py "query" [--max 20] [--cat cs.CV] [--from 2020] [--to 2026]

Examples:
  python3 arxiv_search.py "stereo matching foundation model" --cat cs.CV --from 2023
  python3 arxiv_search.py "EEG self supervised" --max 30
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def build_query(terms: str, cat: str | None, from_year: int | None, to_year: int | None) -> str:
    parts = [f"all:{terms}"]
    if cat:
        parts.append(f"cat:{cat}")
    q = "+AND+".join(urllib.parse.quote(p, safe=":+") for p in parts)
    extra = []
    if from_year and to_year:
        extra.append(f"submittedDate:[{from_year}01010000+TO+{to_year}12312359]")
    elif from_year:
        extra.append(f"submittedDate:[{from_year}01010000+TO+999912312359]")
    if extra:
        q = q + "+AND+" + "+AND+".join(extra)
    return q


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", help="Free-text query terms (will be ANDed).")
    parser.add_argument("--max", type=int, default=20, help="Max results (default 20).")
    parser.add_argument("--cat", default=None, help="arXiv category filter, e.g., cs.CV.")
    parser.add_argument("--from", dest="from_year", type=int, default=None)
    parser.add_argument("--to", dest="to_year", type=int, default=None)
    args = parser.parse_args(argv)

    search_query = build_query(args.query, args.cat, args.from_year, args.to_year)
    url = (
        f"{ARXIV_API}?search_query={search_query}"
        f"&start=0&max_results={args.max}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    print(f"GET {url}\n", file=sys.stderr)

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = resp.read()
    except Exception as exc:
        print(f"arxiv api error: {exc}", file=sys.stderr)
        return 2

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        print(f"arxiv api returned non-XML: {exc}", file=sys.stderr)
        return 2

    entries = root.findall("a:entry", ATOM_NS)
    if not entries:
        print("no results")
        return 0

    for i, entry in enumerate(entries, start=1):
        title = (entry.findtext("a:title", default="", namespaces=ATOM_NS) or "").strip()
        title = re.sub(r"\s+", " ", title)
        link = entry.find("a:id", ATOM_NS)
        arxiv_id = ""
        if link is not None and link.text:
            m = re.search(r"abs/(.+?)(?:v\d+)?$", link.text.strip())
            if m:
                arxiv_id = m.group(1)
        published = entry.findtext("a:published", default="", namespaces=ATOM_NS)
        authors = [
            a.findtext("a:name", default="", namespaces=ATOM_NS) or ""
            for a in entry.findall("a:author", ATOM_NS)
        ]
        first_author = authors[0] if authors else "?"
        n_authors = len(authors)
        summary = (entry.findtext("a:summary", default="", namespaces=ATOM_NS) or "").strip()
        snippet = re.sub(r"\s+", " ", summary)[:280]
        print(f"[{i:02d}] arXiv:{arxiv_id}  {published[:10]}")
        print(f"     {title}")
        print(f"     {first_author} et al. (n={n_authors})")
        print(f"     {snippet}...")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
