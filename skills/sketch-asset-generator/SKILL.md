---
name: sketch-asset-generator
description: Generate modular, reusable, original visual asset packs from user-provided design sketches, wireframes, whiteboard photos, Figma or Sketch screenshots, UI mocks, moodboards, or existing UI source (CSS, SVG, components). Prefer extracting assets from user-owned resources (tokens, vectors, component code); use GPT Image only when an asset cannot be extracted. Use when turning sketches or source UI into design-system-ready assets, asset-pack.yaml briefs, design tokens, SVG and component primitives, manifests, contact sheets, or validation reports, using public design systems only as structural references and never copying third-party brand visuals. Works whether the agent is Claude or Codex.
metadata: {version: 1.2.2, compat: [claude-code, codex], published: [claude-marketplace]}
---

# Sketch Asset Generator

## Overview

Use this skill to convert user-owned sketches and source UI into a reviewable asset pack. The user's sketch or source resource is the visual source of truth. Public design systems may inform taxonomy, governance, accessibility, and validation only.

Production is **extraction-first**: when an asset already exists in a user-owned resource (CSS tokens, SVGs, existing components, source files), extract or vectorize it directly with code. Use GPT Image generation only as a fallback, for original assets that cannot be extracted from any user resource. An agent that can author code and SVG (e.g. Claude) runs the default extraction path with no external image model.

## Trigger Decision

- User provides a sketch, wireframe, whiteboard photo, Figma/Sketch screenshot, or low-fidelity UI mock and wants structured assets from it.
- User provides source UI (CSS, SVG, component code) and wants design-system-ready tokens, primitives, or a packaged asset pack.
- User asks to produce or update an `asset-pack.yaml` brief, manifest, contact sheet, or validation report for a visual project.
- User wants to turn a moodboard or component layout sketch into reusable SVG or component assets.
- User asks to validate an existing asset pack against originality or completeness rules.

## Bootstrap Order

Read before acting:

1. This file (`SKILL.md`) — trigger, rules, routing.
2. [references/sketch-intake.md](references/sketch-intake.md) — sketch inventory protocol (always load for new intake).
3. Lazy references — load only when the matching task fires (see When To Load References below).

## Core Rules

- **MUST** require at least one user-provided sketch, source-UI resource, or visual direction artifact before producing final assets. If none is available, produce only an `asset-pack.yaml` draft and a list of missing-input questions; do not call image generation.
- **MUST** prefer extraction from user-owned resources (CSS variables, SVGs, component code, source files). Use GPT Image only when an asset genuinely cannot be extracted from any user resource and image-generation access is confirmed. Record in the manifest why the asset required generation.
- **MUST** run `python3 scripts/validate_asset_pack.py <asset-pack.yaml>` before finalizing or handing off any asset pack. Stop and surface validation errors before continuing.
- **MUST NOT** copy third-party brand visuals — no competitor or public design-system icons, colors, symbols, product semantics, grid language, slogans, or distinctive design motifs. Use public design systems for structural taxonomy only.
- Record sketch references, source references, prompts, model settings, license notes, and originality-check results in `manifest.json`.

## Gotchas

- **Calling GPT Image before `validate_asset_pack.py` silently skips the originality check.** The validator must run first; image generation without a passing validation is a policy violation regardless of output quality.
- **Missing sketch reference breaks manifest traceability.** Every asset entry in `manifest.json` must carry a `sketch_refs` value. An empty array is accepted only when the asset is extracted purely from code with no sketch source — document why.
- **`render_contact_sheet.py` depends on `manifest.json` being present and valid.** Running it before the manifest is written produces an empty or malformed contact sheet with no error. Always write the manifest first. (enforcement: advisory)
- **Public design-system structure notes are not licenses.** `examples/public-design-systems/structure-notes.md` documents taxonomy patterns only; loading it does not authorize copying any visual from those systems.
- **No sketch provided ≠ skip intake.** Even when the user provides only text or a brief, run the intake inventory to surface missing inputs before acting. Skipping intake causes silent gaps in the final manifest.

## Quick Workflow

1. **Intake** — inventory sketches and source resources; load [references/sketch-intake.md](references/sketch-intake.md). If inputs are missing, produce draft YAML + question list only.
2. **Brief** — build or update `asset-pack.yaml` from [templates/asset-pack.yaml](templates/asset-pack.yaml); use [references/public-case-model.md](references/public-case-model.md) for module taxonomy.
3. **Validate** — run `python3 scripts/validate_asset_pack.py <asset-pack.yaml>`; stop on errors. (enforcement: manual)
4. **Extract** (default) — load [references/direct-extraction-workflow.md](references/direct-extraction-workflow.md); extract tokens from CSS/source, vectorize to SVG, author component assets. Set `generation.provider: direct-extraction`, `model: none`.
5. **Generate** (fallback only) — when extraction is impossible and image-generation access exists, load [references/gpt-image-workflow.md](references/gpt-image-workflow.md) and record the reason in the manifest.
6. **Package** — save tokens under `tokens/`, vectors/components under `assets/`, raster exports under `dist/`. Write `manifest.json` and `validation.md`.
7. **Contact sheet** — run `python3 scripts/render_contact_sheet.py <manifest.json> --output <contact-sheet.svg>` after manifest is written. (enforcement: manual)

## When To Load References

- Sketch review criteria and intake inventory: [references/sketch-intake.md](references/sketch-intake.md)
- Default extraction path (tokens, SVG, component code): [references/direct-extraction-workflow.md](references/direct-extraction-workflow.md)
- Public design-system module taxonomy: [references/public-case-model.md](references/public-case-model.md)
- Claude Design workflow mapping: [references/claude-design-architecture.md](references/claude-design-architecture.md)
- GPT Image generation/editing (fallback only): [references/gpt-image-workflow.md](references/gpt-image-workflow.md)
- Originality and exclusion rules: [references/originality-policy.md](references/originality-policy.md)

## Examples

- [examples/fixtures/](examples/fixtures/) — minimal synthetic run; one card component extracted from a sample wireframe.
- [examples/public-design-systems/](examples/public-design-systems/) — structural taxonomy notes; no visual assets copied.

## Output Footer

At the end of every invocation the skill prints:

```
Validation: PASS | FAIL  (exit code from validate_asset_pack.py)
Produced files: <count> assets in assets/, <count> tokens in tokens/
Manifest: <path to manifest.json>
Contact sheet: <path to contact-sheet.svg or contact-sheet.png, or "not rendered">
```

If the run stops early (missing sketch inputs, validation failure), the footer is replaced by a single-line status and the list of blocking issues.
