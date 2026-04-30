#!/usr/bin/env python3
"""Extract small, heading-bounded Markdown context.

This script is intentionally dependency-free so agents can use it in fresh
repositories before project tooling is installed.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def _discover_repo_root(start: Path) -> Path:
    """Walk up from `start` to locate the enclosing project root.

    The script may live at multiple depths depending on install layout
    (e.g. `<repo>/scripts/extract_doc_context.py`,
    `<repo>/skill/scripts/extract_doc_context.py`, or
    `<install-dir>/skills/project-meta/scripts/extract_doc_context.py`).
    Prefer a `.git` directory; otherwise fall back to the current working
    directory so the extractor remains usable inside a target repo invoked
    via `cd <target> && python <skill>/scripts/extract_doc_context.py ...`.
    """
    for parent in (start, *start.parents):
        if (parent / ".git").exists():
            return parent
    return Path.cwd().resolve()


REPO_ROOT = _discover_repo_root(Path(__file__).resolve().parent)
ALLOWED_EXTENSIONS = {".md", ".mdx", ".markdown"}
MAX_MAX_LINES = 200
MAX_WITHIN_LINES = 500
MAX_CONTEXT_LINES = 50


@dataclass(frozen=True)
class Heading:
    line_no: int
    level: int
    title: str
    path: str


@dataclass(frozen=True)
class Selection:
    start: int
    end: int
    reason: str
    truncated_before: bool = False
    truncated_after: bool = False


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def query_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[\w.-]+", normalize(text), flags=re.UNICODE)
    return [token for token in tokens if token]


def line_matches(line: str, query: str) -> bool:
    haystack = normalize(line)
    needle = normalize(query)
    if needle and needle in haystack:
        return True
    tokens = query_tokens(query)
    return bool(tokens) and all(token in haystack for token in tokens)


def parse_headings(lines: list[str]) -> list[Heading]:
    headings: list[Heading] = []
    stack: list[Heading] = []

    for index, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1].level >= level:
            stack.pop()

        path_parts = [heading.title for heading in stack] + [title]
        heading = Heading(index, level, title, " > ".join(path_parts))
        headings.append(heading)
        stack.append(heading)

    return headings


def heading_end_line(headings: list[Heading], heading_index: int, total_lines: int) -> int:
    heading = headings[heading_index]
    for later in headings[heading_index + 1 :]:
        if later.level <= heading.level:
            return later.line_no - 1
    return total_lines


def heading_score(heading: Heading, query: str) -> int:
    q = normalize(query)
    title = normalize(heading.title)
    path = normalize(heading.path)
    tokens = query_tokens(query)

    score = 0
    if q and q == title:
        score += 100
    if q and q in title:
        score += 80
    if q and q in path:
        score += 60
    score += 8 * sum(1 for token in tokens if token in title)
    score += 3 * sum(1 for token in tokens if token in path)
    score -= heading.level
    return score


def best_heading(headings: list[Heading], query: str) -> int | None:
    scored = [(heading_score(heading, query), index) for index, heading in enumerate(headings)]
    scored = [(score, index) for score, index in scored if score > 0]
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], headings[item[1]].line_no))
    return scored[0][1]


def find_body_hit(
    lines: list[str],
    query: str,
    start: int,
    end: int,
) -> int | None:
    for line_no in range(start, end + 1):
        if line_matches(lines[line_no - 1], query):
            return line_no
    return None


def containing_heading(headings: list[Heading], line_no: int) -> int | None:
    candidate: int | None = None
    for index, heading in enumerate(headings):
        if heading.line_no <= line_no:
            candidate = index
        else:
            break
    return candidate


def bounded_selection(
    section_start: int,
    section_end: int,
    max_lines: int,
    reason: str,
    center: int | None = None,
    context_lines: int = 12,
) -> Selection:
    if center is None:
        start = section_start
        end = min(section_end, section_start + max_lines - 1)
    else:
        start = max(section_start, center - context_lines)
        end = min(section_end, center + context_lines)
        if end - start + 1 > max_lines:
            before = max_lines // 2
            start = max(section_start, center - before)
            end = min(section_end, start + max_lines - 1)

    return Selection(
        start=start,
        end=end,
        reason=reason,
        truncated_before=start > section_start,
        truncated_after=end < section_end,
    )


def select_context(
    lines: list[str],
    headings: list[Heading],
    query: str,
    heading_query: str | None,
    within_lines: int,
    max_lines: int,
    context_lines: int,
) -> Selection:
    if not headings:
        hit = find_body_hit(lines, query, 1, len(lines)) if query else None
        center = hit if hit is not None else None
        return bounded_selection(1, len(lines), max_lines, "document without headings", center, context_lines)

    heading_index = best_heading(headings, heading_query or query)
    if heading_index is not None:
        heading = headings[heading_index]
        section_start = heading.line_no
        section_end = heading_end_line(headings, heading_index, len(lines))
        search_end = min(section_end, section_start + within_lines - 1)

        hit = None
        if query and heading_query:
            hit = find_body_hit(lines, query, section_start, search_end)

        if hit is not None:
            return bounded_selection(
                section_start,
                section_end,
                max_lines,
                f"heading match '{heading.path}', body hit within {within_lines} lines",
                hit,
                context_lines,
            )

        return bounded_selection(
            section_start,
            min(section_end, search_end),
            max_lines,
            f"heading match '{heading.path}'",
            None,
            context_lines,
        )

    hit = find_body_hit(lines, query, 1, len(lines)) if query else None
    if hit is not None:
        owner_index = containing_heading(headings, hit)
        if owner_index is not None:
            section_start = headings[owner_index].line_no
            section_end = heading_end_line(headings, owner_index, len(lines))
            return bounded_selection(
                section_start,
                section_end,
                max_lines,
                f"body hit under '{headings[owner_index].path}'",
                hit,
                context_lines,
            )
        return bounded_selection(1, len(lines), max_lines, "body hit before first heading", hit, context_lines)

    return bounded_selection(1, min(len(lines), max_lines), max_lines, "no match; document prefix")


def print_index(headings: list[Heading]) -> None:
    for heading in headings:
        print(f"L{heading.line_no}: H{heading.level} {heading.path}")


def print_selection(path: Path, lines: list[str], selection: Selection) -> None:
    print(f"file: {path}")
    print(f"lines: {selection.start}-{selection.end}")
    print(f"reason: {selection.reason}")
    if selection.truncated_before or selection.truncated_after:
        print(
            "truncated:"
            f" before={str(selection.truncated_before).lower()}"
            f" after={str(selection.truncated_after).lower()}"
        )
    print()
    for line_no in range(selection.start, selection.end + 1):
        print(f"{line_no}: {lines[line_no - 1]}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Markdown file to inspect")
    parser.add_argument("--index", action="store_true", help="Print only the Markdown heading index")
    parser.add_argument("--query", default="", help="Keyword query for heading or body search")
    parser.add_argument("--heading", default=None, help="Prefer a specific heading before body search")
    parser.add_argument(
        "--within-lines",
        type=int,
        default=80,
        help="Maximum lines after a matched heading to search for --query",
    )
    parser.add_argument("--max-lines", type=int, default=80, help="Maximum lines to print")
    parser.add_argument("--context-lines", type=int, default=12, help="Body-hit context radius")
    return parser.parse_args(argv)


def resolve_repo_markdown_path(path: Path) -> Path:
    resolved = path.resolve(strict=True)

    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"path is outside repo root: {path}") from exc

    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"path must use a Markdown extension ({allowed}): {path}") from None

    return resolved


def validate_line_budgets(args: argparse.Namespace) -> None:
    if args.max_lines <= 0:
        raise ValueError("--max-lines must be positive")
    if args.within_lines <= 0:
        raise ValueError("--within-lines must be positive")
    if args.context_lines < 0:
        raise ValueError("--context-lines must be non-negative")

    if args.max_lines > MAX_MAX_LINES:
        raise ValueError(f"--max-lines may not exceed {MAX_MAX_LINES}")
    if args.within_lines > MAX_WITHIN_LINES:
        raise ValueError(f"--within-lines may not exceed {MAX_WITHIN_LINES}")
    if args.context_lines > MAX_CONTEXT_LINES:
        raise ValueError(f"--context-lines may not exceed {MAX_CONTEXT_LINES}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        validate_line_budgets(args)
        path = resolve_repo_markdown_path(args.path)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"failed to read {path}: {exc}", file=sys.stderr)
        return 1

    headings = parse_headings(lines)
    if args.index:
        print_index(headings)
        return 0

    if not args.query and not args.heading:
        print("provide --index, --query, or --heading", file=sys.stderr)
        return 2

    selection = select_context(
        lines=lines,
        headings=headings,
        query=args.query,
        heading_query=args.heading,
        within_lines=args.within_lines,
        max_lines=args.max_lines,
        context_lines=args.context_lines,
    )
    print_selection(path, lines, selection)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
