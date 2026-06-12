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
        # NB: do NOT .strip() — it would lstrip the first porcelain line's
        # leading status space (" M file"), corrupting line[3:] in _changed_files.
        return p.returncode, p.stdout
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
    # --untracked-files=all so new untracked dirs list files individually
    # (git otherwise collapses "agents/x.md" to "agents/").
    code, out = _git(root, "status", "--porcelain", "--untracked-files=all")
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
        # Advisory: note staleness if present (does not block writeback).
        _print_staleness_hint(root)
        return 1
    return 0


def _print_staleness_hint(root: Path) -> None:
    """Print a one-line advisory if the memory files have STALE citations."""
    try:
        import importlib.util
        import io
        from contextlib import redirect_stdout

        scripts_dir = Path(__file__).parent
        spec = importlib.util.spec_from_file_location(
            "memory_staleness",
            scripts_dir / "memory_staleness.py",
        )
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = mod.run(str(root))
        if exit_code != 0:
            print(
                "[staleness] advisory: memory files have STALE citations — "
                "consider running memory_staleness.py to review before writing back.",
                file=sys.stderr,
            )
    except Exception:  # noqa: BLE001
        pass


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

    # --- Staleness lint (advisory) ---
    # Import from the same directory; fall back gracefully if unavailable.
    _run_staleness_advisory(root)

    return 0


def _run_staleness_advisory(root: Path) -> None:
    """Run memory_staleness lint and print summary as advisory output.

    STALE findings are printed as advisory only — they do NOT flip the
    validate exit code to 1 in this version. The summary line is always
    printed so downstream greps can verify wiring.
    """
    try:
        import importlib.util
        import os

        scripts_dir = Path(__file__).parent
        spec = importlib.util.spec_from_file_location(
            "memory_staleness",
            scripts_dir / "memory_staleness.py",
        )
        if spec is None or spec.loader is None:
            print("[staleness] advisory: memory_staleness.py not found; skipping")
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        # Redirect mod's stdout to capture its lines, then replay them.
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = mod.run(str(root))
        output = buf.getvalue()

        for line in output.splitlines():
            if line.startswith("staleness:"):
                print(f"[staleness] {line}")
            elif line.startswith("[staleness]"):
                # date annotations from the module itself
                print(line)
            # individual OK/STALE/UNKNOWN rows are omitted from validate
            # output to keep it concise; the summary line is sufficient.

        if exit_code != 0:
            print(
                "[staleness] advisory: STALE citations found in memory files "
                "(run memory_staleness.py directly for details — not blocking validate)"
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[staleness] advisory: lint skipped ({exc})")


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
