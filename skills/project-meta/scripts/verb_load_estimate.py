#!/usr/bin/env python3
"""Estimate the per-verb context load of each `/project-meta` recipe.

`context_cost_estimate.py` measures a *skill's* always-on/on-invoke/lazy tiers;
it cannot see how heavy a single verb's read set is. This script fills that gap:
it parses each recipe's `## Required references` section, classifies every cited
file as **base** (always loaded when the verb runs), **lazy** (loaded only when a
specific step fires — under a `Lazy-load:` label), or **optional** (feature-flag
gated — under an `Optional` label), and sums file sizes per tier.

That alone understates real invocation cost: every verb also pays for the
skill's `SKILL.md` router (loaded once per run, whichever verb fires) and for
the recipe file itself (its own prose, read in full). This script adds those
two as a **router** and **recipe** column and reports **initial** = router +
recipe + base — the true first-load cost of invoking the verb, before any
lazy/optional reference is pulled in.

The point of staging (D4): keep each verb's **base** load small so invoking a verb
does not eagerly pull every reference. The headline budget is `init` base <= 40 KB.

Usage:

    python3 verb_load_estimate.py <recipe.md | recipes-dir> [--budget-kb 40] \
        [--chars-per-token 4] [--json]

Parsing convention (the recipes' `## Required references` section):
  - bullets before any tier label are **base**;
  - a tier label is a non-reference line whose first word is `Base`, `Lazy-load`
    (or `Lazy`), or `Optional` (bold `**Lazy-load**` or plain) — it switches the
    tier for the bullets that follow, until the next label;
  - a bullet's references are every `.md`/`.sh` path on the line written as a
    markdown link `[text](href)` (a single bullet may name more than one file,
    e.g. an `--flag` that loads two); bare code-span mentions are not counted, so
    a `scripts/x.py` invocation or an instantiated target artifact is ignored.

The router is `SKILL.md` in the parent directory of the recipes dir passed on
the command line (e.g. `skills/project-meta/recipes` -> `skills/project-meta/SKILL.md`);
its size is computed once per run and added to every verb's row. If no such
SKILL.md exists, router is counted as 0 bytes and a warning is printed.

Dependency-free; sizes are real bytes (KB = bytes/1024). Token counts are a
chars/N heuristic, not a tokenizer. Exit: 0 = every recipe's base within budget,
1 = at least one base over --budget-kb, 2 = path not resolved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# A reference is a *markdown link* to a .md/.sh path — `[text](href)`. We match the
# whole link (text + href) and capture the href, so the path inside the link's code-span
# text is never double-counted, and incidental code-span mentions of non-reference paths
# (e.g. an instantiated target artifact, or a `scripts/x.py` invocation) are ignored.
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#]+?\.(?:md|sh))(?:#[^)]*)?\)")
REQ_HEADING_RE = re.compile(r"^##\s+Required references\b", re.IGNORECASE)
NEXT_HEADING_RE = re.compile(r"^##\s+")
# A tier label is a non-reference line whose first word (after bold/quote marks)
# is the tier keyword. `-` is deliberately NOT in the leading-strip class, so a
# list bullet like "- optional note:" cannot masquerade as a tier label; only a
# bold/plain heading (`**Lazy-load** — …`, `Optional:`) flips the tier.
LABEL_RE = re.compile(r"^[*_\s>]*(base|lazy-?load|lazy|optional)\b", re.IGNORECASE)


def line_refs(line: str) -> list[str]:
    """Distinct markdown-link reference hrefs on a line, in order — a single
    bullet may name more than one file (e.g. an `--flag` that loads two)."""
    out: list[str] = []
    for href in LINK_RE.findall(line):
        if href not in out:
            out.append(href)
    return out


def resolve_ref(recipe: Path, link: str) -> Path | None:
    """Resolve a markdown link target relative to the recipe file, tolerating
    both `../references/x.md` and `references/x.md` forms."""
    link = link.split("#", 1)[0].strip()
    if not link:
        return None
    for base in (recipe.parent, recipe.parent.parent):
        cand = (base / link).resolve()
        if cand.is_file():
            return cand
    return None


def classify_refs(recipe: Path) -> tuple[dict[str, list[tuple[str, int]]], list[str]]:
    """Return ({tier: [(ref, bytes), ...]}, missing) for the refs in the recipe's
    `## Required references` section. Missing files count as 0 bytes and are also
    collected so the caller can warn (a silent 0 would hide a typo'd href)."""
    text = recipe.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    tiers: dict[str, list[tuple[str, int]]] = {"base": [], "lazy": [], "optional": []}
    missing: list[str] = []
    in_section = False
    mode = "base"
    for line in lines:
        if not in_section:
            if REQ_HEADING_RE.match(line):
                in_section = True
            continue
        if NEXT_HEADING_RE.match(line):
            break
        refs = line_refs(line)
        if not refs:
            # No reference on this line — it may be a tier label.
            m = LABEL_RE.match(line)
            if m:
                kw = m.group(1).lower()
                mode = "optional" if kw == "optional" else ("lazy" if kw.startswith("lazy") else "base")
            continue
        for ref in refs:
            resolved = resolve_ref(recipe, ref)
            if resolved is None:
                missing.append(f"{recipe.name}: {ref}")
            size = resolved.stat().st_size if resolved else 0
            tiers[mode].append((ref, size))
    return tiers, missing


def kb(n: int) -> float:
    return round(n / 1024, 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="a recipe .md file or a recipes/ directory")
    parser.add_argument("--budget-kb", type=float, default=40.0, help="base-load ceiling per verb in KB (default 40)")
    parser.add_argument("--chars-per-token", type=int, default=4, help="chars/token heuristic (default 4)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if root.is_dir():
        recipes = sorted(p for p in root.glob("*.md"))
        recipes_dir = root
    elif root.is_file():
        recipes = [root]
        recipes_dir = root.parent
    else:
        print(f"not a file or directory: {root}", file=sys.stderr)
        return 2
    if not recipes:
        print(f"no recipe .md files under {root}", file=sys.stderr)
        return 2

    # Router: the skill's SKILL.md, one directory up from the recipes dir
    # (e.g. skills/project-meta/recipes -> skills/project-meta/SKILL.md). Every
    # verb pays for it once per invocation, so it's added to each row below.
    router = recipes_dir.parent / "SKILL.md"
    if router.is_file():
        router_b = router.stat().st_size
    else:
        router_b = 0
        print(f"warning: no SKILL.md found at {router} (router counted as 0 bytes)", file=sys.stderr)

    report = []
    over = 0
    all_missing: list[str] = []
    for recipe in recipes:
        tiers, missing = classify_refs(recipe)
        all_missing.extend(missing)
        base_b = sum(b for _, b in tiers["base"])
        lazy_b = sum(b for _, b in tiers["lazy"])
        opt_b = sum(b for _, b in tiers["optional"])
        recipe_b = recipe.stat().st_size
        initial_b = router_b + recipe_b + base_b
        verb = recipe.stem
        breached = kb(base_b) > args.budget_kb
        if breached:
            over += 1
        report.append({
            "verb": verb,
            "router_kb": kb(router_b),
            "recipe_kb": kb(recipe_b),
            "base_kb": kb(base_b),
            "base_tokens": (base_b + args.chars_per_token - 1) // args.chars_per_token,
            "initial_kb": kb(initial_b),
            "initial_tokens": (initial_b + args.chars_per_token - 1) // args.chars_per_token,
            "lazy_kb": kb(lazy_b),
            "optional_kb": kb(opt_b),
            "over_budget": breached,
            "base_refs": [r for r, _ in tiers["base"]],
            "lazy_refs": [r for r, _ in tiers["lazy"]],
            "optional_refs": [r for r, _ in tiers["optional"]],
        })

    if all_missing:
        for m in all_missing:
            print(f"warning: unresolved reference (counted as 0 bytes): {m}", file=sys.stderr)

    if args.json:
        print(json.dumps({"budget_kb": args.budget_kb, "router_kb": kb(router_b), "recipes": report, "missing_refs": all_missing}, indent=2))
        return 1 if over else 0

    print(f"{'verb':<14} {'router':>8} {'recipe':>8} {'base':>8} {'initial':>9} {'lazy':>8} {'optional':>9}  flag")
    print("-" * 82)
    for r in report:
        flag = f"BASE>{args.budget_kb:g}KB" if r["over_budget"] else ""
        print(
            f"{r['verb']:<14} {r['router_kb']:>7}K {r['recipe_kb']:>7}K {r['base_kb']:>7}K "
            f"{r['initial_kb']:>8}K {r['lazy_kb']:>7}K {r['optional_kb']:>8}K  {flag}"
        )
    print()
    print(f"summary: {len(report)} recipe(s), {over} over the {args.budget_kb:g}KB base budget")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
