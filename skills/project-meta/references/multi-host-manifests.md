# Multi-Host Manifests

Use this reference when emitting per-host plugin / configuration files
from one canonical project-memory source.

## Why

A repo's project-memory contract should be tool-agnostic. The same rules
need to surface to whatever agent host the user invokes — Claude Code,
Cursor, Codex, Copilot CLI, Gemini CLI, OpenCode. Each host has its own
manifest discovery convention; without a generator, the repo accumulates
hand-edited copies that drift.

The principle: **one canonical file, many auto-generated mirrors**. The
canonical is `AGENTS.md` (default) or `CLAUDE.md` (when Claude Code is
the primary host per the tool-awareness rule in
`mirrors-and-updates.md`). Everything else is a mirror with a generation
banner at the top.

## Supported Hosts

`scripts/render_host_manifests.py` ships emitters for these hosts:

| Host | Manifest path | Notes |
|---|---|---|
| Claude Code | `.claude/instructions.md` | mirror; canonical `CLAUDE.md` already exists at root |
| GitHub Copilot CLI | `.github/copilot-instructions.md` | mirror |
| OpenAI Codex | `AGENTS.md` (root) | canonical when running under Codex |
| Cursor | `.cursor/rules/agents.md` | mirror |
| OpenCode | `.opencode/instructions.md` | mirror |
| Gemini CLI | `gemini-extension.json` + `.gemini/instructions.md` | JSON extension manifest pointing at markdown body |

If a host isn't listed, add an emitter to `scripts/render_host_manifests.py`
following the pattern of `emit_markdown_mirror` (for plain markdown
mirrors) or `emit_gemini` (for hosts that want a JSON extension manifest
plus a markdown body).

## Generation Contract

Every generated mirror carries a banner naming:

- the canonical source file
- the generation timestamp (UTC, ISO-8601)
- the generator script path

This makes it trivial for an agent or human reading the mirror to know
it's auto-generated and where the source lives. Agents that want to
*edit* a rule must edit the canonical, then re-run the generator.

The script never overwrites the canonical. If a host's manifest path
collides with the canonical (e.g. running under Codex with the
canonical already named `AGENTS.md`), the emitter is a no-op for that
host.

## Invocation

`/project-meta init --hosts <list>` runs the generator at install time.
`/project-meta deliver` runs it again to refresh mirrors after canonical
changes. Manual invocation:

```bash
python3 ~/.claude/skills/project-meta/scripts/render_host_manifests.py \
    --target-root /path/to/repo \
    --hosts claude,copilot,cursor
```

Defaults to all supported hosts when `--hosts` is omitted. Use
`--dry-run` to preview without writing.

## When to Re-Run

The generator is idempotent — re-running with the same canonical
produces byte-identical mirrors (modulo the timestamp). Re-run when:

- The canonical file changes structurally (new sections, renamed
  topical references, changed bootstrap order).
- A new host is added to the team's stack.
- The team retires a host (delete the mirror manually; the generator
  doesn't garbage-collect mirrors for hosts no longer in the list).

Don't re-run on every commit; the timestamp churn pollutes diffs. A
weekly cadence or pre-release run is usually enough.

## Conflict Handling

When a manual edit lands in a generated mirror, the next regeneration
will silently overwrite it. Two safeguards:

1. The banner makes the auto-generated nature visible to humans
   reading the file.
2. `/project-meta validate` can detect mirror-vs-canonical drift and
   warn before the next regeneration.

The cleaner habit: edit only the canonical. Treat any urge to "just
quickly fix the mirror" as a sign that the canonical needs the same
fix, generalised.

## Anti-patterns

- **Mirror as alternate manual.** Adding rules to a mirror that don't
  exist in the canonical creates a parallel source of truth. AP-MEM-2.
  Generator-emitted mirrors short-circuit this by overwriting; the
  drift only comes back if a hand edit lands in the mirror.
- **Generating mirrors for hosts the team doesn't use.** Each
  unmaintained mirror is a future drift source. Trim `--hosts` to the
  team's actual stack.
- **Per-host content forks.** "But Cursor needs slightly different
  rules" → either generalise the rule into the canonical, or accept
  that the divergent rule belongs in a host-specific reference (not in
  the auto-generated mirror).
- **Banners stripped.** The generation banner is the audit trail.
  Removing it makes drift undetectable. Treat banner removal as a
  policy violation.
