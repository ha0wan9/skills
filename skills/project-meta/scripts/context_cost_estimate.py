#!/usr/bin/env python3
"""Estimate the context-window cost of each skill, by load tier.

Mirrors Claude Code's per-component cost display: the frontmatter
`description` is *always-on* (paid every session a plugin is enabled), the
SKILL.md body is *on-invoke* (paid each time the skill fires), and
references/ + templates/ are *lazy* (paid only when a task class loads them).
An oversized always-on description is the most expensive mistake; this critic
flags it.

Usage:

    python3 context_cost_estimate.py <skill-or-marketplace-root> \
        [--max-desc-tokens 200] [--max-invoke-tokens 4000] [--fail-on-invoke] \
        [--chars-per-token 4]

--max-invoke-tokens gates the on-invoke SKILL.md body (0 = disabled).
Recommended: 4000 for a root/router skill, 3000 for ordinary skills. By
default an overage is advisory only (prints an INVOKE flag, exit code
unaffected); pass --fail-on-invoke to also count it toward the failure
total and exit code.

Dependency-free. Token counts are a chars/N heuristic, NOT a real tokenizer;
treat them as relative estimates, not billing figures.

Exit: 0 = every description within budget (and, with --fail-on-invoke, every
on-invoke body within budget), 1 = at least one over ceiling, 2 = path not
resolved.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance import frontmatter_field, split_frontmatter  # noqa: E402


def tokens(text: str, cpt: int) -> int:
    return math.ceil(len(text) / cpt)


def dir_tokens(path: Path, cpt: int) -> int:
    if not path.is_dir():
        return 0
    return sum(tokens(f.read_text(encoding="utf-8", errors="replace"), cpt) for f in path.rglob("*.md"))


def resolve_skills(path: Path) -> list[Path]:
    if (path / "SKILL.md").is_file():
        return [path]
    root = path / "skills" if (path / "skills").is_dir() else path
    return sorted(d for d in root.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="A skill directory or a marketplace root")
    parser.add_argument("--max-desc-tokens", type=int, default=200, help="always-on description ceiling (default 200)")
    parser.add_argument(
        "--max-invoke-tokens",
        type=int,
        default=0,
        help="on-invoke SKILL.md body ceiling (default 0 = disabled; recommend 4000 root/router, 3000 ordinary)",
    )
    parser.add_argument(
        "--fail-on-invoke",
        action="store_true",
        help="count on-invoke overages toward the failure total / exit code (default: advisory flag only)",
    )
    parser.add_argument("--chars-per-token", type=int, default=4, help="chars/token heuristic (default 4)")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    skills = resolve_skills(root)
    if not skills:
        print(f"no skills found under {root}", file=sys.stderr)
        return 2

    cpt = args.chars_per_token
    print(f"{'skill':<22} {'always-on':>9} {'on-invoke':>9} {'lazy':>7}  flag")
    print("-" * 60)
    over = 0
    for skill in skills:
        text = (skill / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        desc_t = tokens(frontmatter_field(fm, "description"), cpt)
        body_t = tokens(body, cpt)
        lazy_t = dir_tokens(skill / "references", cpt) + dir_tokens(skill / "templates", cpt)
        flags = []
        if desc_t > args.max_desc_tokens:
            flags.append(f"DESC>{args.max_desc_tokens} (compress; always-on)")
            over += 1
        if args.max_invoke_tokens and body_t > args.max_invoke_tokens:
            if args.fail_on_invoke:
                flags.append(f"INVOKE>{args.max_invoke_tokens}")
                over += 1
            else:
                flags.append(f"INVOKE>{args.max_invoke_tokens} (advisory)")
        flag = "; ".join(flags)
        print(f"{skill.name:<22} {desc_t:>9} {body_t:>9} {lazy_t:>7}  {flag}")

    print()
    print(f"summary: {len(skills)} skill(s), {over} over the enforced ceiling(s)")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
