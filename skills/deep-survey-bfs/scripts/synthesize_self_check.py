#!/usr/bin/env python3
"""Self-check survey.md against the structural requirements in
templates/survey-skeleton.md.

Catches the class of regressions that the stereo-matching test surfaced
(flat reading list when skeleton requires four tiers; §4 datasets
section absent or placed after §5 method comparison; §14 reproducibility
tier missing when ★★★ papers have varied code-release status).

Usage:
  python3 synthesize_self_check.py <survey.md> [paper_index.md]

Exit codes:
  0 = all required structure present
  1 = one or more required sections missing or out of order
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SECTION_RE = re.compile(r"^##\s+§?(\d+(?:\.\d+)?)(?:\.\d+)?\s+(.+?)(?:\s*\{#[\w-]+\})?\s*$")
SUBSECTION_RE = re.compile(r"^###\s+(.+?)\s*$")


def parse_sections(text: str) -> list[tuple[str, str, int]]:
    """Return [(section_id, title, line_no), ...] for top-level §N headings."""
    out: list[tuple[str, str, int]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        m = SECTION_RE.match(raw.strip())
        if m:
            out.append((m.group(1), m.group(2).strip(), line_no))
    return out


def parse_subsections_under(text: str, section_id: str) -> list[str]:
    """Return list of H3 titles that appear under §section_id, in order."""
    lines = text.splitlines()
    inside = False
    found: list[str] = []
    for raw in lines:
        m = SECTION_RE.match(raw.strip())
        if m:
            inside = m.group(1) == section_id
            continue
        if inside:
            sm = SUBSECTION_RE.match(raw.strip())
            if sm:
                found.append(sm.group(1).strip())
    return found


def has_starstarstar_with_varied_repro(paper_index_path: Path) -> bool:
    if not paper_index_path.is_file():
        return False
    repro_values: set[str] = set()
    for raw in paper_index_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not re.match(r"^P\d{3,5}$", cells[0]):
            continue
        if cells[-1] if False else "":  # placeholder; we look up by header below
            pass
        # Try to find a "repro" cell heuristically: any cell containing
        # "oss/" or "pending" or "closed" suffices.
        if any("★★★" in c for c in cells):
            for c in cells:
                if "oss/" in c or c.lower() == "pending" or "/recipe:" in c:
                    repro_values.add(c)
    # If any ★★★ has a non-empty repro descriptor that isn't 'pending',
    # AND any other has 'pending', this is "varied" → require §14.
    has_real = any(v != "pending" for v in repro_values)
    has_pending = any(v == "pending" for v in repro_values)
    return has_real and has_pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("survey", type=Path)
    parser.add_argument("paper_index", type=Path, nargs="?", default=None)
    args = parser.parse_args(argv)

    if not args.survey.is_file():
        print(f"missing: {args.survey}", file=sys.stderr)
        return 2

    text = args.survey.read_text(encoding="utf-8")
    sections = parse_sections(text)
    section_ids = [s[0] for s in sections]
    section_titles = {s[0]: s[1] for s in sections}

    issues: list[str] = []

    # Rule 1: §4 datasets must exist and come before §5 method comparison.
    # Permit §3.x datasets (legacy v1.1 layout) but warn.
    datasets_id = None
    for sid, title, _ in sections:
        if "dataset" in title.lower() or "benchmark" in title.lower():
            datasets_id = sid
            break
    methods_id = None
    methods_keywords = (
        "method-route", "method comparison", "method route",
        "per-paper deep-dive", "per-paper",
        "architecture", "architectures",
        "approach", "approaches",
        "model comparison", "models compared",
    )
    for sid, title, _ in sections:
        tl = title.lower()
        if any(k in tl for k in methods_keywords):
            methods_id = sid
            break
    if datasets_id is None:
        issues.append(
            "no datasets section found (skeleton §4 requires "
            "'Datasets and benchmarks' before method comparison)"
        )
    if methods_id is None:
        issues.append(
            "no methods/architecture section found (skeleton §5 requires "
            "a method-route comparison or per-paper deep-dives section). "
            "If your survey calls it something else, add 'method', "
            "'architecture', or 'approach' to the heading so the check "
            "can locate it."
        )
    elif datasets_id is not None:
        try:
            d_num = float(datasets_id)
            m_num = float(methods_id)
            if d_num >= m_num:
                issues.append(
                    f"datasets section §{datasets_id} '{section_titles[datasets_id]}' "
                    f"comes at or after methods section §{methods_id} "
                    f"'{section_titles[methods_id]}'; skeleton requires datasets first"
                )
        except ValueError:
            pass

    # Rule 2: §13 (reading list) must have all four tiers if it exists.
    reading_id = None
    for sid, title, _ in sections:
        if "reading" in title.lower() or "recommended" in title.lower():
            reading_id = sid
            break
    if reading_id is None:
        issues.append(
            "no reading-list section found (skeleton §13 requires "
            "'Recommended reading' with Entry/Deep/Critical/Overview tiers)"
        )
    else:
        subs = parse_subsections_under(text, reading_id)
        sub_blob = " | ".join(s.lower() for s in subs)
        for tier_label, keywords in [
            ("Entry", ("entry tier", "entry-tier", "entry ")),
            ("Deep", ("deep tier", "deep-tier", "deep ")),
            ("Critical", ("critical tier", "critical-tier", "critical ")),
            ("Overview", ("overview tier", "overview-tier", "overview ")),
        ]:
            if not any(kw in sub_blob for kw in keywords):
                issues.append(
                    f"reading-list section §{reading_id} missing '{tier_label} tier' subsection "
                    f"(skeleton §13 requires Entry/Deep/Critical/Overview)"
                )

    # Rule 3: §14 reproducibility tier required when ★★★ papers have
    # varied repro status in paper_index.md.
    paper_index_path = args.paper_index or args.survey.parent / "paper_index.md"
    if has_starstarstar_with_varied_repro(paper_index_path):
        repro_id = None
        for sid, title, _ in sections:
            tl = title.lower()
            if "reproducibility" in tl or "repro tier" in tl:
                repro_id = sid
                break
        if repro_id is None:
            issues.append(
                "★★★ papers have mixed repro status (some 'pending', some "
                "with code-release descriptors) but no Reproducibility tier "
                "section found (skeleton §14 required when status varies)"
            )

    # Rule 4: section IDs must be monotonic (warns about v1.x append-style
    # supplements that break TOC order).
    seen_floats: list[float] = []
    for sid, _, ln in sections:
        try:
            v = float(sid)
        except ValueError:
            continue
        seen_floats.append(v)
    out_of_order = [
        (i, seen_floats[i])
        for i in range(1, len(seen_floats))
        if seen_floats[i] < seen_floats[i - 1]
    ]
    if out_of_order:
        issues.append(
            "section numbering is non-monotonic: "
            + ", ".join(f"§{v} after §{seen_floats[i - 1]}" for i, v in out_of_order)
            + " (run 05-version.md renumber pass before publishing)"
        )

    if issues:
        print(f"synthesis self-check FAILED with {len(issues)} issue(s):")
        for i in issues:
            print(f"  - {i}")
        return 1
    print(
        f"ok: {len(sections)} sections; datasets at §{datasets_id}, methods at "
        f"§{methods_id}, reading list at §{reading_id}; structure compliant"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
