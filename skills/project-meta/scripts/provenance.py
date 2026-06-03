#!/usr/bin/env python3
"""Frontmatter + provenance primitive shared across project-meta and its
dependent skills.

This is the single canonical home for the frontmatter parse / validate / stamp
logic that several skill scripts had each re-rolled. Import it as a module
(``from provenance import split_frontmatter, parse_scalars, missing_keys``) or
drive it as a CLI. Standard library only.

Provenance is the small set of fields an instantiated artifact carries so its
lineage back to a template/reference is auditable:

    instantiated_from   # template/reference the artifact was derived from
    source_reference    # the canonical doc that owns the rule
    last_reviewed       # YYYY-MM-DD the artifact was last checked for drift

Usage:

    # validate required provenance keys are present and well-formed
    python3 provenance.py check path/to/artifact.md
    python3 provenance.py check path/to/file.yaml --require name,version

    # read one field
    python3 provenance.py get path/to/artifact.md last_reviewed

    # stamp / update scalar frontmatter keys (idempotent)
    python3 provenance.py stamp path/to/artifact.md \
        --set instantiated_from=project-meta/templates/foo.md \
        --set source_reference=project-meta/references/bar.md \
        --stamp-date                      # sets last_reviewed=<today>
    python3 provenance.py stamp path/to/artifact.md --set x=y --dry-run

Exit: 0 = ok, 1 = check failed / file problem, 2 = bad invocation.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

DEFAULT_REQUIRED = ("instantiated_from", "source_reference", "last_reviewed")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body). Frontmatter is '' when absent.

    Matches skill_architecture_lint.split_frontmatter so behaviour is identical
    everywhere this primitive replaces a bespoke parser.
    """
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    return text[3:end], text[end + 4 :]


def parse_scalars(fm: str) -> dict[str, str]:
    """Top-level ``key: value`` scalars only. Block/folded scalars and nested
    maps are ignored — provenance fields are always simple scalars."""
    out: dict[str, str] = {}
    for line in fm.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # top-level only: no leading indentation
        if line[:1].isspace():
            continue
        m = re.match(r"([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            val = m.group(2).strip()
            if val and val not in (">", "|", ">-", "|-", ">+", "|+"):
                out[m.group(1)] = val.strip("'\"")
    return out


def missing_keys(fm: str, required: tuple[str, ...]) -> list[str]:
    scalars = parse_scalars(fm)
    return [k for k in required if not scalars.get(k)]


def frontmatter_field(fm: str, key: str) -> str:
    """Grab a single field, handling inline and folded/literal (>- / |) scalars.

    Canonical home for the helper several skill scripts had each copied. Unlike
    parse_scalars (top-level scalars as a dict), this resolves one key and
    gathers folded block values."""
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            rest = stripped[len(key) + 1 :].strip()
            if rest and rest not in (">", "|", ">-", "|-", ">+", "|+"):
                return rest.strip("'\"")
            base_indent = len(line) - len(line.lstrip())
            collected: list[str] = []
            for cont in lines[i + 1 :]:
                if not cont.strip():
                    continue
                indent = len(cont) - len(cont.lstrip())
                if indent <= base_indent:
                    break
                collected.append(cont.strip())
            return " ".join(collected)
    return ""


def stamp(text: str, updates: dict[str, str]) -> str:
    """Insert/replace top-level scalar keys in the frontmatter, idempotently.

    Creates a frontmatter block when none exists. Existing non-scalar lines are
    preserved verbatim; only the named keys are touched."""
    fm, body = split_frontmatter(text)
    if not text.startswith("---") or not fm.strip():
        lines: list[str] = []
        remaining = dict(updates)
        body = text
    else:
        lines = fm.strip("\n").splitlines()
        remaining = dict(updates)
        for i, line in enumerate(lines):
            m = re.match(r"([A-Za-z0-9_-]+):", line)
            if m and m.group(1) in remaining:
                lines[i] = f"{m.group(1)}: {remaining.pop(m.group(1))}"
    for key, val in remaining.items():
        lines.append(f"{key}: {val}")
    return "---\n" + "\n".join(lines) + "\n---\n" + body.lstrip("\n")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1
    required = tuple(k.strip() for k in args.require.split(",")) if args.require else DEFAULT_REQUIRED
    fm, _ = split_frontmatter(_read(path))
    if not fm.strip():
        print(f"FAIL {path}: no frontmatter", file=sys.stderr)
        return 1
    missing = missing_keys(fm, required)
    scalars = parse_scalars(fm)
    bad_date = "last_reviewed" in required and scalars.get("last_reviewed") and not DATE_RE.match(
        scalars["last_reviewed"]
    )
    if missing or bad_date:
        if missing:
            print(f"FAIL {path}: missing {', '.join(missing)}", file=sys.stderr)
        if bad_date:
            print(f"FAIL {path}: last_reviewed not YYYY-MM-DD: {scalars['last_reviewed']}", file=sys.stderr)
        return 1
    print(f"PASS {path}: {', '.join(required)} present")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1
    fm, _ = split_frontmatter(_read(path))
    val = parse_scalars(fm).get(args.key, "")
    if not val:
        return 1
    print(val)
    return 0


def cmd_stamp(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1
    updates: dict[str, str] = {}
    for pair in args.set or []:
        if "=" not in pair:
            print(f"bad --set (need key=value): {pair}", file=sys.stderr)
            return 2
        key, val = pair.split("=", 1)
        if "\n" in val or "\r" in val:
            print(f"bad --set: value for {key.strip()} contains a newline (would corrupt frontmatter)", file=sys.stderr)
            return 2
        updates[key.strip()] = val.strip()
    if args.stamp_date:
        updates["last_reviewed"] = datetime.date.today().isoformat()
    if not updates:
        print("nothing to stamp (use --set or --stamp-date)", file=sys.stderr)
        return 2
    new_text = stamp(_read(path), updates)
    if args.dry_run:
        sys.stdout.write(new_text)
        return 0
    path.write_text(new_text, encoding="utf-8")
    print(f"stamped {path}: {', '.join(updates)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="validate provenance/required keys")
    p_check.add_argument("path")
    p_check.add_argument("--require", help="comma-separated keys (default: provenance trio)")
    p_check.set_defaults(func=cmd_check)

    p_get = sub.add_parser("get", help="print one frontmatter scalar")
    p_get.add_argument("path")
    p_get.add_argument("key")
    p_get.set_defaults(func=cmd_get)

    p_stamp = sub.add_parser("stamp", help="set/update scalar frontmatter keys")
    p_stamp.add_argument("path")
    p_stamp.add_argument("--set", action="append", metavar="KEY=VAL", help="repeatable")
    p_stamp.add_argument("--stamp-date", action="store_true", help="set last_reviewed=<today>")
    p_stamp.add_argument("--dry-run", action="store_true", help="print result, do not write")
    p_stamp.set_defaults(func=cmd_stamp)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
