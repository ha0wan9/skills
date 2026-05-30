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
        [--max-desc-tokens 200] [--chars-per-token 4]

Dependency-free. Token counts are a chars/N heuristic, NOT a real tokenizer;
treat them as relative estimates, not billing figures.

Exit: 0 = every description within budget, 1 = at least one over the
--max-desc-tokens ceiling, 2 = path not resolved.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    return ("", text) if end == -1 else (text[3:end], text[end + 4 :])


def frontmatter_field(fm: str, key: str) -> str:
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}:"):
            rest = line.strip()[len(key) + 1 :].strip()
            if rest and rest not in (">", "|", ">-", "|-", ">+", "|+"):
                return rest.strip("'\"")
            base = len(line) - len(line.lstrip())
            out = []
            for cont in lines[i + 1 :]:
                if not cont.strip():
                    continue
                if len(cont) - len(cont.lstrip()) <= base:
                    break
                out.append(cont.strip())
            return " ".join(out)
    return ""


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
        flag = ""
        if desc_t > args.max_desc_tokens:
            flag = f"DESC>{args.max_desc_tokens} (compress; always-on)"
            over += 1
        print(f"{skill.name:<22} {desc_t:>9} {body_t:>9} {lazy_t:>7}  {flag}")

    print()
    print(f"summary: {len(skills)} skill(s), {over} over the always-on description ceiling")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
