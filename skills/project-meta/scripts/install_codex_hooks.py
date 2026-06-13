#!/usr/bin/env python3
"""Install Project Meta's hook pack into Codex's global hooks.json.

This is the Codex backing for templates/hooks/README.md. It copies the
portable shell hooks into ~/.codex/hooks/project-meta/ and merges hook
entries into ~/.codex/hooks.json without removing existing hooks.

It intentionally does not pre-populate Codex's hook trust state in
config.toml. Trust hashing is Codex-owned; the first run may ask the user
to approve the new hook commands.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
HOOK_SOURCE_DIR = SKILL_DIR / "templates" / "hooks" / "scripts"

HOOK_SCRIPTS = {
    "load-agents-md.sh": "SessionStart",
    "format-on-edit.sh": "PostToolUse",
    "provenance-on-edit.sh": "PostToolUse",
    "verify-before-stop.sh": "Stop",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home directory. Default: $CODEX_HOME or ~/.codex.",
    )
    p.add_argument(
        "--project-meta-dir",
        type=Path,
        default=SKILL_DIR,
        help="Installed project-meta skill directory used by hooks.",
    )
    p.add_argument(
        "--profile",
        choices=("minimal", "standard", "strict"),
        default="standard",
        help="HARNESS_PROFILE value injected into hook commands.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned writes without modifying files.",
    )
    return p.parse_args()


def load_hooks_json(path: Path) -> dict:
    if not path.exists():
        return {"hooks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"{path}: hooks must be a JSON object")
    return data


def command(profile: str, project_meta_dir: Path, hook_path: Path) -> str:
    return (
        f"HARNESS_PROFILE={profile} "
        f"PROJECT_META_DIR={project_meta_dir} "
        f"bash {hook_path}"
    )


def hook_entry(event: str, command_text: str) -> dict:
    matcher = "*"
    timeout = 5
    if event == "PostToolUse":
        matcher = "Edit|Write|MultiEdit"
        timeout = 30
    elif event == "Stop":
        timeout = 120
    return {
        "matcher": matcher,
        "hooks": [
            {
                "type": "command",
                "command": command_text,
                "timeout": timeout,
            }
        ],
    }


def merge_hook(data: dict, event: str, entry: dict) -> str:
    hooks = data.setdefault("hooks", {})
    event_entries = hooks.setdefault(event, [])
    if not isinstance(event_entries, list):
        raise SystemExit(f"hooks.{event} must be a list")

    new_cmd = entry["hooks"][0]["command"]
    script_name = Path(new_cmd.split()[-1]).name
    for idx, existing in enumerate(event_entries):
        existing_hooks = existing.get("hooks", [])
        if not isinstance(existing_hooks, list):
            continue
        for h in existing_hooks:
            old_cmd = h.get("command", "")
            if old_cmd == new_cmd or f"/project-meta/{script_name}" in old_cmd:
                event_entries[idx] = entry
                return "updated"
    event_entries.append(entry)
    return "added"


def install_scripts(dest_dir: Path, dry_run: bool) -> list[str]:
    actions = []
    for script_name in HOOK_SCRIPTS:
        src = HOOK_SOURCE_DIR / script_name
        dst = dest_dir / script_name
        if not src.is_file():
            raise SystemExit(f"missing hook script: {src}")
        actions.append(f"copy {src} -> {dst}")
        if dry_run:
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        mode = dst.stat().st_mode
        dst.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return actions


def main() -> int:
    args = parse_args()
    codex_home = args.codex_home.expanduser().resolve()
    project_meta_dir = args.project_meta_dir.expanduser().resolve()
    hooks_dir = codex_home / "hooks" / "project-meta"
    hooks_json = codex_home / "hooks.json"

    if not project_meta_dir.is_dir():
        raise SystemExit(f"project-meta dir not found: {project_meta_dir}")

    actions = install_scripts(hooks_dir, args.dry_run)
    data = load_hooks_json(hooks_json)

    for script_name, event in HOOK_SCRIPTS.items():
        hook_path = hooks_dir / script_name
        cmd = command(args.profile, project_meta_dir, hook_path)
        action = merge_hook(data, event, hook_entry(event, cmd))
        actions.append(f"{action} {event} hook: {cmd}")

    if args.dry_run:
        for action in actions:
            print(f"DRY-RUN {action}")
        print(f"DRY-RUN would write {hooks_json}")
        return 0

    codex_home.mkdir(parents=True, exist_ok=True)
    hooks_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for action in actions:
        print(action)
    print(f"wrote {hooks_json}")
    print("note: Codex may ask you to trust these hook commands on first run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
