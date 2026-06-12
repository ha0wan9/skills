#!/usr/bin/env python3
"""Memory staleness lint — deterministic, stdlib-only, no LLM.

Extracts referential claims from a repo's canonical memory file (AGENTS.md or
CLAUDE.md) and any agents/*.md topical files, then checks whether each cited
path, script, or command token actually exists in the repo tree.

CLI:
    python3 memory_staleness.py [--target-root <repo>]  (default: .)

Output: one TSV line per claim:
    STATUS<TAB>claim<TAB>source-file:line

Status values:
    OK      — cited path/file exists in the repo tree
    STALE   — cited path/file is absent from the repo tree
    UNKNOWN — unresolvable or ambiguous (glob, external URL, bare command
              name, env-var token, or any path containing < > * $ — never
              guess these)

Summary line (to stdout):
    staleness: N ok, N stale, N unknown

Exit: 1 iff ≥1 STALE; 0 otherwise.

Design:
    Conservative over aggressive — prefer UNKNOWN to false STALE.
    Only tokens that look like repo-relative paths (contain a '/' *or* end in
    .py/.sh/.json/.md/.yaml/.yml) are resolved; bare command names like "git",
    "python3", "bash" are always UNKNOWN/skipped.
    Any token containing shell metacharacters (< > * $ ? [ ] ! {) or ://
    (URL) is UNKNOWN.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Claim extraction helpers
# ---------------------------------------------------------------------------

# Shell metacharacters and URL fragments that make a token unresolvable.
_UNSAFE_CHARS = re.compile(r'[<>*$?!\[\]{}]')
_URL_LIKE = re.compile(r'\w+://')

# Markdown link: [text](target) — capture target
_MD_LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')

# Bare filename with extension we care about (no directory component required)
_BARE_EXT = re.compile(r'\b([\w.\-/]+\.(?:py|sh|json|md|yaml|yml))\b')

# Command invocations: "python3 path/to/script.py", "bash path/to/script.sh"
# We want the *path* token after the command, not the command itself.
_CMD_PATH = re.compile(
    r'\b(?:python3?|bash|sh|node|ruby|perl)\s+([\w.\-/]+\.(?:py|sh|rb|pl|js))\b'
)


def _is_safe_token(token: str) -> bool:
    """Return True iff the token is concrete enough to resolve."""
    token = token.strip()
    if not token:
        return False
    if _UNSAFE_CHARS.search(token):
        return False
    if _URL_LIKE.search(token):
        return False
    # Markdown/rst anchors like #section
    if token.startswith('#'):
        return False
    # Absolute paths to system dirs are not repo-relative claims
    if token.startswith('/') and not any(
        token.startswith(p) for p in ('/Users', '/home', '/tmp')
    ):
        return False
    return True


def _strip_md_link_target(token: str) -> str:
    """Strip leading ./ from a markdown link target."""
    if token.startswith('./'):
        return token[2:]
    return token


def _extract_claims(text: str, source_label: str) -> list[tuple[str, str]]:
    """Return list of (raw_token, source_file:line) tuples from *text*.

    source_label is the display label (e.g. "AGENTS.md").

    Extraction sources (in order of confidence):
    1. Markdown links [text](target) — explicit references; always extracted.
    2. Command invocation paths inside code fences: ``python3 path/to/script.py``
       — only inside triple-backtick fenced blocks to avoid prose shorthand.
    3. Path tokens inside fenced code blocks that contain a '/' (directory
       separator) — must have an explicit '/' to avoid bare filenames that
       are shorthand descriptions rather than repo-root paths.

    Inline backticks in prose (e.g. ``scripts/foo.py`` in a bullet point
    describing a skill's internal path) are deliberately NOT extracted because
    they are frequently shorthand relative to the skill's own directory, not
    to the repo root, and would produce false STALE results.
    """
    claims: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _emit(token: str, lineno: int) -> None:
        token = token.strip().rstrip('.,;)')
        token = _strip_md_link_target(token)
        if not token or token in seen:
            return
        seen.add(token)
        claims.append((token, f"{source_label}:{lineno}"))

    lines = text.splitlines()
    in_fence = False
    fence_marker = ""

    for lineno, line in enumerate(lines, 1):
        # Track triple-backtick code fences.
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            # Don't extract from the fence delimiter line itself.
            continue

        # 1. Markdown links [text](target) — extract from any line (inside or
        #    outside fences). These are explicit, unambiguous references.
        if not in_fence:
            for m in _MD_LINK.finditer(line):
                target = m.group(1).strip()
                # strip in-page anchors
                if '#' in target:
                    target = target.split('#')[0]
                if target and _is_safe_token(target):
                    _emit(target, lineno)

        # 2 & 3. Inside code fences: extract command paths and path tokens.
        if in_fence:
            # Command invocations: python3 scripts/foo.py
            for m in _CMD_PATH.finditer(line):
                token = m.group(1).strip()
                if _is_safe_token(token):
                    _emit(token, lineno)
            # Any token with a '/' that looks like an extension-bearing path.
            # Require '/' so bare names like "validate_project_meta.py" are
            # skipped — they could be shorthand for any subdirectory.
            for m in _BARE_EXT.finditer(line):
                token = m.group(1).strip()
                if '/' in token and _is_safe_token(token):
                    _emit(token, lineno)

    return claims


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def _resolve(token: str, root: Path) -> str:
    """Return OK / STALE / UNKNOWN for a single token.

    Conservative strategy:
    - If the path exists under root → OK
    - If the path does NOT exist but the first path component IS a real
      top-level directory/file in root → STALE (the prefix is anchored)
    - Otherwise → UNKNOWN (too ambiguous to call stale)

    This prevents shorthand paths like ``scripts/foo.py`` (which are
    relative to a skill subdir, not the repo root) from being falsely
    reported as STALE when the repo root has no ``scripts/`` dir.
    """
    # Final safety guard: reject tokens with unsafe chars or URL patterns.
    if _UNSAFE_CHARS.search(token) or _URL_LIKE.search(token):
        return "UNKNOWN"
    # Tokens that look like bare command names (no '/' and no extension we check)
    # are UNKNOWN — we don't try to resolve system commands.
    if '/' not in token and not any(token.endswith(ext) for ext in
                                    ('.py', '.sh', '.json', '.md', '.yaml', '.yml')):
        return "UNKNOWN"
    candidate = (root / token).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return "UNKNOWN"
    if candidate.exists():
        return "OK"
    # Path doesn't exist — only call it STALE if the first component is
    # a real top-level entry in the root (anchors the path to this repo).
    parts = Path(token).parts
    if parts and (root / parts[0]).exists():
        return "STALE"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_log_date(root: Path, rel_path: str) -> str | None:
    """Return the YYYY-MM-DD of the last commit touching rel_path, or None."""
    try:
        p = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%cs", "--", rel_path],
            capture_output=True,
            text=True,
            check=False,
        )
        date = p.stdout.strip()
        if p.returncode == 0 and date:
            return date
    except FileNotFoundError:
        pass
    return None


def _is_git(root: Path) -> bool:
    try:
        p = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        return p.returncode == 0
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

ENTRYPOINTS = ("CLAUDE.md", "AGENTS.md")


def _collect_memory_files(root: Path) -> list[Path]:
    """Return the canonical entrypoint(s) + agents/*.md topical files."""
    files: list[Path] = []
    for name in ENTRYPOINTS:
        p = root / name
        if p.is_file():
            files.append(p)
    agents_dir = root / "agents"
    if agents_dir.is_dir():
        files.extend(sorted(p for p in agents_dir.glob("*.md") if p.is_file()))
    return files


def run(target_root: str) -> int:
    root = Path(target_root).expanduser().resolve()
    in_git = _is_git(root)

    memory_files = _collect_memory_files(root)
    if not memory_files:
        print("staleness: 0 ok, 0 stale, 0 unknown")
        print("[staleness] no canonical memory file found; skipping lint", file=sys.stderr)
        return 0

    rows: list[tuple[str, str, str]] = []  # (status, token, source_label)

    for mf in memory_files:
        try:
            text = mf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(mf.relative_to(root))
        # Annotate the entrypoint itself with git-log age when available
        if mf.name in ENTRYPOINTS and in_git:
            date = _git_log_date(root, rel)
            if date:
                print(f"[staleness] {rel} last modified in git: {date}")

        claims = _extract_claims(text, rel)
        for token, source_loc in claims:
            status = _resolve(token, root)
            rows.append((status, token, source_loc))

    # Deduplicate by (token, source_loc) — same token from same file+line only once.
    seen_keys: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str, str]] = []
    for status, token, source_loc in rows:
        key = (token, source_loc)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append((status, token, source_loc))

    n_ok = sum(1 for s, _, _ in deduped if s == "OK")
    n_stale = sum(1 for s, _, _ in deduped if s == "STALE")
    n_unknown = sum(1 for s, _, _ in deduped if s == "UNKNOWN")

    for status, token, source_loc in deduped:
        print(f"{status}\t{token}\t{source_loc}")

    print(f"staleness: {n_ok} ok, {n_stale} stale, {n_unknown} unknown")

    return 1 if n_stale >= 1 else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0]
    )
    parser.add_argument(
        "--target-root",
        default=".",
        help="repo root to lint (default: current directory)",
    )
    args = parser.parse_args(argv)
    return run(args.target_root)


if __name__ == "__main__":
    sys.exit(main())
