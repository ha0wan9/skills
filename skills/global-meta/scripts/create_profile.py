#!/usr/bin/env python3
"""
create_profile.py — scaffold a new Claude Code or Codex config profile.

global-meta `create` verb. Absorbed from the former `profile-creator` skill and
generalized to both runtimes via a small RuntimeAdapter.

runtime=claude (default):
  ~/.claude-<name>/            profile config dir (CLAUDE_CONFIG_DIR)
  ~/.claude-<name>/plugins     symlink -> ~/.claude-shared/plugins   (required)
  ~/.local/bin/claude-<name>   launcher (chmod +x)

runtime=codex:
  ~/.codex-<name>/             profile config dir (CODEX_HOME)
  ~/.local/bin/codex-<name>    launcher (chmod +x)
  ~/.codex-<name>/plugins      symlink -> ~/.codex-shared/plugins   (only if it
                               exists; the Codex shared-plugin model is unverified
                               — see proposals/global-meta.md §10)

Optionally seeds memory files from an existing profile of the SAME runtime
(--seed-from). claude seeds CLAUDE.md/RTK.md; codex seeds AGENTS.md/RTK.md.
"""

import argparse
import shutil
import sys
import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# Launcher bodies. Placeholders: {var} config-home env var, {rt} runtime token,
# {name} profile name, {bin} exec binary, {extra_unset} runtime-specific unsets.
LAUNCHER_SIMPLE = """\
#!/usr/bin/env bash
export {var}="$HOME/.{rt}-{name}"
if [ -f "$HOME/.config/{rt}-{name}/env" ]; then
  source "$HOME/.config/{rt}-{name}/env"
fi
exec {bin} "$@"
"""

LAUNCHER_ISOLATED = """\
#!/usr/bin/env bash
export {var}="$HOME/.{rt}-{name}"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
{extra_unset}unset GITHUB_TOKEN GOOGLE_APPLICATION_CREDENTIALS
unset SLACK_BOT_TOKEN LINEAR_API_KEY JIRA_API_TOKEN CONFLUENCE_API_TOKEN
if [ -f "$HOME/.config/{rt}-{name}/env" ]; then
  source "$HOME/.config/{rt}-{name}/env"
fi
exec {bin} "$@"
"""

# RuntimeAdapter: one entry per runtime. The claude entry reproduces the former
# profile-creator behavior byte-for-byte (extra_unset="" -> identical launcher).
ADAPTERS = {
    "claude": dict(
        env_var="CLAUDE_CONFIG_DIR",
        bin="claude",
        shared_root=".claude-shared",
        seed_files=("CLAUDE.md", "RTK.md"),
        plugins_required=True,        # proven prerequisite
        extra_unset="",
    ),
    "codex": dict(
        env_var="CODEX_HOME",
        bin="codex",
        shared_root=".codex-shared",
        seed_files=("AGENTS.md", "RTK.md"),  # AGENTS.md is Codex's canonical memory
        plugins_required=False,       # Codex shared-plugin model unverified (§10)
        extra_unset="unset OPENAI_API_KEY\n",
    ),
}


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


def check_prerequisites(rt: str, ad: dict, name: str, seed_from, dry_run: bool) -> None:
    home = Path.home()
    profile_dir = home / f".{rt}-{name}"
    if profile_dir.exists():
        die(
            f"Profile directory {profile_dir} already exists.\n"
            "  Remediation: choose a different name, or remove it manually to\n"
            f"  start fresh: rm -rf {profile_dir}"
        )

    shared_plugins = home / ad["shared_root"] / "plugins"
    if not shared_plugins.exists():
        msg = (
            f"Shared plugins directory {shared_plugins} does not exist.\n"
            f"  Remediation: create ~/{ad['shared_root']}/plugins/ first, or run\n"
            "  the shared-store setup before creating profiles."
        )
        if ad["plugins_required"] and not dry_run:
            die(msg)
        # codex (not required) or dry-run: warn and continue
        print(f"[{'dry-run' if dry_run else 'note'}] {msg}")

    if seed_from is not None:
        seed_dir = home / f".{rt}-{seed_from}"
        if not seed_dir.exists():
            die(
                f"Seed profile directory {seed_dir} does not exist.\n"
                f"  Remediation: check the name; existing profiles are ~/.{rt}-* dirs."
            )


def create_profile(rt: str, ad: dict, name: str, isolated: bool, seed_from, dry_run: bool) -> None:
    home = Path.home()
    profile_dir = home / f".{rt}-{name}"
    plugins_link = profile_dir / "plugins"
    shared_plugins = home / ad["shared_root"] / "plugins"
    bin_dir = home / ".local" / "bin"
    launcher_path = bin_dir / f"{rt}-{name}"
    body_tmpl = LAUNCHER_ISOLATED if isolated else LAUNCHER_SIMPLE
    launcher_body = body_tmpl.format(
        var=ad["env_var"], rt=rt, name=name, bin=ad["bin"], extra_unset=ad["extra_unset"]
    )

    actions: list[str] = []

    def run(label: str, fn):
        if dry_run:
            print(f"[dry-run] {label}")
        else:
            fn()
            actions.append(label)

    # 1. Profile dir
    run(f"mkdir {profile_dir}", lambda: profile_dir.mkdir(parents=True, exist_ok=False))

    # 2. Plugins symlink — only when the shared store exists. For claude this is a
    #    hard prerequisite (already enforced); for codex it is best-effort.
    if shared_plugins.exists() or dry_run:
        run(f"ln -s {shared_plugins} {plugins_link}",
            lambda: plugins_link.symlink_to(shared_plugins))
    else:
        print(f"[skip] {shared_plugins} absent; plugins symlink not created ({rt})")

    # 3. Launcher
    run(f"mkdir -p {bin_dir}", lambda: bin_dir.mkdir(parents=True, exist_ok=True))
    run(f"write {launcher_path}", lambda: launcher_path.write_text(launcher_body))
    run(f"chmod +x {launcher_path}",
        lambda: launcher_path.chmod(launcher_path.stat().st_mode | 0o111))

    # 4. Optional seed copy (runtime-specific canonical memory files)
    if seed_from is not None:
        seed_dir = home / f".{rt}-{seed_from}"
        for fname in ad["seed_files"]:
            src, dst = seed_dir / fname, profile_dir / fname
            if src.exists():
                run(f"cp {src} {dst}", lambda s=src, d=dst: shutil.copy2(s, d))
            else:
                print(f"[skip] {fname} not found in {seed_dir}, skipping seed copy")

    # 5. Symlink the global-meta skill into the profile (if present in the shared store)
    skills_dir = profile_dir / "skills"
    shared_skill = home / ad["shared_root"] / "skills" / "global-meta"
    skill_link = skills_dir / "global-meta"
    if shared_skill.exists():
        run(f"mkdir {skills_dir}", lambda: skills_dir.mkdir(exist_ok=True))
        run(f"ln -s {shared_skill} {skill_link}",
            lambda: skill_link.symlink_to(shared_skill))
    else:
        print(f"[skip] {shared_skill} not found; global-meta skill not symlinked")

    # Summary
    if dry_run:
        print("\n[dry-run] No changes made. Remove --dry-run to apply.")
    else:
        print(f"\nProfile '{rt}-{name}' created successfully.")
        for a in actions:
            print(f"  {a}")
        print(f"\nLauncher form : {'isolated' if isolated else 'simple'}")
        print(f"Launch with   : {rt}-{name}   (open a fresh terminal first)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold a new Claude Code or Codex config profile (global-meta create).\n\n"
            "claude: ~/.claude-<name>/ + plugins symlink + ~/.local/bin/claude-<name>.\n"
            "codex:  ~/.codex-<name>/  + ~/.local/bin/codex-<name> (plugins best-effort)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "name",
        help=(
            "Profile name — lowercase letters, digits, hyphens; must start with a "
            "letter or digit. Do NOT include the 'claude-'/'codex-' prefix."
        ),
    )
    parser.add_argument(
        "--runtime", choices=sorted(ADAPTERS), default="claude",
        help="Target runtime (default: claude).",
    )
    parser.add_argument(
        "--isolated", action="store_true", default=False,
        help=(
            "Use the isolated launcher form, which unsets common API/token env vars "
            "before exec-ing the runtime. Default: simple form (inherits env)."
        ),
    )
    parser.add_argument(
        "--seed-from", metavar="PROFILE", default=None,
        help=(
            "Copy the runtime's canonical memory files from a same-runtime profile "
            "(~/.<runtime>-<PROFILE>/) into the new profile. PROFILE must exist."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print what would be done without making any changes.",
    )

    args = parser.parse_args()
    rt = args.runtime
    ad = ADAPTERS[rt]
    validate_name(args.name)
    check_prerequisites(rt, ad, args.name, args.seed_from, args.dry_run)
    create_profile(rt, ad, args.name, args.isolated, args.seed_from, args.dry_run)


if __name__ == "__main__":
    main()
