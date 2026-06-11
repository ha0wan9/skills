#!/usr/bin/env python3
"""config_root_audit.py — read-only config-root inventory and audit for global-meta.

Verbs:
  status    Inventory of config root: profiles x runtimes, plugins (registry),
            hook entries in settings files, launchers, and context-tax estimate.
  audit     Everything status reads, plus four-way consistency findings with stable
            codes. Exit 0=clean, 1=findings, 2=error.
  snapshot  Copy the three stores into <--snapshot-root>/<UTC-timestamp>/.
  restore   List (--dry-run) or apply (--apply) files from the newest snapshot.

Layout conventions (fixture root uses dotless names; real root uses dot-prefixed):
  <config-home>/.claude-shared/plugins/installed_plugins.json
  <config-home>/.claude-shared/enabled-plugins.local.json
  <config-home>/.claude-shared/plugins/cache/<mkt>/<plugin>/<version>/
  <config-home>/.claude/settings.json  (default profile)
  <config-home>/.claude-<name>/settings.json  (named profiles)
  <config-home>/.local/bin/  (launchers)

  Under a fixture root (no dot prefix):
  <config-home>/claude-shared/plugins/installed_plugins.json
  ... etc.

Relative installPath values in the registry are resolved against --config-home.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _find_path(base: Path, dotted: str, dotless: str) -> Path:
    """Probe dot-prefixed first; fall back to dotless."""
    d = base / dotted
    if d.exists():
        return d
    return base / dotless


def resolve_stores(config_home: Path) -> dict:
    """Return absolute paths for the three canonical stores and cache root."""
    shared_dot = _find_path(config_home, ".claude-shared", "claude-shared")
    plugins_dir = shared_dot / "plugins"
    return {
        "installed_plugins": plugins_dir / "installed_plugins.json",
        "enabled_plugins": shared_dot / "enabled-plugins.local.json",
        "default_settings": _find_path(config_home, ".claude", "claude") / "settings.json",
        "cache_root": plugins_dir / "cache",
        "shared_root": shared_dot,
    }


def load_json(p: Path) -> dict | list | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_store_json(p: Path, what: str, *, required: bool) -> dict | None:
    """Strict loader for the core stores: malformed JSON is an ERROR (exit 2),
    never a finding (exit 1) or a silent {} — the audit cannot certify a store
    it could not parse. A missing optional store returns None."""
    if not p.exists():
        if required:
            print(f"error: {what} missing: {p}", file=sys.stderr)
            sys.exit(2)
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"error: {what} is malformed JSON ({e.__class__.__name__}): {p}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print(f"error: {what} is not a JSON object: {p}", file=sys.stderr)
        sys.exit(2)
    return data


def resolve_install_path(raw: str, config_home: Path) -> Path:
    """Relative installPath values resolve against config_home."""
    p = Path(raw)
    if p.is_absolute():
        return p
    return config_home / p


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def find_profiles(config_home: Path) -> list[dict]:
    """Discover Claude and Codex profiles (dot-prefixed and dotless patterns)."""
    profiles = []
    for item in sorted(config_home.iterdir()):
        name = item.name
        if not item.is_dir():
            continue
        # The shared plugin store is NOT a profile (it has no settings.json and
        # would otherwise register as a bogus "shared" profile).
        if name in {".claude-shared", "claude-shared", ".codex-shared", "codex-shared"}:
            continue
        # Match .claude, .claude-<name>, .codex, .codex-<name>
        # AND dotless equivalents: claude, claude-<name>, codex, codex-<name>
        for prefix, runtime in [
            (".claude", "claude"), ("claude", "claude"),
            (".codex", "codex"), ("codex", "codex"),
        ]:
            if name == prefix:
                profiles.append({"dir": item, "runtime": runtime, "profile": "default"})
                break
            if name.startswith(prefix + "-"):
                pname = name[len(prefix) + 1:]
                profiles.append({"dir": item, "runtime": runtime, "profile": pname})
                break
    return profiles


def find_launchers(config_home: Path) -> list[dict]:
    """Scan ~/.local/bin (or local-bin) for claude-*/codex-* launchers."""
    bin_dir = _find_path(config_home, ".local/bin", "local-bin")
    if not bin_dir.exists():
        bin_dir = config_home / ".local" / "bin"
        if not bin_dir.exists():
            bin_dir = config_home / "local-bin"
    launchers = []
    if bin_dir.exists():
        for f in sorted(bin_dir.iterdir()):
            if f.name.startswith("claude-") or f.name.startswith("codex-"):
                alive = f.exists() and (f.is_file() or f.is_symlink())
                target = None
                if f.is_symlink():
                    target = str(os.readlink(f))
                dead = f.is_symlink() and not f.exists()
                launchers.append({
                    "name": f.name,
                    "path": str(f),
                    "alive": alive and not dead,
                    "dead": dead,
                    "symlink_target": target,
                })
    return launchers


def scan_hooks_in_settings(settings_path: Path) -> list[str]:
    """Return hook names/paths found in a settings.json (NAMES ONLY — never execute)."""
    data = load_json(settings_path)
    if not isinstance(data, dict):
        return []
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return []
    found = []
    for event, entries in hooks.items():
        if isinstance(entries, list):
            for e in entries:
                if isinstance(e, dict):
                    cmd = e.get("command") or e.get("path") or e.get("name") or "(hook)"
                    found.append(f"{event}: {cmd}")
                elif isinstance(e, str):
                    found.append(f"{event}: {e}")
        elif isinstance(entries, str):
            found.append(f"{event}: {entries}")
    return found


def count_skill_md_copies(cache_root: Path) -> dict:
    """Count SKILL.md files under the cache root to estimate context tax."""
    if not cache_root.exists():
        return {"total": 0, "unique_plugins": 0, "duplication_factor": 1.0}
    copies = list(cache_root.rglob("SKILL.md"))
    total = len(copies)
    # unique plugins: top-level dirs under cache_root/<mkt>/<plugin>/
    plugins = set()
    for p in copies:
        parts = p.relative_to(cache_root).parts
        if len(parts) >= 2:
            plugins.add(parts[0] + "/" + parts[1])
    unique = len(plugins) if plugins else 1
    factor = total / unique if unique > 0 else 1.0
    return {"total": total, "unique_plugins": unique, "duplication_factor": round(factor, 1)}


# ---------------------------------------------------------------------------
# Status verb
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    config_home = Path(args.config_home).expanduser().resolve()
    stores = resolve_stores(config_home)

    print("=" * 60)
    print("global-meta status — config root inventory")
    print("=" * 60)
    print(f"config-home: {config_home}")
    print()

    # Profiles
    profiles = find_profiles(config_home)
    print(f"Profiles ({len(profiles)}):")
    for p in profiles:
        settings = p["dir"] / "settings.json"
        hooks = scan_hooks_in_settings(settings) if settings.exists() else []
        print(f"  [{p['runtime']}] {p['profile']}  ({p['dir']})")
        if hooks:
            for h in hooks:
                print(f"    hook: {h}")
        enabled = load_json(settings) or {}
        ep = enabled.get("enabledPlugins", {})
        if ep:
            print(f"    enabledPlugins (settings.json): {list(ep.keys())}")

    print()

    # Registry
    reg_path = stores["installed_plugins"]
    reg = load_json(reg_path) or {}
    plugins_reg = reg.get("plugins", {}) if isinstance(reg, dict) else {}
    print(f"Registry ({reg_path}):")
    if plugins_reg:
        for key, records in plugins_reg.items():
            scopes = [r.get("scope", "?") for r in records] if isinstance(records, list) else ["?"]
            versions = [r.get("version", "?") for r in records] if isinstance(records, list) else ["?"]
            print(f"  {key}: {len(records)} record(s), scopes={scopes}, versions={versions}")
    else:
        print("  (empty or missing)")
    print()

    # Enabled plugins
    enabled_path = stores["enabled_plugins"]
    enabled_data = load_json(enabled_path) or {}
    enabled_keys = list((enabled_data.get("enabledPlugins", {}) or {}).keys())
    print(f"Enabled plugins ({enabled_path}):")
    for k in enabled_keys:
        print(f"  {k}")
    if not enabled_keys:
        print("  (none)")
    print()

    # Launchers
    launchers = find_launchers(config_home)
    print(f"Launchers ({len(launchers)}):")
    for lnch in launchers:
        status = "DEAD" if lnch["dead"] else "ok"
        print(f"  {lnch['name']}  [{status}]  {lnch['path']}")
    if not launchers:
        print("  (none found)")
    print()

    # Context-tax estimate
    tax = count_skill_md_copies(stores["cache_root"])
    print("Context-tax estimate (SKILL.md copies in plugin cache):")
    print(f"  total SKILL.md copies: {tax['total']}")
    print(f"  unique plugins:        {tax['unique_plugins']}")
    print(f"  duplication factor:    {tax['duplication_factor']}x")
    print()

    print("NOTE: 'claude doctor' covers runtime health, binary version, and")
    print("      connectivity checks — see 'claude doctor' for those diagnostics.")

    return 0


# ---------------------------------------------------------------------------
# Audit verb — four-way consistency + findings
# ---------------------------------------------------------------------------

FINDING_CODES = {
    "stale-enablement":      "Enabled key with no registry entry",
    "wrong-scope":           "Spec-marketplace plugin whose only record is not local-scope@--home-dir",
    "dup-scope-records":     "Multiple scope records for one plugin",
    "cache-version-mismatch":"Registry version has no matching cache dir",
}


def _audit_findings(
    config_home: Path,
    home_dir: Path,
    spec_marketplace: str,
    stores: dict,
) -> list[dict]:
    """Run four-way consistency checks; return list of finding dicts."""
    findings = []

    reg_path = stores["installed_plugins"]
    reg = load_store_json(reg_path, "plugin registry", required=True)
    plugins_reg = reg.get("plugins", {})

    enabled_path = stores["enabled_plugins"]
    enabled_data = load_store_json(enabled_path, "enabled-plugins store", required=False) or {}
    enabled_keys = set((enabled_data.get("enabledPlugins", {}) or {}).keys())

    cache_root = stores["cache_root"]

    # F1: stale-enablement — enabled key with no registry entry
    for key in enabled_keys:
        if key not in plugins_reg:
            findings.append({
                "code": "stale-enablement",
                "plugin": key,
                "message": f"{key} is enabled but has no registry entry",
            })

    for key, records in plugins_reg.items():
        if not isinstance(records, list) or not records:
            continue
        # Only spec-check plugins from the spec marketplace
        mkt = key.split("@", 1)[1] if "@" in key else ""
        is_spec = (mkt == spec_marketplace)
        plugin_name = key.split("@", 1)[0]

        # F2: wrong-scope — spec plugin not installed at local-scope@home-dir
        if is_spec:
            local_at_home = [
                r for r in records
                if r.get("scope") == "local" and r.get("projectPath") == str(home_dir)
            ]
            if not local_at_home:
                findings.append({
                    "code": "wrong-scope",
                    "plugin": key,
                    "message": (
                        f"{key} has no local-scope record at projectPath={home_dir}; "
                        f"scopes present: {[r.get('scope') for r in records]}"
                    ),
                })

        # F3: dup-scope-records — multiple records for one plugin
        if len(records) > 1:
            findings.append({
                "code": "dup-scope-records",
                "plugin": key,
                "message": (
                    f"{key} has {len(records)} registry records "
                    f"(scopes: {[r.get('scope') for r in records]})"
                ),
            })

        # F4: cache-version-mismatch — registry version has no matching cache dir
        for record in records:
            version = record.get("version", "")
            if not version:
                continue
            # Cache dir: <cache_root>/<mkt>/<plugin_name>/<version>/
            cache_ver_dir = cache_root / mkt / plugin_name / version
            if not cache_ver_dir.exists():
                # Deduplicate: only report once per (plugin, version)
                if not any(
                    f["code"] == "cache-version-mismatch"
                    and f.get("plugin") == key
                    and f.get("version") == version
                    for f in findings
                ):
                    # What cache dirs DO exist?
                    plugin_cache = cache_root / mkt / plugin_name
                    existing = sorted([d.name for d in plugin_cache.iterdir()]) if plugin_cache.exists() else []
                    findings.append({
                        "code": "cache-version-mismatch",
                        "plugin": key,
                        "version": version,
                        "message": (
                            f"{key} registry version {version} has no cache dir "
                            f"{cache_ver_dir}; found: {existing}"
                        ),
                    })

    return findings


def _launcher_health_findings(config_home: Path) -> list[dict]:
    """Report dead launchers as findings."""
    findings = []
    for lnch in find_launchers(config_home):
        if lnch["dead"]:
            findings.append({
                "code": "dead-launcher",
                "launcher": lnch["name"],
                "message": f"Dead launcher symlink: {lnch['path']} -> {lnch['symlink_target']}",
            })
    return findings


def _enablement_divergence_notes(config_home: Path, stores: dict) -> list[str]:
    """Report-only: divergence between per-profile settings.json enabledPlugins vs shared file."""
    notes = []
    shared_path = stores["enabled_plugins"]
    shared_data = load_json(shared_path) or {}
    shared_ep = set((shared_data.get("enabledPlugins", {}) or {}).keys())

    profiles = find_profiles(config_home)
    for p in profiles:
        settings_path = p["dir"] / "settings.json"
        if not settings_path.exists():
            continue
        data = load_json(settings_path) or {}
        profile_ep = set((data.get("enabledPlugins", {}) or {}).keys())
        only_profile = profile_ep - shared_ep
        only_shared = shared_ep - profile_ep
        if only_profile or only_shared:
            notes.append(
                f"[{p['runtime']}/{p['profile']}] "
                f"profile-only={sorted(only_profile)}, "
                f"shared-only={sorted(only_shared)}"
            )
    return notes


# ---------------------------------------------------------------------------
# emit_fix — bash remediation script generator
# ---------------------------------------------------------------------------

def _emit_fix_script(
    findings: list[dict],
    config_home: Path,
    home_dir: Path,
    spec_marketplace: str,
    stores: dict,
    audit_script: Path,
    snapshot_root: Path,
) -> str:
    """Generate a bash-3.2-compatible remediation script from a list of findings.

    The emitted script:
    - Refuses to mutate without --apply (default = dry-run/plan print).
    - Takes a snapshot before the first mutation.
    - Is idempotent (each block guards on current state).
    - Uses python3 json round-trips for JSON edits (never sed on JSON).
    - Shell-escapes all interpolated finding values (shlex.quote at generation time).
    - Ends with a re-audit to report remaining findings.
    """
    lines: list[str] = []

    def w(s: str = "") -> None:
        lines.append(s)

    def sq(s: str) -> str:
        """shlex-quote at generation time for shell contexts (bash variables, arguments)."""
        return shlex.quote(s)

    def pr(s: str) -> str:
        """repr() for Python string literals inside heredoc blocks (not shell context)."""
        return repr(s)

    # Header
    w("#!/bin/bash")
    w("# global-meta remediation script — generated by config_root_audit.py --emit-fix")
    w("# audit --emit-fix (DASH-040)")
    w("#")
    w("# USAGE:")
    w("#   /bin/bash fix.sh           # dry-run: print the remediation plan, write nothing")
    w("#   /bin/bash fix.sh --apply   # apply all fixes (operator-run only)")
    w("#")
    w("# This script is bash-3.2 compatible (macOS /bin/bash).")
    w("# Shell context: values shell-escaped at generation time (shlex.quote).")
    w("# Python heredoc context: values are repr()-quoted Python string literals.")
    w("set -euo pipefail")
    w()

    # Baked-in constants (shell context — shlex.quote)
    w("# --- Baked-in generation-time constants ---")
    w(f"CONFIG_HOME={sq(str(config_home))}")
    w(f"HOME_DIR={sq(str(home_dir))}")
    w(f"SPEC_MKT={sq(spec_marketplace)}")
    w(f"AUDIT_SCRIPT={sq(str(audit_script))}")
    w(f"SNAPSHOT_ROOT={sq(str(snapshot_root))}")
    w(f"REGISTRY={sq(str(stores['installed_plugins']))}")
    w(f"ENABLED={sq(str(stores['enabled_plugins']))}")
    w()

    # --apply gate
    w("# --- Apply gate: default is dry-run ---")
    w('APPLY=0')
    w('for _arg in "$@"; do')
    w('  case "$_arg" in --apply) APPLY=1 ;; esac')
    w('done')
    w()

    if not findings:
        w('echo "global-meta fix: 0 findings -- nothing to do."')
        w('exit 0')
        return "\n".join(lines) + "\n"

    # Plan header
    w('echo "global-meta remediation plan:"')
    w('echo "  config-home:  $CONFIG_HOME"')
    w('echo "  spec-mkt:     $SPEC_MKT"')
    w(f'echo "  findings:     {len(findings)}"')
    w('echo ""')

    # Print plan (sq() for shell echo safety on untrusted plugin keys)
    for i, f in enumerate(findings, 1):
        code = f["code"]
        msg = f.get("message", "")
        # Use printf to avoid ambiguity with special chars in messages
        safe_msg = f"[{i}] {code}: {msg}"
        w(f"printf '%s\\n' {sq('  ' + safe_msg)}")
    w('echo ""')

    # Bail if dry-run
    w('if [ "$APPLY" -eq 0 ]; then')
    w('  echo "Dry-run mode: no changes written. Re-run with --apply to apply."')
    w('  exit 0')
    w('fi')
    w()

    # Snapshot before first mutation (shell context — shlex.quote for all args)
    w('# --- Step 0: snapshot before any mutation ---')
    w('echo "Taking pre-fix snapshot..."')
    w(
        f'python3 {sq(str(audit_script))} snapshot'
        f' --config-home {sq(str(config_home))}'
        f' --snapshot-root {sq(str(snapshot_root))}'
    )
    w('echo ""')
    w()

    # Build one fix block per finding
    for i, f in enumerate(findings, 1):
        code = f["code"]
        plugin_key = f.get("plugin", "")
        w(f'# --- Fix block [{i}]: {code} ({sq(plugin_key)}) ---')

        if code == "stale-enablement":
            # Remove the orphan key from enabled-plugins.local.json via python3 json round-trip
            w(f"printf '%s\\n' {sq('Fix [' + str(i) + '] stale-enablement: removing orphan enabled key ' + plugin_key)}")
            # Idempotency guard: only act if the key is still present
            # Python heredoc context: use repr() for Python string literals
            w("python3 - <<'PYEOF'")
            w("import json, sys, os")
            w(f"p = {pr(str(stores['enabled_plugins']))}")
            w(f"key = {pr(plugin_key)}")
            w("if not os.path.exists(p):")
            w("    print('  skip: ' + p + ' not found'); sys.exit(0)")
            w("with open(p, 'r', encoding='utf-8') as fh:")
            w("    data = json.load(fh)")
            w("ep = data.get('enabledPlugins', {})")
            w("if key not in ep:")
            w("    print('  idempotent: ' + repr(key) + ' already absent -- no change'); sys.exit(0)")
            w("del ep[key]")
            w("data['enabledPlugins'] = ep")
            w("with open(p, 'w', encoding='utf-8') as fh:")
            w("    json.dump(data, fh, indent=2)")
            w("    fh.write('\\n')")
            w("print('  removed ' + repr(key) + ' from enabledPlugins')")
            w("PYEOF")

        elif code == "dup-scope-records":
            # Drop the non-spec scope record (non-local@home), keep the local@home one
            w(f"printf '%s\\n' {sq('Fix [' + str(i) + '] dup-scope-records: keeping only local@home record for ' + plugin_key)}")
            w("python3 - <<'PYEOF'")
            w("import json, sys, os")
            w(f"p = {pr(str(stores['installed_plugins']))}")
            w(f"key = {pr(plugin_key)}")
            w(f"home_dir = {pr(str(home_dir))}")
            w("if not os.path.exists(p):")
            w("    print('  skip: ' + p + ' not found'); sys.exit(0)")
            w("with open(p, 'r', encoding='utf-8') as fh:")
            w("    data = json.load(fh)")
            w("plugins = data.get('plugins', {})")
            w("records = plugins.get(key, [])")
            w("if len(records) <= 1:")
            w("    print('  idempotent: ' + repr(key) + ' already has <=1 records -- no change'); sys.exit(0)")
            w("# Keep local@home record; drop others")
            w("kept = [r for r in records if r.get('scope') == 'local' and r.get('projectPath') == home_dir]")
            w("if not kept:")
            w("    # Fallback: keep first record if no local@home found")
            w("    kept = [records[0]]")
            w("plugins[key] = kept")
            w("data['plugins'] = plugins")
            w("with open(p, 'w', encoding='utf-8') as fh:")
            w("    json.dump(data, fh, indent=2)")
            w("    fh.write('\\n')")
            w("print('  ' + repr(key) + ': kept ' + str(len(kept)) + ' record(s), dropped ' + str(len(records)-len(kept)))")
            w("PYEOF")

        elif code == "wrong-scope":
            # Rewrite the record to scope=local + projectPath=home_dir via json round-trip
            w(f"printf '%s\\n' {sq('Fix [' + str(i) + '] wrong-scope: rewriting record for ' + plugin_key + ' to local@home')}")
            w("python3 - <<'PYEOF'")
            w("import json, sys, os")
            w(f"p = {pr(str(stores['installed_plugins']))}")
            w(f"key = {pr(plugin_key)}")
            w(f"home_dir = {pr(str(home_dir))}")
            w("if not os.path.exists(p):")
            w("    print('  skip: ' + p + ' not found'); sys.exit(0)")
            w("with open(p, 'r', encoding='utf-8') as fh:")
            w("    data = json.load(fh)")
            w("plugins = data.get('plugins', {})")
            w("records = plugins.get(key, [])")
            w("# Idempotency: already has a local@home record?")
            w("already = [r for r in records if r.get('scope') == 'local' and r.get('projectPath') == home_dir]")
            w("if already:")
            w("    print('  idempotent: ' + repr(key) + ' already has local@home record -- no change'); sys.exit(0)")
            w("# Rewrite all records to local + projectPath")
            w("for r in records:")
            w("    r['scope'] = 'local'")
            w("    r['projectPath'] = home_dir")
            w("data['plugins'] = plugins")
            w("with open(p, 'w', encoding='utf-8') as fh:")
            w("    json.dump(data, fh, indent=2)")
            w("    fh.write('\\n')")
            w("print('  ' + repr(key) + ': rewrote to scope=local, projectPath=' + repr(home_dir))")
            w("PYEOF")

        elif code == "cache-version-mismatch":
            version = f.get("version", "?")
            # Advisory only: print the exact install command; never script CLI installs
            w(f"printf '%s\\n' {sq('Fix [' + str(i) + '] cache-version-mismatch (ADVISORY): ' + plugin_key + ' v' + str(version))}")
            w(f"printf '%s\\n' {sq('  The cache dir for version ' + str(version) + ' is missing.')}")
            w(f"printf '%s\\n' {sq('  Run the following command to reinstall the correct version:')}")
            w(f"printf '%s\\n' {sq('    claude plugin install ' + plugin_key)}")
            w(f"printf '%s\\n' {sq('  (Never scripted -- operator must run this manually)')}")

        else:
            # Unknown / dead-launcher: advisory only
            msg_val = f.get("message", code)
            w(f"printf '%s\\n' {sq('Fix [' + str(i) + '] ' + code + ' (ADVISORY): ' + msg_val)}")
            w(f"printf '%s\\n' {sq('  Manual remediation required.')}")

        w()

    # Re-audit at the end (shell context — shlex.quote)
    w('# --- Final re-audit ---')
    w('echo "Re-running audit to count remaining findings..."')
    w('echo ""')
    w(
        f'python3 {sq(str(audit_script))} audit'
        f' --config-home {sq(str(config_home))}'
        f' --home-dir {sq(str(home_dir))}'
        f' --spec-marketplace {sq(spec_marketplace)}'
        f' --snapshot-root {sq(str(snapshot_root))}'
        " || true"
    )
    w('echo ""')
    w('echo "global-meta --emit-fix: done."')

    return "\n".join(lines) + "\n"


def cmd_audit(args: argparse.Namespace) -> int:
    config_home = Path(args.config_home).expanduser().resolve()
    home_dir = Path(args.home_dir).expanduser().resolve()
    spec_marketplace = args.spec_marketplace
    stores = resolve_stores(config_home)

    print("=" * 60)
    print("global-meta audit — config root four-way consistency")
    print("=" * 60)
    print(f"config-home:       {config_home}")
    print(f"home-dir:          {home_dir}")
    print(f"spec-marketplace:  {spec_marketplace}")
    print()

    # Run status inventory first (as a summary)
    reg_path = stores["installed_plugins"]
    reg = load_json(reg_path)
    plugins_reg = reg.get("plugins", {}) if isinstance(reg, dict) else {}

    enabled_path = stores["enabled_plugins"]
    enabled_data = load_json(enabled_path) or {}
    enabled_keys = set((enabled_data.get("enabledPlugins", {}) or {}).keys())

    print(f"Registry entries:  {len(plugins_reg)}")
    print(f"Enabled keys:      {len(enabled_keys)}")

    profiles = find_profiles(config_home)
    launchers = find_launchers(config_home)
    print(f"Profiles found:    {len(profiles)}")
    print(f"Launchers found:   {len(launchers)}")

    tax = count_skill_md_copies(stores["cache_root"])
    print(f"Context tax:       {tax['total']} SKILL.md copies, {tax['duplication_factor']}x duplication")
    print()

    # Four-way findings
    findings = _audit_findings(config_home, home_dir, spec_marketplace, stores)
    findings += _launcher_health_findings(config_home)

    # Divergence notes (report-only, not findings)
    divergence_notes = _enablement_divergence_notes(config_home, stores)

    if divergence_notes:
        print("Enablement divergence (report-only):")
        for note in divergence_notes:
            print(f"  {note}")
        print()

    # Delegation note for claude doctor territory
    print("NOTE: 'claude doctor' covers runtime health, binary version, and")
    print("      connectivity — those checks are delegated; not re-checked here.")
    print()

    if not findings:
        print("RESULT: CLEAN — 0 findings")
        # --emit-fix with 0 findings: write a no-op script
        emit_fix = getattr(args, "emit_fix", None)
        if emit_fix:
            audit_script = Path(__file__).resolve()
            snapshot_root = Path(args.snapshot_root).expanduser().resolve()
            script_content = _emit_fix_script(
                findings=[],
                config_home=config_home,
                home_dir=home_dir,
                spec_marketplace=spec_marketplace,
                stores=stores,
                audit_script=audit_script,
                snapshot_root=snapshot_root,
            )
            emit_path = Path(emit_fix)
            emit_path.write_text(script_content, encoding="utf-8")
            emit_path.chmod(0o755)
            print(f"Remediation script written (no-op): {emit_path}")
        return 0

    print(f"FINDINGS ({len(findings)}):")
    for i, f in enumerate(findings, 1):
        code = f.get("code", "unknown")
        msg = f.get("message", "")
        print(f"  [{i}] {code}: {msg}")

    print()
    print("Capture lines (ready-to-run):")
    for f in findings:
        code = f.get("code", "unknown")
        plugin = f.get("plugin", f.get("launcher", ""))
        title_body = f"{code}: {plugin}" if plugin else f"{code}: {f.get('message', '')[:60]}"
        # shlex.quote: registry/enablement keys are untrusted input — a crafted
        # plugin name must not become shell injection when the line is pasted.
        print(
            f"python3 skills/project-meta/scripts/board.py inbox-add "
            f"--title {shlex.quote(title_body)} --source config_root_audit"
        )

    # --emit-fix: write remediation script if requested
    emit_fix = getattr(args, "emit_fix", None)
    if emit_fix:
        audit_script = Path(__file__).resolve()
        snapshot_root = Path(args.snapshot_root).expanduser().resolve()
        script_content = _emit_fix_script(
            findings=findings,
            config_home=config_home,
            home_dir=home_dir,
            spec_marketplace=spec_marketplace,
            stores=stores,
            audit_script=audit_script,
            snapshot_root=snapshot_root,
        )
        emit_path = Path(emit_fix)
        emit_path.write_text(script_content, encoding="utf-8")
        emit_path.chmod(0o755)
        print()
        print(f"Remediation script written: {emit_path}")
        print(f"  dry-run:  /bin/bash {emit_path}")
        print(f"  apply:    /bin/bash {emit_path} --apply")

    return 1


# ---------------------------------------------------------------------------
# Snapshot verb
# ---------------------------------------------------------------------------

STORE_KEYS = ["installed_plugins", "enabled_plugins", "default_settings"]
STORE_FILENAMES = {
    "installed_plugins": "installed_plugins.json",
    "enabled_plugins": "enabled-plugins.local.json",
    "default_settings": "settings.json",
}


def cmd_snapshot(args: argparse.Namespace) -> int:
    config_home = Path(args.config_home).expanduser().resolve()
    snapshot_root = Path(args.snapshot_root).expanduser().resolve()
    stores = resolve_stores(config_home)

    ts = now_utc()
    snap_dir = snapshot_root / ts
    snap_dir.mkdir(parents=True, exist_ok=True)

    print(f"Snapshot -> {snap_dir}")
    copied = 0
    for key in STORE_KEYS:
        src = stores[key]
        dst = snap_dir / STORE_FILENAMES[key]
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  copied: {src.name} ({src.stat().st_size} bytes)")
            copied += 1
        else:
            print(f"  skip (not found): {src}")

    print(f"Done. {copied} file(s) in {snap_dir}")
    return 0


# ---------------------------------------------------------------------------
# Restore verb
# ---------------------------------------------------------------------------

def _find_newest_snapshot(snapshot_root: Path, from_ts: str | None) -> Path | None:
    if not snapshot_root.exists():
        return None
    candidates = sorted(
        [d for d in snapshot_root.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    if from_ts:
        for c in candidates:
            if c.name == from_ts:
                return c
        return None
    return candidates[0] if candidates else None


def cmd_restore(args: argparse.Namespace) -> int:
    config_home = Path(args.config_home).expanduser().resolve()
    snapshot_root = Path(args.snapshot_root).expanduser().resolve()
    dry_run = args.dry_run
    apply = getattr(args, "apply", False)
    from_ts = getattr(args, "from_ts", None)

    # Refuse immediately if neither --dry-run nor --apply is given (zero writes, clear message).
    if not dry_run and not apply:
        print(
            "restore: requires --dry-run (list only) or --apply (write files).\n"
            "Re-run with --dry-run to preview, or --apply to restore (operator-only this milestone).",
            file=sys.stderr,
        )
        return 2

    stores = resolve_stores(config_home)
    snap_dir = _find_newest_snapshot(snapshot_root, from_ts)

    if snap_dir is None:
        print(f"restore: no snapshot found in {snapshot_root}", file=sys.stderr)
        return 2

    print(f"Snapshot to restore: {snap_dir}")
    if dry_run:
        print("Mode: DRY-RUN (no writes)")

    plan = []
    for key in STORE_KEYS:
        src = snap_dir / STORE_FILENAMES[key]
        dst = stores[key]
        if src.exists():
            plan.append((src, dst))
            print(f"  would restore: {src.name} -> {dst}")
        else:
            print(f"  skip (not in snapshot): {STORE_FILENAMES[key]}")

    if dry_run:
        print("Dry-run complete. No files written.")
        return 0

    # Apply (--apply flag was set; operator-confirmed)
    for src, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  restored: {dst}")

    print(f"Done. {len(plan)} file(s) restored from {snap_dir}")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing & dispatch
# ---------------------------------------------------------------------------

def _add_common_args(p: argparse.ArgumentParser) -> None:
    """Add shared global arguments to a (sub)parser."""
    p.add_argument(
        "--config-home",
        default=os.environ.get("HOME", str(Path.home())),
        help="Config root to inspect (default: $HOME). Fixture roots use dotless subdirs.",
    )
    p.add_argument(
        "--home-dir",
        default=os.environ.get("HOME", str(Path.home())),
        help=(
            "Expected projectPath for the local-scope spec check (default: $HOME). "
            "Pass the real home even when --config-home points at a fixture."
        ),
    )
    p.add_argument(
        "--spec-marketplace",
        default="",
        help="Marketplace name whose plugins are subject to the four-way spec check.",
    )
    p.add_argument(
        "--snapshot-root",
        default=str(Path.home() / ".claude-shared" / "snapshots"),
        help="Root dir for snapshots (default: ~/.claude-shared/snapshots).",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="config_root_audit.py",
        description="global-meta: read-only config-root inventory, audit, and snapshot.",
    )

    sub = p.add_subparsers(dest="verb", required=True)

    # status
    sp_status = sub.add_parser("status", help="Read-only inventory of the config root.")
    _add_common_args(sp_status)

    # audit
    sp_audit = sub.add_parser("audit", help="Inventory + four-way consistency findings.")
    _add_common_args(sp_audit)
    sp_audit.add_argument(
        "--emit-fix",
        metavar="PATH",
        default=None,
        help=(
            "Write a bash remediation script to PATH. "
            "Default invocation (without --apply) prints the plan and exits 0 without writing. "
            "Run with --apply to apply fixes. "
            "With 0 findings writes a no-op script."
        ),
    )

    # snapshot
    sp_snap = sub.add_parser("snapshot", help="Copy the three stores to a timestamped snapshot dir.")
    _add_common_args(sp_snap)

    # restore
    restore_p = sub.add_parser("restore", help="Restore stores from a snapshot.")
    _add_common_args(restore_p)
    restore_p.add_argument("--dry-run", action="store_true", help="List files; do not write.")
    restore_p.add_argument("--apply", action="store_true", help="Actually write the files.")
    restore_p.add_argument("--from", dest="from_ts", default=None,
                           help="Restore from a specific snapshot timestamp (default: newest).")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.verb == "status":
            return cmd_status(args)
        elif args.verb == "audit":
            return cmd_audit(args)
        elif args.verb == "snapshot":
            return cmd_snapshot(args)
        elif args.verb == "restore":
            return cmd_restore(args)
        else:
            print(f"Unknown verb: {args.verb}", file=sys.stderr)
            return 2
    except KeyboardInterrupt:
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
