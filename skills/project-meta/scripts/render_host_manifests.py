#!/usr/bin/env python3
"""Generate per-host plugin manifests from the canonical AGENTS.md / CLAUDE.md.

Different agent hosts (Claude Code, Cursor, OpenAI Codex, GitHub Copilot
CLI, Gemini CLI, OpenCode) discover the project via different manifest
files. This script generates the host-specific shims from one canonical
source so they don't drift.

Inputs:
    --canonical PATH    The canonical project-memory file. Default: auto-
                        detect (AGENTS.md, then CLAUDE.md).
    --target-root PATH  Repo root. Default: cwd.
    --hosts LIST        Comma-separated host targets. Default: all
                        supported. Choices below.
    --dry-run           Print what would change without writing.

Supported hosts (and the manifest each emits):

    claude       .claude/instructions.md         (mirror of canonical)
    copilot      .github/copilot-instructions.md (mirror of canonical)
    codex        AGENTS.md                       (canonical when applicable)
    cursor       .cursor/rules/agents.md         (mirror of canonical)
    opencode     .opencode/instructions.md       (mirror of canonical)
    gemini       gemini-extension.json + .gemini/instructions.md
    codex-subagents  .codex/agents/{explorer,worker,reviewer}.toml
                 (Codex-side mechanical backing of the multi-agent
                 dispatch protocol — role configs, NOT a memory mirror)

The default --hosts set is the memory-mirror hosts above (everything
except codex-subagents).
`codex-subagents` is opt-in: pass `--hosts codex-subagents` explicitly. It
emits role-config TOML seeds (template-based, not derived from canonical
memory) that operationalize multi-agent-protocols.md on Codex. The exact
TOML keys may need adjustment to your Codex CLI version's agent schema;
the emitted files carry a banner saying so.

Notes:

- The canonical file is never overwritten by this script. Only the
  host-specific mirrors and (for codex-subagents) role configs are emitted.
- Each generated mirror carries a top-banner comment naming the
  canonical source and the generation timestamp; agents and humans
  reading the mirror know it's auto-generated.
- For hosts that expect JSON manifests (Gemini), the script writes a
  thin pointer that references the markdown instructions file, not the
  full prose.

Exit codes:
    0  success (or dry-run that would have succeeded)
    1  canonical file missing or unreadable
    2  bad CLI usage
    3  one or more host emissions failed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path


HOSTS: dict[str, dict] = {
    "claude": {
        "path": ".claude/instructions.md",
        "kind": "markdown",
        "comment": "<!-- generated from {canonical} on {ts} by project-meta render_host_manifests.py — do not edit -->",
    },
    "copilot": {
        "path": ".github/copilot-instructions.md",
        "kind": "markdown",
        "comment": "<!-- generated from {canonical} on {ts} by project-meta render_host_manifests.py — do not edit -->",
    },
    "codex": {
        "path": "AGENTS.md",
        "kind": "canonical-or-mirror",
        "comment": "<!-- generated from {canonical} on {ts} by project-meta render_host_manifests.py — do not edit -->",
    },
    "cursor": {
        "path": ".cursor/rules/agents.md",
        "kind": "markdown",
        "comment": "<!-- generated from {canonical} on {ts} by project-meta render_host_manifests.py — do not edit -->",
    },
    "opencode": {
        "path": ".opencode/instructions.md",
        "kind": "markdown",
        "comment": "<!-- generated from {canonical} on {ts} by project-meta render_host_manifests.py — do not edit -->",
    },
    "gemini": {
        "path": "gemini-extension.json",
        "kind": "gemini-pair",
        "comment": "",
    },
    "codex-subagents": {
        "path": ".codex/agents/",
        "kind": "codex-subagents",
        "comment": "",
    },
}

# Memory-mirror hosts emitted by default. `codex-subagents` is opt-in.
DEFAULT_HOSTS = [h for h in HOSTS if h != "codex-subagents"]

# Role-config seeds for the Codex-side backing of the dispatch protocol
# (multi-agent-protocols.md). Template-based, not derived from canonical
# memory. Per-task write-sets are assigned by the orchestrator's brief;
# these encode only role-level read/write capability.
CODEX_SUBAGENT_ROLES: dict[str, str] = {
    "explorer": (
        '[agents.explorer]\n'
        'role = "explorer"  # read-only; never edits files\n'
        'description = "Read-only exploration and narrow Q&A. Returns findings only."\n'
        'instructions = """\n'
        'You are an Explorer (read-only). Answer the narrow question in your brief.\n'
        'Do NOT edit files. Return findings only. See AGENTS.md and the project\n'
        'dispatch protocol (multi-agent-protocols.md) for roles and ownership.\n'
        '"""\n'
    ),
    "worker": (
        '[agents.worker]\n'
        'role = "worker"  # read-write; edits ONLY the files named in the brief\n'
        'description = "Bounded editor. Edits only its assigned write-set, returns a patch summary."\n'
        'instructions = """\n'
        'You are a Worker. Edit ONLY the files your brief assigns (its write-set).\n'
        'Do not expand scope, refactor adjacent code, or add dependencies. Produce\n'
        'a patch summary and stop. The reviewer (separate agent) checks your diff.\n'
        '"""\n'
    ),
    "reviewer": (
        '# Derived/custom agent named "reviewer"; base role is "default"\n'
        '# because Codex has no native reviewer role. Table-name (reviewer)\n'
        '# and role-field (default) are different axes — this is intentional.\n'
        '[agents.reviewer]\n'
        'role = "default"  # read-only reviewer; does not edit (advisory — back with sandbox config)\n'
        'description = "Reviews a worker diff against its brief. Returns PASS / SUGGEST / BLOCKER."\n'
        'instructions = """\n'
        'You are a Reviewer with fresh context: you see only the brief, the diff, and\n'
        'the success criterion — not the conductor context. Return one verdict:\n'
        'PASS | SUGGEST | BLOCKER. BLOCKER is a synchronous halt: stop the chain and\n'
        'surface to the user; do not let further edits land. Do not edit files yourself.\n'
        '"""\n'
    ),
}


def detect_canonical(target_root: Path) -> Path | None:
    for name in ("AGENTS.md", "CLAUDE.md"):
        candidate = target_root / name
        if candidate.is_file():
            return candidate
    return None


def banner(canonical: Path, ts: str, host_kind: str) -> str:
    if host_kind == "json":
        return ""
    return (
        f"<!-- generated from {canonical.name} on {ts} by "
        f"project-meta render_host_manifests.py — do not edit -->\n\n"
    )


def emit_markdown_mirror(out_path: Path, canonical: Path, ts: str,
                         dry_run: bool) -> tuple[bool, str]:
    body = canonical.read_text(encoding="utf-8")
    content = banner(canonical, ts, "markdown") + body
    if dry_run:
        return True, f"would write {out_path} ({len(content)} chars)"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return True, f"wrote {out_path} ({len(content)} chars)"


def emit_codex(out_path: Path, canonical: Path, ts: str,
               dry_run: bool) -> tuple[bool, str]:
    # Codex reads AGENTS.md natively. If canonical IS already AGENTS.md,
    # nothing to emit. Otherwise mirror canonical to AGENTS.md.
    if canonical.name == "AGENTS.md":
        return True, "codex: canonical is AGENTS.md; no mirror needed"
    return emit_markdown_mirror(out_path, canonical, ts, dry_run)


def emit_gemini(target_root: Path, canonical: Path, ts: str,
                dry_run: bool) -> tuple[bool, str]:
    # Gemini wants a JSON extension file pointing at instructions.
    json_path = target_root / "gemini-extension.json"
    md_path = target_root / ".gemini/instructions.md"
    extension = {
        "name": target_root.name,
        "version": "1",
        "instructions": ".gemini/instructions.md",
        "_generated_from": canonical.name,
        "_generated_at": ts,
        "_generator": "project-meta render_host_manifests.py",
    }
    md_content = (
        f"<!-- generated from {canonical.name} on {ts} -->\n\n"
        + canonical.read_text(encoding="utf-8")
    )
    if dry_run:
        return True, (
            f"would write {json_path} (gemini extension manifest) and "
            f"{md_path} ({len(md_content)} chars)"
        )
    json_path.write_text(
        json.dumps(extension, indent=2) + "\n", encoding="utf-8"
    )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_content, encoding="utf-8")
    return True, f"wrote {json_path} + {md_path}"


def emit_codex_subagents(target_root: Path, canonical: Path, ts: str,
                         dry_run: bool) -> tuple[bool, str]:
    # Emit role-config seeds under .codex/agents/. These are template-based
    # (not memory-derived); they back the dispatch protocol on Codex.
    agents_dir = target_root / ".codex/agents"
    banner_line = (
        f"# generated from {canonical.name} on {ts} by project-meta "
        f"render_host_manifests.py\n"
        f"# Role-config SEED for the multi-agent dispatch protocol "
        f"(multi-agent-protocols.md).\n"
        f"# Adjust keys to match your Codex CLI version's agent schema; "
        f"per-task write-sets come from the brief, not this file.\n\n"
    )
    written = []
    for role, body in CODEX_SUBAGENT_ROLES.items():
        out_path = agents_dir / f"{role}.toml"
        content = banner_line + body
        if dry_run:
            written.append(f"{out_path} ({len(content)} chars)")
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        written.append(str(out_path))
    verb = "would write" if dry_run else "wrote"
    return True, f"codex-subagents: {verb} {', '.join(written)}"


EMITTERS = {
    "claude": emit_markdown_mirror,
    "copilot": emit_markdown_mirror,
    "codex": emit_codex,
    "cursor": emit_markdown_mirror,
    "opencode": emit_markdown_mirror,
    "gemini": emit_gemini,
    "codex-subagents": emit_codex_subagents,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--canonical", type=Path, default=None)
    parser.add_argument("--target-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--hosts",
        default=",".join(DEFAULT_HOSTS),
        help=(
            "Comma-separated host names. Default: the memory-mirror hosts "
            "(all except codex-subagents). 'codex-subagents' is opt-in — "
            "name it explicitly."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    target_root = args.target_root.resolve()
    canonical = (
        args.canonical.resolve() if args.canonical
        else detect_canonical(target_root)
    )
    if canonical is None or not canonical.is_file():
        sys.stderr.write(
            f"render_host_manifests: no canonical project-memory file at "
            f"{target_root}. Expected AGENTS.md or CLAUDE.md, or pass "
            f"--canonical PATH.\n"
        )
        return 1

    hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]
    unknown = [h for h in hosts if h not in HOSTS]
    if unknown:
        sys.stderr.write(
            f"render_host_manifests: unknown hosts: {unknown}. "
            f"Known: {sorted(HOSTS)}\n"
        )
        return 2

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    failed = 0
    for host in hosts:
        spec = HOSTS[host]
        emitter = EMITTERS[host]
        try:
            if host in ("gemini", "codex-subagents"):
                ok, msg = emitter(target_root, canonical, ts, args.dry_run)
            else:
                out_path = target_root / spec["path"]
                ok, msg = emitter(out_path, canonical, ts, args.dry_run)
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"{host} emission failed: {e}"
        prefix = "  " if ok else "  FAIL "
        print(prefix + f"[{host}] {msg}")
        if not ok:
            failed += 1

    if failed:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
