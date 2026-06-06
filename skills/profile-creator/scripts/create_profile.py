#!/usr/bin/env python3
"""
create_profile.py — scaffold a new Claude Code config profile.

Creates:
  ~/.claude-<name>/            profile config dir
  ~/.claude-<name>/plugins     symlink → ~/.claude-shared/plugins
  ~/.local/bin/claude-<name>   launcher script (chmod +x)

Optionally seeds memory files from an existing profile (--seed-from).
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

LAUNCHER_SIMPLE = """\
#!/usr/bin/env bash
export CLAUDE_CONFIG_DIR="$HOME/.claude-{name}"
if [ -f "$HOME/.config/claude-{name}/env" ]; then
  source "$HOME/.config/claude-{name}/env"
fi
exec claude "$@"
"""

LAUNCHER_ISOLATED = """\
#!/usr/bin/env bash
export CLAUDE_CONFIG_DIR="$HOME/.claude-{name}"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
unset GITHUB_TOKEN GOOGLE_APPLICATION_CREDENTIALS
unset SLACK_BOT_TOKEN LINEAR_API_KEY JIRA_API_TOKEN CONFLUENCE_API_TOKEN
if [ -f "$HOME/.config/claude-{name}/env" ]; then
  source "$HOME/.config/claude-{name}/env"
fi
exec claude "$@"
"""


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def validate_name(name: str) -> None:
    if not NAME_RE.match(name):
        die(
            f"Profile name {name!r} is invalid.\n"
            "  Remediation: use lowercase letters, digits, and hyphens only;\n"
            "  must start with a letter or digit (e.g. 'team', 'client-acme', 'oss2')."
        )


def check_prerequisites(name: str, seed_from: str | None) -> None:
    profile_dir = Path.home() / f".claude-{name}"
    if profile_dir.exists():
        die(
            f"Profile directory {profile_dir} already exists.\n"
            "  Remediation: choose a different name, or remove the existing\n"
            f"  directory manually if you want to start fresh: rm -rf {profile_dir}"
        )

    shared_plugins = Path.home() / ".claude-shared" / "plugins"
    if not shared_plugins.exists():
        die(
            f"Shared plugins directory {shared_plugins} does not exist.\n"
            "  Remediation: create ~/.claude-shared/plugins/ first, or run\n"
            "  the shared-store setup before creating profiles."
        )

    if seed_from is not None:
        seed_dir = Path.home() / f".claude-{seed_from}"
        if not seed_dir.exists():
            die(
                f"Seed profile directory {seed_dir} does not exist.\n"
                f"  Remediation: check the profile name; existing profiles are\n"
                f"  listed as ~/.claude-* directories in your home folder."
            )


def create_profile(name: str, isolated: bool, seed_from: str | None, dry_run: bool) -> None:
    home = Path.home()
    profile_dir = home / f".claude-{name}"
    plugins_link = profile_dir / "plugins"
    shared_plugins = home / ".claude-shared" / "plugins"
    bin_dir = home / ".local" / "bin"
    launcher_path = bin_dir / f"claude-{name}"
    launcher_body = (LAUNCHER_ISOLATED if isolated else LAUNCHER_SIMPLE).format(name=name)

    actions: list[str] = []

    def run(label: str, fn):
        if dry_run:
            print(f"[dry-run] {label}")
        else:
            fn()
            actions.append(label)

    # 1. Create profile dir
    run(f"mkdir {profile_dir}", lambda: profile_dir.mkdir(parents=True, exist_ok=False))

    # 2. Symlink plugins
    run(
        f"ln -s {shared_plugins} {plugins_link}",
        lambda: plugins_link.symlink_to(shared_plugins),
    )

    # 3. Write launcher
    run(f"mkdir -p {bin_dir}", lambda: bin_dir.mkdir(parents=True, exist_ok=True))
    run(
        f"write {launcher_path}",
        lambda: launcher_path.write_text(launcher_body),
    )
    run(
        f"chmod +x {launcher_path}",
        lambda: launcher_path.chmod(launcher_path.stat().st_mode | 0o111),
    )

    # 4. Optional seed copy
    if seed_from is not None:
        seed_dir = home / f".claude-{seed_from}"
        for fname in ("CLAUDE.md", "RTK.md"):
            src = seed_dir / fname
            dst = profile_dir / fname
            if src.exists():
                run(
                    f"cp {src} {dst}",
                    lambda s=src, d=dst: shutil.copy2(s, d),
                )
            else:
                print(f"[skip] {fname} not found in {seed_dir}, skipping seed copy")

    # 5. Symlink profile-creator skill
    skills_dir = profile_dir / "skills"
    shared_skill = home / ".claude-shared" / "skills" / "profile-creator"
    skill_link = skills_dir / "profile-creator"
    if shared_skill.exists():
        run(f"mkdir {skills_dir}", lambda: skills_dir.mkdir(exist_ok=True))
        run(
            f"ln -s {shared_skill} {skill_link}",
            lambda: skill_link.symlink_to(shared_skill),
        )
    else:
        print(f"[skip] {shared_skill} not found; profile-creator skill not symlinked")

    # Summary
    if dry_run:
        print("\n[dry-run] No changes made. Remove --dry-run to apply.")
    else:
        print(f"\nProfile 'claude-{name}' created successfully.")
        for a in actions:
            print(f"  {a}")
        launcher_form = "isolated" if isolated else "simple"
        print(f"\nLauncher form : {launcher_form}")
        print(f"Launch with   : claude-{name}   (open a fresh terminal first)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold a new Claude Code config profile.\n\n"
            "Creates ~/.claude-<name>/ with a plugins symlink to\n"
            "~/.claude-shared/plugins and a launcher at ~/.local/bin/claude-<name>."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "name",
        help=(
            "Profile name — lowercase letters, digits, hyphens; "
            "must start with a letter or digit. Do NOT include the 'claude-' prefix."
        ),
    )
    parser.add_argument(
        "--isolated",
        action="store_true",
        default=False,
        help=(
            "Use the isolated launcher form, which unsets common API/token env vars "
            "(ANTHROPIC_API_KEY, GITHUB_TOKEN, etc.) before exec-ing claude. "
            "Default: simple form (inherits env)."
        ),
    )
    parser.add_argument(
        "--seed-from",
        metavar="PROFILE",
        default=None,
        help=(
            "Copy CLAUDE.md and RTK.md from ~/.claude-<PROFILE>/ into the new profile. "
            "PROFILE must already exist."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print what would be done without making any changes.",
    )

    args = parser.parse_args()

    validate_name(args.name)
    check_prerequisites(args.name, args.seed_from)
    create_profile(args.name, args.isolated, args.seed_from, args.dry_run)


if __name__ == "__main__":
    main()
