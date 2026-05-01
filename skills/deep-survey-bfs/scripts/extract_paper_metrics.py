#!/usr/bin/env python3
"""Extract candidate metric rows from a paper PDF.

Pipeline:
  1. If input is an arXiv ID (e.g. 2303.06615), download
     https://arxiv.org/pdf/<id> to a cached path under /tmp.
  2. Run pdftotext -layout to produce text.
  3. Locate candidate table sections by header signatures
     (e.g. lines containing "Method" + a metric keyword).
  4. Print each candidate window with line numbers so the agent
     can quote-verify into claims.jsonl.

The script does NOT decide what number is "the" answer — it surfaces
candidates. The agent must read each candidate and pick the right cell
(metric, split, version) before quoting.

Usage:
    python3 extract_paper_metrics.py <arxiv-id-or-pdf-path> [--metric METRIC] [--window N]

Examples:
    python3 extract_paper_metrics.py 2303.06615
    python3 extract_paper_metrics.py 2303.06615 --metric KITTI --window 30
    python3 extract_paper_metrics.py /tmp/foundation.pdf --metric "EPE|D1|Bad"

Default metric pattern covers KITTI / Scene Flow / Middlebury / ETH3D /
EPE / Bad / D1 / params / FPS / latency / TensorRT / Jetson. Override
with --metric to narrow.

Dependencies: pdftotext (poppler-utils). No Python pip dependencies.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


CACHE_DIR = Path(os.environ.get("DEEP_SURVEY_PDF_CACHE", "/tmp/deep-survey-pdf-cache"))

DEFAULT_METRIC_PATTERN = (
    r"KITTI|Scene\s*Flow|SceneFlow|Middlebury|ETH3D|"
    r"\bEPE\b|\bD1\b|\bBad\s*[12]|"
    r"params?\s*\(\s*M|\b[0-9]+\.?[0-9]*\s*M\s*params|"
    r"\bFPS\b|\bms\b|latency|runtime|inference\s+time|"
    r"TensorRT|\bONNX\b|Jetson|\bTRT\b|FP16|FP32|INT8"
)

TABLE_HEADER_HINTS = (
    r"^\s*(Method|Model|Models?)\s",
    r"^\s*(Method|Model|Models?)\s*\|",
    r"Method\s+.+?(EPE|D1|Bad|KITTI|Scene\s*Flow|Middlebury|ETH3D|FPS|Param)",
    r"^\s*Table\s+\d",
)


def is_arxiv_id(s: str) -> bool:
    return bool(re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", s))


def fetch_pdf(arxiv_id: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    base = re.sub(r"v\d+$", "", arxiv_id)
    out = CACHE_DIR / f"{base}.pdf"
    if out.exists() and out.stat().st_size > 1024:
        return out
    url = f"https://arxiv.org/pdf/{base}"
    print(f"downloading {url} -> {out}", file=sys.stderr)
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            out.write_bytes(resp.read())
    except Exception as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        raise
    return out


def to_text(pdf_path: Path) -> Path:
    if not shutil.which("pdftotext"):
        print("pdftotext not on PATH (install poppler-utils)", file=sys.stderr)
        sys.exit(2)
    txt = pdf_path.with_suffix(".txt")
    if txt.exists() and txt.stat().st_mtime >= pdf_path.stat().st_mtime:
        return txt
    subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt)], check=True)
    return txt


def locate_tables(lines: list[str]) -> list[int]:
    """Return 1-based line numbers that look like table headers."""
    hits = []
    patterns = [re.compile(p, re.IGNORECASE) for p in TABLE_HEADER_HINTS]
    for i, line in enumerate(lines, start=1):
        for p in patterns:
            if p.search(line):
                hits.append(i)
                break
    return hits


def candidate_metric_lines(lines: list[str], metric_re: re.Pattern) -> list[int]:
    """Return 1-based line numbers that mention any metric keyword."""
    return [i for i, line in enumerate(lines, start=1) if metric_re.search(line)]


def render_window(lines: list[str], center: int, window: int) -> str:
    lo = max(0, center - 1 - window // 2)
    hi = min(len(lines), center + window // 2)
    out = []
    for n in range(lo, hi):
        marker = ">>" if n + 1 == center else "  "
        out.append(f"{marker} {n + 1:5d}: {lines[n].rstrip()}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paper", help="arXiv ID (e.g. 2303.06615) or path to PDF")
    parser.add_argument(
        "--metric",
        default=DEFAULT_METRIC_PATTERN,
        help="Regex (case-insensitive) of metric keywords. Default covers stereo benchmark + edge deployment terms.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=20,
        help="Lines of context around each candidate (default 20).",
    )
    parser.add_argument(
        "--max-hits",
        type=int,
        default=8,
        help="Maximum candidate windows to show (default 8).",
    )
    parser.add_argument(
        "--tables-only",
        action="store_true",
        help="Show only candidates that coincide with a table-header line.",
    )
    args = parser.parse_args(argv)

    if is_arxiv_id(args.paper):
        pdf_path = fetch_pdf(args.paper)
    else:
        pdf_path = Path(args.paper)
        if not pdf_path.is_file():
            print(f"missing pdf: {pdf_path}", file=sys.stderr)
            return 2

    txt_path = to_text(pdf_path)
    lines = txt_path.read_text(encoding="utf-8", errors="replace").splitlines()
    metric_re = re.compile(args.metric, re.IGNORECASE)
    metric_hits = candidate_metric_lines(lines, metric_re)
    table_hits = set(locate_tables(lines))

    if args.tables_only:
        windows = sorted(set(h for h in metric_hits if any(abs(h - t) <= 5 for t in table_hits)))
    else:
        # Prefer hits near table headers
        windows = sorted(
            metric_hits,
            key=lambda h: (0 if any(abs(h - t) <= 5 for t in table_hits) else 1, h),
        )

    if not windows:
        print(f"no metric candidates found in {pdf_path}", file=sys.stderr)
        return 1

    seen_blocks: set[int] = set()
    rendered = 0
    for h in windows:
        block_id = h // max(args.window, 1)
        if block_id in seen_blocks:
            continue
        seen_blocks.add(block_id)
        print(f"\n--- candidate window centered at line {h} ---")
        print(render_window(lines, h, args.window))
        rendered += 1
        if rendered >= args.max_hits:
            break

    print(
        f"\nshowed {rendered} window(s) from {pdf_path}; "
        f"total metric hits {len(metric_hits)}, table-header hits {len(table_hits)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
