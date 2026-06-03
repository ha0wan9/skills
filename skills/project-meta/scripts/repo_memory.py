#!/usr/bin/env python3
"""Runtime repo-memory CLI — the single execution point for the memory
read/write-back protocol that every skill shares.

This script ships inside the ``project-meta`` skill. Dependent skills do NOT
vendor it; they resolve the installed ``project-meta`` directory and delegate
to it at runtime (see references/shared-cli-delegation.md). The SessionStart
and Stop hooks call it for the read leg and the write-back gate respectively.

Operates on a *target repo* (``--target-root``, default: cwd). Standard library
only. Profile-aware via ``$HARNESS_PROFILE`` (minimal disables the gate).

Subcommands:

    read         resolve the canonical memory entrypoint + topical routing
                 (the read leg — SessionStart hook prints this)
    writeback    deterministic write-back gate: if substantive files changed
                 but no memory file did and no ack marker exists, the lesson
                 decision is pending (the write leg — Stop hook calls this)
    write        format (and optionally append) a durable memory entry
    validate     sanity-check the memory surface (entrypoint present, USER.md
                 ignored)

Exit: read/validate/write 0 ok | 1 problem. writeback 0 = nothing pending,
1 = decision pending. 2 = bad invocation.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

# Canonical entrypoint candidates, in Claude-primary-first preference order.
ENTRYPOINTS = ("CLAUDE.md", "AGENTS.md")
MIRRORS = ("CLAUDE.md", ".github/copilot-instructions.md")
ACK_MARKER = ".harness/writeback-ack"
READ_CAP = 30  # bounded output to preserve context budget


def _profile() -> str:
    import os

    return os.environ.get("HARNESS_PROFILE", "standard")


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, ""


def _is_git(root: Path) -> bool:
    code, _ = _git(root, "rev-parse", "--is-inside-work-tree")
    return code == 0


def canonical_entrypoint(root: Path) -> str | None:
    for name in ENTRYPOINTS:
        if (root / name).is_file():
            return name
    return None


def _first_purpose(path: Path) -> str:
    """Best-effort one-line purpose: first non-heading, non-blank prose line."""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("---"):
                return s[:100]
    except OSError:
        pass
    return ""


def cmd_read(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    present = [n for n in ENTRYPOINTS if (root / n).is_file()]
    out: list[str] = []
    if len(present) > 1:
        # Both exist: one is canonical, the other is likely a thin mirror
        # (repo-memory-structure.md). Don't guess — surface both.
        out.append(
            f"[memory] entrypoints present: {', '.join(present)} — read the canonical one. "
            "CLAUDE.md is often a thin mirror of AGENTS.md; check before trusting it as the source."
        )
    elif present:
        out.append(f"[memory] canonical entrypoint: {present[0]} — read it before substantive work.")
    else:
        out.append("[memory] no CLAUDE.md/AGENTS.md found; create one before relying on repo memory.")
    agents_dir = root / "agents"
    if agents_dir.is_dir():
        topical = sorted(p for p in agents_dir.glob("*.md") if p.is_file())
        if topical:
            out.append("[memory] topical files (load only what the task needs):")
            for p in topical[: READ_CAP - len(out) - 2]:
                purpose = _first_purpose(p)
                out.append(f"  - agents/{p.name}" + (f" — {purpose}" if purpose else ""))
    if (root / "USER.md").is_file():
        out.append("[memory] local USER.md present — honor stated preferences.")
    if args.task:
        out.append(f"[memory] task hint: {args.task} — route to the matching topical file above.")
    print("\n".join(out[:READ_CAP]))
    return 0


def _changed_files(root: Path) -> list[str]:
    code, out = _git(root, "status", "--porcelain")
    if code != 0 or not out:
        return []
    files = []
    for line in out.splitlines():
        # porcelain: XY <path>  (or rename "old -> new")
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def _is_memory_file(rel: str) -> bool:
    if rel in ENTRYPOINTS or rel in MIRRORS or rel == "USER.md":
        return True
    return rel.startswith("agents/") and rel.endswith(".md")


WRITEBACK_BLOCK = """\
Durable lesson:
- <lesson>

Memory owner:
- <CLAUDE.md|AGENTS.md | agents/*.md | USER.md | none>

Writeback decision:
- <write now | suggest only | skip>

Reason:
- <why this will or will not matter again>"""


def cmd_writeback(args: argparse.Namespace) -> int:
    if _profile() == "minimal":
        return 0
    root = Path(args.target_root).expanduser().resolve()
    if not _is_git(root):
        return 0  # cannot gate without git history
    ack = root / ACK_MARKER
    if ack.is_file():
        # One-shot: honor the skip for exactly this turn, then consume the
        # marker so it cannot silently disable the gate on every future turn.
        try:
            ack.unlink()
        except OSError:
            pass
        return 0
    changed = _changed_files(root)
    if not changed:
        return 0  # nothing was done, nothing to capture
    substantive = [f for f in changed if not _is_memory_file(f)]
    memory_touched = any(_is_memory_file(f) for f in changed)
    if substantive and not memory_touched:
        print(
            "[memory] write-back decision pending: work changed files but no memory file was "
            f"updated and no {ACK_MARKER} marker exists.",
            file=sys.stderr,
        )
        print("[memory] decide write / suggest / skip using this block:", file=sys.stderr)
        print(WRITEBACK_BLOCK, file=sys.stderr)
        print(
            f"[memory] to clear: edit the memory owner, or `touch {ACK_MARKER}` for a one-shot skip (consumed this turn).",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    owner = (root / args.owner).resolve()
    try:
        owner.relative_to(root)
    except ValueError:
        print(f"--owner must stay inside target-root: {args.owner}", file=sys.stderr)
        return 2
    today = datetime.date.today().isoformat()
    entry = f"- ({today}) {args.lesson}"
    if args.why:
        entry += f" — {args.why}"
    if not args.apply:
        print("# dry-run (pass --apply to append to the owner file)")
        print(f"# owner: {owner}")
        print(entry)
        return 0
    if not owner.is_file():
        print(f"owner file does not exist: {owner}", file=sys.stderr)
        return 1
    with owner.open("a", encoding="utf-8") as fh:
        fh.write(("" if owner.read_text(encoding="utf-8").endswith("\n") else "\n") + entry + "\n")
    print(f"appended lesson to {args.owner}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    problems: list[str] = []
    entry = canonical_entrypoint(root)
    if not entry:
        problems.append("no canonical entrypoint (CLAUDE.md or AGENTS.md)")
    elif not (root / entry).read_text(encoding="utf-8", errors="replace").strip():
        problems.append(f"{entry} is empty")
    user = root / "USER.md"
    if user.is_file() and _is_git(root):
        code, _ = _git(root, "check-ignore", "USER.md")
        if code != 0:
            problems.append("USER.md present but not git-ignored (it is local-only)")
    if problems:
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1
    print(f"PASS memory surface ok (entrypoint: {entry})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target-root", default=".", help="repo to operate on (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="resolve entrypoint + topical routing (read leg)")
    p_read.add_argument("--task", help="optional task hint for routing")
    p_read.set_defaults(func=cmd_read)

    p_wb = sub.add_parser("writeback", help="deterministic write-back gate (write leg)")
    p_wb.set_defaults(func=cmd_writeback)

    p_write = sub.add_parser("write", help="format/append a durable memory entry")
    p_write.add_argument("--owner", required=True, help="memory file, relative to target-root")
    p_write.add_argument("--lesson", required=True)
    p_write.add_argument("--why")
    p_write.add_argument("--apply", action="store_true", help="append (default: dry-run)")
    p_write.set_defaults(func=cmd_write)

    p_val = sub.add_parser("validate", help="sanity-check the memory surface")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
