#!/usr/bin/env python3
"""Detect trigger collisions between peer skills (AP-SKL-3).

Two skills whose descriptions and trigger bullets overlap will fire
order-dependently unless each names the other in a Skill Arbitration section.
This critic extracts the trigger surface of every skill in a marketplace,
scores pairwise phrase overlap, and FAILs any overlapping pair that lacks a
*reciprocal* arbitration entry.

Usage:

    python3 trigger_collision_check.py <marketplace-root-or-skills-dir> \
        [--ngram 3] [--min-shared 4]

Dependency-free (standard library only).

Method:

- Trigger surface = frontmatter `description` + every bullet under a heading
  matching "Trigger Decision" / "Triggers" / "When to use". Intra-skill
  "Auto-detect" / "Loading Rules" routing is deliberately excluded.
- Overlap = count of distinctive word n-grams shared by both surfaces
  (stopword-only n-grams dropped).
- Arbitration = a heading matching "Skill Arbitration" whose body names the
  peer skill. Overlap without reciprocal arbitration => FAIL.

Exit: 0 = no unguarded collisions, 1 = at least one, 2 = path not resolved.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "with", "is",
    "are", "be", "this", "that", "it", "as", "at", "by", "from", "when", "what",
    "how", "use", "user", "asks", "ask", "skill", "into", "across", "via", "an",
}
# Trigger surface = "should I invoke this skill" content only. Auto-detect /
# Loading Rules are intra-skill phase routing, NOT cross-skill trigger surface,
# so they are deliberately excluded (they are near-identical boilerplate and
# would manufacture false collisions).
TRIGGER_HEADINGS = ("trigger decision", "triggers", "when to use")


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


def section_body(body: str, needles: tuple[str, ...]) -> str:
    """Return the text under the first heading matching any needle."""
    lines = body.splitlines()
    out: list[str] = []
    capturing = False
    cap_level = 0
    for line in lines:
        if line.lstrip().startswith("#"):
            stripped = line.lstrip()
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip().lower()
            if capturing and level <= cap_level:
                break
            if any(n in title for n in needles):
                capturing, cap_level = True, level
                continue
        if capturing:
            out.append(line)
    return "\n".join(out)


def ngrams(text: str, n: int) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    grams = set()
    for i in range(len(words) - n + 1):
        gram = words[i : i + n]
        if all(w in STOPWORDS for w in gram):
            continue
        grams.add(" ".join(gram))
    return grams


def trigger_surface(text: str) -> str:
    fm, body = split_frontmatter(text)
    return frontmatter_field(fm, "description") + "\n" + section_body(body, TRIGGER_HEADINGS)


def arbitration_names(text: str, peer: str) -> bool:
    _, body = split_frontmatter(text)
    arb = section_body(body, ("skill arbitration",))
    return peer.lower() in arb.lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="Marketplace root (with skills/) or a directory of skill dirs")
    parser.add_argument("--ngram", type=int, default=3, help="n-gram size for overlap (default 3)")
    parser.add_argument("--min-shared", type=int, default=4, help="shared n-grams to flag a collision (default 4)")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    skills_root = root / "skills" if (root / "skills").is_dir() else root
    skills = {d.name: d for d in sorted(skills_root.iterdir()) if d.is_dir() and (d / "SKILL.md").is_file()}
    if len(skills) < 2:
        print(f"need >=2 skills to check collisions; found {len(skills)} under {skills_root}", file=sys.stderr)
        return 2

    texts = {n: (d / "SKILL.md").read_text(encoding="utf-8", errors="replace") for n, d in skills.items()}
    surfaces = {n: ngrams(trigger_surface(t), args.ngram) for n, t in texts.items()}

    names = list(skills)
    failures = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            shared = surfaces[a] & surfaces[b]
            a_names_b = arbitration_names(texts[a], b)
            b_names_a = arbitration_names(texts[b], a)
            overlap_hit = len(shared) >= args.min_shared

            # Two independent signals, both AP-SKL-3:
            #  (1) asymmetric arbitration — one skill declares the collision, the
            #      peer is silent. The robust signal; doesn't depend on phrasing.
            #  (2) trigger-phrase overlap with no reciprocal arbitration at all.
            asymmetric = a_names_b != b_names_a
            unguarded_overlap = overlap_hit and not (a_names_b or b_names_a)

            if not (asymmetric or unguarded_overlap or overlap_hit):
                continue

            status = "FAIL" if (asymmetric or unguarded_overlap) else "PASS"
            if status == "FAIL":
                failures += 1
            print(f"{status} {a} <-> {b}: {len(shared)} shared trigger phrases")
            if shared:
                print(f"    shared: {', '.join(sorted(shared)[:8])}")
            print(f"    arbitration: {a}->{b}={a_names_b}  {b}->{a}={b_names_a}")
            if asymmetric:
                silent = b if a_names_b else a
                print(f"    fix: {silent} has no reciprocal Skill Arbitration row for its peer (AP-SKL-3)")
            elif unguarded_overlap:
                print("    fix: overlapping triggers, neither skill arbitrates — add reciprocal rows (AP-SKL-3)")

    print()
    print(f"summary: {len(names)} skills, {failures} arbitration/collision finding(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
