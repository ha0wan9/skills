#!/usr/bin/env bash
# ship_plugin.sh — deterministic mechanics for the "validated edit → ship" workflow.
#
# The agent orchestrates the chain; this script owns only the deterministic legs so
# they are reliable and cheap. The two judgment gates (repo validator must pass AND a
# fresh-context review agent must approve) live in the agent's flow, not here:
#
#   1. scripts/ship_plugin.sh validate          # validator gate — exits non-zero on failure
#   2. scripts/ship_plugin.sh open "<title>"    # commit (if needed) + push + open PR
#   3. <agent dispatches a FRESH-context review agent over the PR diff>
#   4. scripts/ship_plugin.sh land              # merge-if-clean + reload changed plugins
#
# `land` re-checks GitHub mergeability but does NOT itself run the review — the agent
# must only call `land` after the fresh review came back clean ("review, merge if clean").
#
# Version policy: EVERY shipped change must bump a version before the PR merges.
# The agent picks the semver level by impact (patch = fix/docs/internal; minor =
# new backward-compatible capability; major = breaking change). `check-version`
# enforces it in both `validate` and `land`; `land` will not merge without it.
#
# Subcommands:
#   validate            run repo validators + the version-bump gate; exit 0 iff all pass
#   check-version       gate: every changed plugin's marketplace.json version must be
#                       bumped vs base (root-only changes must bump marketplace version)
#   bump <tgt> <level>  bump a version in marketplace.json. tgt = a plugin name or
#                       "marketplace"; level = major|minor|patch. Edits the manifest.
#   changed-plugins     print the plugin names touched vs the base branch (one per line)
#   open "<title>"      stage all, commit if there are changes, push branch, open/echo PR
#   land [--no-reload]  merge the current branch's PR if clean, then reload changed plugins
#   reload [names...]   refresh local install: marketplace update + scope-aware reinstall
#                       (each plugin re-lands at its recorded scope/projectPath)
#
# Env overrides: BASE_BRANCH (default main), MARKETPLACE (default ha0wan9-skills),
#                MERGE_FLAGS (default "--squash --delete-branch").
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_BRANCH="${BASE_BRANCH:-main}"
MARKETPLACE="${MARKETPLACE:-ha0wan9-skills}"
MERGE_FLAGS="${MERGE_FLAGS:---squash --delete-branch}"

die()  { echo "ship: $*" >&2; exit 1; }
info() { echo "ship: $*" >&2; }

# Files changed by this branch's work: committed-vs-base ∪ staged ∪ unstaged.
_changed_files() {
  { git diff --name-only "${BASE_BRANCH}...HEAD" 2>/dev/null || true
    git diff --name-only 2>/dev/null || true
    git diff --name-only --staged 2>/dev/null || true
  } | sort -u | sed '/^$/d'
}

# Plugin (== skill dir) basenames touched by the change set.
_changed_plugins() {
  _changed_files | sed -n 's#^skills/\([^/]*\)/.*#\1#p' | sort -u
}

# --- marketplace.json sanity: parses, every skills[] path is a dir with SKILL.md,
#     plugin names are unique, and each plugin description matches its SKILL.md. ---
_validate_marketplace() {
  python3 - "$REPO_ROOT" <<'PY'
import json, os, re, sys
root = sys.argv[1]
mani = os.path.join(root, ".claude-plugin", "marketplace.json")
with open(mani) as f:
    data = json.load(f)
errs, names = [], set()
for p in data.get("plugins", []):
    n = p.get("name", "<unnamed>")
    if n in names:
        errs.append(f"duplicate plugin name: {n}")
    names.add(n)
    for sk in p.get("skills", []):
        d = os.path.normpath(os.path.join(root, sk))
        if not os.path.isdir(d):
            errs.append(f"{n}: skills path not a dir: {sk}")
            continue
        sm = os.path.join(d, "SKILL.md")
        if not os.path.isfile(sm):
            errs.append(f"{n}: no SKILL.md in {sk}")
            continue
        # If SKILL.md frontmatter declares a version, it must match the manifest version.
        head = open(sm, encoding="utf-8").read()[:4000]
        mv = re.search(r"version:\s*(\d+\.\d+\.\d+)", head)
        if mv and mv.group(1) != p.get("version"):
            errs.append(f"{n}: SKILL.md version {mv.group(1)} != manifest version {p.get('version')}")
if errs:
    print("marketplace.json invalid:\n  - " + "\n  - ".join(errs), file=sys.stderr)
    sys.exit(1)
print(f"marketplace.json ok ({len(names)} plugins)", file=sys.stderr)
PY
}

cmd_validate() {
  local plugins; plugins="$(_changed_plugins || true)"
  info "changed plugins: ${plugins:-<none>}"

  # Always: manifest must be coherent (cheap, catches the common drift).
  _validate_marketplace

  # Version policy: a shippable change must bump a version.
  cmd_check_version

  # project-meta has a dedicated dev validator.
  if grep -qx "project-meta" <<<"$plugins"; then
    info "running validate_project_meta.py"
    python3 scripts/validate_project_meta.py
  fi

  # dl-research ships a ledger validator; run it only when a runs.jsonl fixture changed.
  if grep -qx "dl-research" <<<"$plugins"; then
    local ledgers
    ledgers="$(_changed_files | grep -E 'skills/dl-research/.*runs\.jsonl$' || true)"
    if [[ -n "$ledgers" ]]; then
      while IFS= read -r lf; do
        [[ -n "$lf" ]] || continue
        info "validating ledger fixture: $lf"
        python3 skills/dl-research/scripts/validate_ledger.py "$lf"
      done <<<"$ledgers"
    fi
  fi

  info "validate: PASS"
}

cmd_changed_plugins() { _changed_plugins; }

# bump <target> <level> — edit a version in .claude-plugin/marketplace.json.
# target = a plugin name (its plugins[].version) or "marketplace" (metadata.version).
# level  = major | minor | patch. Keeps the bumped plugin's SKILL.md frontmatter
# version in sync when that file declares one.
cmd_bump() {
  local target="${1:-}" level="${2:-}"
  [[ -n "$target" && -n "$level" ]] || die "usage: ship_plugin.sh bump <plugin|marketplace> <major|minor|patch>"
  case "$level" in major|minor|patch) : ;; *) die "level must be major|minor|patch (got: $level)" ;; esac
  python3 - "$REPO_ROOT" "$target" "$level" <<'PY'
import json, os, re, sys
root, target, level = sys.argv[1], sys.argv[2], sys.argv[3]
mani = os.path.join(root, ".claude-plugin", "marketplace.json")
with open(mani) as f:
    data = json.load(f)

def bump(v):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", v.strip())
    if not m:
        sys.exit(f"bump: version '{v}' is not X.Y.Z")
    a, b, c = (int(x) for x in m.groups())
    if level == "major": a, b, c = a + 1, 0, 0
    elif level == "minor": b, c = b + 1, 0
    else: c += 1
    return f"{a}.{b}.{c}"

if target == "marketplace":
    old = data["metadata"]["version"]; new = bump(old)
    data["metadata"]["version"] = new
    skill_md = None
else:
    plug = next((p for p in data.get("plugins", []) if p.get("name") == target), None)
    if plug is None:
        sys.exit(f"bump: no plugin named '{target}' in marketplace.json")
    old = plug["version"]; new = bump(old)
    plug["version"] = new
    skill_md = os.path.join(root, "skills", target, "SKILL.md")

with open(mani, "w") as f:
    json.dump(data, f, indent=2); f.write("\n")

synced = ""
if skill_md and os.path.isfile(skill_md):
    txt = open(skill_md).read()
    new_txt, n = re.subn(r"(version:\s*)\d+\.\d+\.\d+", rf"\g<1>{new}", txt, count=1)
    if n:
        open(skill_md, "w").write(new_txt)
        synced = f"  (synced {os.path.relpath(skill_md, root)})"
print(f"bumped {target}: {old} -> {new} [{level}]{synced}", file=sys.stderr)
PY
}

# check-version — the gate. Every changed plugin must have a strictly higher
# marketplace.json version than on the base branch; a change that touches no
# plugin (root/infra only) must bump the marketplace metadata.version instead.
# A brand-new plugin (absent on the base branch) passes on first appearance with
# any valid semver — there is no base version to exceed.
# A REMOVED plugin (manifest entry and skills/<name>/ dir both gone) is a retirement,
# not a missing bump; the covering bump is the marketplace metadata.version.
cmd_check_version() {
  local plugins; plugins="$(_changed_plugins || true)"
  python3 - "$REPO_ROOT" "$BASE_BRANCH" "$plugins" <<'PY'
import json, os, re, subprocess, sys
root, base_ref, plugins_raw = sys.argv[1], sys.argv[2], sys.argv[3]
changed = [p for p in plugins_raw.split() if p]
raw = subprocess.run(["git", "-C", root, "show", f"{base_ref}:.claude-plugin/marketplace.json"],
                     capture_output=True, text=True)
if raw.returncode != 0:
    print("check-version: no base manifest (new repo?); skipping", file=sys.stderr)
    sys.exit(0)
base = json.loads(raw.stdout)
cur = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))

def ver(d, name):
    if name == "marketplace":
        return d.get("metadata", {}).get("version")
    return next((p.get("version") for p in d.get("plugins", []) if p.get("name") == name), None)

def parse(v):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", (v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None

def higher(name):
    b, c = parse(ver(base, name)), parse(ver(cur, name))
    if c is None:
        return False            # current version missing/malformed → not a valid bump
    if b is None:
        return True             # new plugin: first appearance with a valid version IS the bump
    return c > b

fails, removed = [], []
if changed:
    for name in changed:
        # Manifest entry AND skill dir both gone → the plugin was retired, not
        # left unbumped. Dir-still-present falls through to the normal failure
        # (an unregistered skill dir is drift, not a removal).
        if ver(cur, name) is None and not os.path.isdir(os.path.join(root, "skills", name)):
            removed.append(name)
            continue
        if not higher(name):
            fails.append(f"plugin '{name}' version not bumped ({ver(base,name)} -> {ver(cur,name)}); "
                         f"run: ship_plugin.sh bump {name} <major|minor|patch>")
    if removed and not higher("marketplace"):
        fails.append(f"plugin removal ({', '.join(removed)}) requires a marketplace version bump "
                     f"({ver(base,'marketplace')} -> {ver(cur,'marketplace')}); "
                     f"run: ship_plugin.sh bump marketplace <major|minor|patch>")
else:
    if not higher("marketplace"):
        fails.append(f"no plugin changed and marketplace version not bumped "
                     f"({ver(base,'marketplace')} -> {ver(cur,'marketplace')}); "
                     f"run: ship_plugin.sh bump marketplace <major|minor|patch>")

if fails:
    print("check-version: FAIL\n  - " + "\n  - ".join(fails), file=sys.stderr)
    sys.exit(1)
live = [n for n in changed if n not in removed]
tgt = ", ".join(live) if live else "marketplace"
note = f"; removed: {', '.join(removed)}" if removed else ""
print(f"check-version: ok ({tgt} bumped{note})", file=sys.stderr)
PY
}

cmd_open() {
  local title="${1:-}"
  [[ -n "$title" ]] || die "open requires a PR title: ship_plugin.sh open \"<title>\""
  local branch; branch="$(git rev-parse --abbrev-ref HEAD)"
  [[ "$branch" != "$BASE_BRANCH" ]] || die "refusing to ship from $BASE_BRANCH; switch to a feature branch"

  if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    git commit -m "$title" \
      -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  else
    info "no uncommitted changes; using existing commits"
  fi

  git push -u origin "$branch"

  local existing; existing="$(gh pr view "$branch" --json url -q .url 2>/dev/null || true)"
  if [[ -n "$existing" ]]; then
    info "PR already open: $existing"
    echo "$existing"
  else
    gh pr create --base "$BASE_BRANCH" --head "$branch" --title "$title" \
      --body "$(printf '%s\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)' "$title")" \
      --fill
  fi
}

cmd_land() {
  local do_reload=1
  [[ "${1:-}" == "--no-reload" ]] && { do_reload=0; shift || true; }

  local branch; branch="$(git rev-parse --abbrev-ref HEAD)"
  local plugins; plugins="$(_changed_plugins || true)"

  # Hard gate: an open + red audit transaction means a final audit did not
  # converge — never merge past it (DASH-032; recipes/audit.md Convergence
  # loop). Checked before the version gate so the more fundamental signal
  # surfaces first. The ledger is branch-scoped and self-skips when absent.
  local audit_gate="$REPO_ROOT/skills/project-meta/scripts/audit_ledger.py"
  if [[ -f "$audit_gate" && -f "$REPO_ROOT/.harness/audit-ledger.jsonl" ]]; then
    python3 "$audit_gate" --target-root "$REPO_ROOT" gate \
      || die "audit convergence gate failed — see the gate message above for the path out (re-audit to a clean round, or at the cap an operator override: audit_ledger.py record --final --accept-residuals \"reason\")"
  fi

  # Hard gate: never merge a change that did not bump a version.
  cmd_check_version

  # Resolve the PR number up front: after a --delete-branch merge the branch ref is gone,
  # so a later branch-name lookup would fail; the number stays stable.
  local prnum
  prnum="$(gh pr view "$branch" --json number -q .number 2>/dev/null || true)"
  [[ -n "$prnum" ]] || die "no open PR found for branch $branch"

  local state
  state="$(gh pr view "$prnum" --json mergeStateStatus -q .mergeStateStatus 2>/dev/null || true)"
  info "PR #$prnum mergeStateStatus: ${state:-<unknown>}"
  case "$state" in
    CLEAN|UNSTABLE|HAS_HOOKS|"") : ;;  # UNSTABLE = mergeable but checks pending/failing
    BEHIND)  die "PR is BEHIND base; update the branch before landing" ;;
    DIRTY)   die "PR has conflicts (DIRTY); resolve before landing" ;;
    BLOCKED) die "PR is BLOCKED by branch protection; cannot auto-merge" ;;
    *)       info "proceeding despite mergeStateStatus=$state" ;;
  esac

  # gh's post-merge local cleanup (checkout base + delete local branch) fails inside a git
  # worktree where base is checked out elsewhere — a cosmetic failure that must not abort
  # the flow. Confirm the merge via the PR's actual state rather than gh's exit code.
  # shellcheck disable=SC2086
  gh pr merge "$prnum" $MERGE_FLAGS \
    || info "gh pr merge exited non-zero (likely local-branch cleanup in a worktree); verifying state"
  local merged
  merged="$(gh pr view "$prnum" --json state -q .state 2>/dev/null || true)"
  [[ "$merged" == "MERGED" ]] || die "PR #$prnum did not reach MERGED (state=${merged:-<unknown>}); not reloading"
  info "merged PR #$prnum into $BASE_BRANCH"

  if [[ "$do_reload" == "1" ]]; then
    # $plugins is newline-separated; split explicitly instead of relying on IFS word-split.
    # No mapfile: macOS /bin/bash is 3.2 (mapfile is bash 4+), and `env bash` can
    # resolve there — land used to die right after the merge on exactly that.
    local -a plugin_arr=()
    while IFS= read -r _p; do plugin_arr+=("$_p"); done <<< "$plugins"
    cmd_reload "${plugin_arr[@]}"
  fi
}

# --- scope-aware reload helpers ----------------------------------------------
# `claude plugin uninstall`/`install` default to --scope user, but installs on this
# machine may be recorded at LOCAL scope (scope:"local" + projectPath in
# installed_plugins.json). A scope-blind uninstall misses those, and the follow-up
# install then lands a user-scope DUPLICATE next to the stale local record —
# registry drift that needed manual re-convergence after every land. Reload
# therefore refreshes each plugin AT its recorded scope, running local/project-scope
# work from the recorded projectPath (the CLI keys those scopes to its cwd).

# _plugin_records <name> — registry lookup for <name>@$MARKETPLACE. Prints one
# "record<TAB>scope<TAB>projectPath" line per install record, local-scope rows
# first (the first row is the one reload refreshes; extra rows are drift). A plugin
# with NO record prints a single "sibling<TAB>scope<TAB>projectPath" row carrying
# the dominant scope of the other plugins from this marketplace — a brand-new
# plugin should land where its siblings live, not at the CLI's user-scope default.
# Prints nothing when the registry is missing or holds no marketplace records.
# The registry path is resolved through symlinks: shared-store setups point
# ~/.claude/plugins at a common store (e.g. ~/.claude-shared/plugins).
_plugin_records() {
  python3 - "$1" "$MARKETPLACE" <<'PY'
import json, os, sys
from collections import Counter
name, mkt = sys.argv[1], sys.argv[2]
cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
reg = os.path.realpath(os.path.join(cfg, "plugins", "installed_plugins.json"))
try:
    with open(reg) as f:
        plugins = json.load(f).get("plugins", {})
except (OSError, ValueError):
    sys.exit(0)
recs = plugins.get("%s@%s" % (name, mkt)) or []
if recs:
    for r in sorted(recs, key=lambda r: r.get("scope") != "local"):
        print("record\t%s\t%s" % (r.get("scope", "user"), r.get("projectPath", "")))
else:
    sibs = Counter(
        (r.get("scope", "user"), r.get("projectPath", ""))
        for key, rs in plugins.items() if key.endswith("@" + mkt)
        for r in (rs or []))
    if sibs:
        scope, proj = sibs.most_common(1)[0][0]
        print("sibling\t%s\t%s" % (scope, proj))
PY
}

# Local-scope plugin ops write <projectPath>/.claude/settings.local.json. In a
# shared-enablement setup that file is a SYMLINK (e.g. -> ~/.claude-shared/
# enabled-plugins.local.json) and the CLI refuses symlink writes. Work around it:
# park the link, give the CLI a real copy, then push the (possibly CLI-edited)
# copy back into the link target and restore the link. The EXIT trap guarantees
# the link comes back even if a CLI call dies mid-window.
_PARK_LINK=""
_PARK_TARGET=""
_park_settings() {  # $1 = projectPath; no-op unless settings.local.json is a symlink
  local s="$1/.claude/settings.local.json"
  [[ -L "$s" ]] || return 0
  _PARK_TARGET="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$s")"
  mv "$s" "$s.symlink-parked"
  _PARK_LINK="$s"
  trap _unpark_settings EXIT
  if ! cp "$_PARK_TARGET" "$s"; then
    _PARK_LINK=""
    mv "$s.symlink-parked" "$s"
    die "settings.local.json symlink target unreadable ($_PARK_TARGET); aborted before any uninstall"
  fi
  info "parked settings.local.json symlink under $1 (CLI refuses symlink writes)"
}
_unpark_settings() {
  [[ -n "$_PARK_LINK" ]] || return 0
  local s="$_PARK_LINK"
  _PARK_LINK=""
  # Keep enablement edits the CLI made inside the window: sync the working copy
  # back into the shared target before swapping the symlink back in.
  if [[ -f "$s" ]]; then
    cp "$s" "$_PARK_TARGET" \
      || info "WARNING: could not sync settings edits back to $_PARK_TARGET; CLI edits inside the park window may be lost"
  fi
  rm -f "$s"
  mv "$s.symlink-parked" "$s"
  info "restored settings.local.json symlink ($s)"
}

cmd_reload() {
  info "updating marketplace: $MARKETPLACE"
  # A failed marketplace update leaves a STALE cache: the install below would silently
  # re-materialize the old version while still printing "reload done". Die instead —
  # a reload from a stale cache is worse than no reload (memory: ship-reload-stale-cache-trap).
  claude plugin marketplace update "$MARKETPLACE" \
    || die "marketplace update failed — cache is stale; aborting reload (re-run after fixing connectivity/auth)"
  local n recs primary kind scope proj dup mode failed=0
  local scoped_jobs=""   # one line per scoped job: projectPath \t name \t scope \t mode \t dup
  for n in "$@"; do
    [[ -n "$n" ]] || continue
    recs="$(_plugin_records "$n")"
    primary="$(printf '%s\n' "$recs" | head -n 1)"
    kind="${primary%%$'\t'*}"
    primary="${primary#*$'\t'}"
    scope="${primary%%$'\t'*}"
    proj="${primary#*$'\t'}"
    # Older scope-blind reloads left user-scope duplicates next to local records;
    # remember to drop the dup once the real record is refreshed.
    dup=0
    if [[ "$kind" == "record" && "$scope" != "user" ]] \
        && printf '%s\n' "$recs" | grep -q $'^record\tuser\t'; then
      dup=1
    fi

    # A name no longer in the manifest is a RETIRED plugin: the marketplace no longer
    # offers it, so a reinstall would fail. Remove the local install instead
    # (best-effort — it may never have been installed on this machine).
    if ! python3 -c 'import json,sys; d=json.load(open(".claude-plugin/marketplace.json")); sys.exit(0 if any(p.get("name")==sys.argv[1] for p in d.get("plugins",[])) else 1)' "$n"; then
      if [[ "$kind" != "record" ]]; then
        info "plugin $n is retired and not installed locally — nothing to remove"
      elif [[ -n "$proj" ]]; then
        scoped_jobs+="${proj}"$'\t'"${n}"$'\t'"${scope}"$'\t'retired$'\t'"${dup}"$'\n'
      else
        info "plugin $n is gone from the manifest (retired) — uninstalling locally (--scope $scope)"
        claude plugin uninstall "$n@$MARKETPLACE" --scope "$scope" \
          || info "uninstall $n@$MARKETPLACE non-zero (may not be installed locally)"
      fi
      continue
    fi

    # `claude plugin update` is a no-op when the manifest version is unchanged, so a
    # same-version edit never re-materializes the cache (it reports "already at the latest
    # version" and the stale copy under .../plugins/cache/<mkt>/<plugin>/<version>/ stands).
    # Reinstall instead: uninstall + install re-clones from the refreshed marketplace cache
    # and refreshes the recorded gitCommitSha. Names in installed_plugins.json are
    # marketplace-qualified, so address as <name>@<mkt> (the bare name fails "not found").
    mode="live"
    if [[ "$kind" == "sibling" ]]; then
      mode="fresh"   # not installed yet: adopt the siblings' scope, skip the uninstall
      info "plugin $n not installed — adopting marketplace siblings' scope (${scope}${proj:+ @ $proj})"
    elif [[ "$kind" != "record" ]]; then
      # No record and no siblings either: nothing to imitate — plain install at the
      # CLI default (user scope).
      info "installing plugin: $n@$MARKETPLACE (no local records; CLI default scope)"
      if ! claude plugin install "$n@$MARKETPLACE"; then
        info "ERROR: install $n@$MARKETPLACE failed"
        failed=1
      fi
      continue
    fi
    if [[ -z "$proj" && "$scope" != "user" ]]; then
      info "ERROR: $n has a $scope-scope record with no projectPath (malformed registry); skipping — fix installed_plugins.json manually"
      failed=1
      continue
    fi

    if [[ -n "$proj" ]]; then
      scoped_jobs+="${proj}"$'\t'"${n}"$'\t'"${scope}"$'\t'"${mode}"$'\t'"${dup}"$'\n'
      continue
    fi

    # User-scope record (no projectPath): reinstall in place, scope made explicit.
    info "reinstalling plugin: $n@$MARKETPLACE (--scope $scope)"
    if [[ "$mode" == "live" ]]; then
      # Uninstall is best-effort: a not-yet-installed plugin makes it exit non-zero, and
      # the install below is what actually matters, so swallow it and proceed.
      claude plugin uninstall "$n@$MARKETPLACE" --scope "$scope" \
        || info "uninstall $n@$MARKETPLACE non-zero (plugin may be absent; proceeding to install)"
    fi
    # Install is load-bearing: if it fails after a successful uninstall the plugin is now
    # GONE locally — surface loudly and mark the reload failed rather than swallowing it.
    if ! claude plugin install "$n@$MARKETPLACE" --scope "$scope"; then
      info "ERROR: install $n@$MARKETPLACE failed — plugin may now be UNINSTALLED locally; reinstall it manually"
      failed=1
    fi
  done

  # Scoped (local/project) jobs, grouped per projectPath so the settings.local.json
  # symlink dance happens once per project, not once per plugin.
  if [[ -n "$scoped_jobs" ]]; then
    local p jproj jname jscope jmode jdup
    while IFS= read -r p; do
      [[ -n "$p" ]] || continue
      if [[ ! -d "$p" ]]; then
        info "ERROR: recorded projectPath missing: $p — skipping its plugins"
        failed=1
        continue
      fi
      _park_settings "$p"
      while IFS=$'\t' read -r jproj jname jscope jmode jdup; do
        [[ "$jproj" == "$p" ]] || continue
        if [[ "$jmode" == "retired" ]]; then
          info "plugin $jname is gone from the manifest (retired) — uninstalling (--scope $jscope @ $p)"
          (cd "$p" && claude plugin uninstall "$jname@$MARKETPLACE" --scope "$jscope") \
            || info "uninstall $jname@$MARKETPLACE non-zero (may not be installed locally)"
          continue
        fi
        info "reinstalling plugin: $jname@$MARKETPLACE (--scope $jscope @ $p)"
        if [[ "$jmode" == "live" ]]; then
          # Uninstall is best-effort: a not-yet-installed plugin makes it exit non-zero,
          # and the install below is what actually matters, so swallow it and proceed.
          (cd "$p" && claude plugin uninstall "$jname@$MARKETPLACE" --scope "$jscope") \
            || info "uninstall $jname@$MARKETPLACE non-zero (plugin may be absent; proceeding to install)"
        fi
        # Install is load-bearing: if it fails after a successful uninstall the plugin is
        # now GONE locally — surface loudly and mark the reload failed, not swallowed.
        if ! (cd "$p" && claude plugin install "$jname@$MARKETPLACE" --scope "$jscope"); then
          info "ERROR: install $jname@$MARKETPLACE failed — plugin may now be UNINSTALLED locally; reinstall it manually"
          failed=1
        elif [[ "$jdup" == "1" ]]; then
          # Drift left by older scope-blind reloads: a user-scope duplicate shadowing
          # the real record. Drop it now that the real record is refreshed.
          info "dropping stale user-scope duplicate of $jname"
          claude plugin uninstall "$jname@$MARKETPLACE" --scope user \
            || info "could not drop user-scope dup of $jname (clean up manually)"
        fi
      done <<< "$scoped_jobs"
      _unpark_settings
    done <<< "$(printf '%s' "$scoped_jobs" | cut -f1 | sort -u)"
  fi

  [[ "$failed" == "0" ]] \
    || die "one or more plugins failed to reinstall (see above); fix them before restarting Claude Code"
  info "reload done — restart Claude Code to apply updated plugins"
}

main() {
  local sub="${1:-}"; shift || true
  case "$sub" in
    validate)         cmd_validate "$@" ;;
    check-version)    cmd_check_version "$@" ;;
    bump)             cmd_bump "$@" ;;
    changed-plugins)  cmd_changed_plugins "$@" ;;
    open)             cmd_open "$@" ;;
    land)             cmd_land "$@" ;;
    reload)           cmd_reload "$@" ;;
    ""|-h|--help)
      sed -n '2,33p' "${BASH_SOURCE[0]}" ;;
    *) die "unknown subcommand: $sub (try --help)" ;;
  esac
}
main "$@"
