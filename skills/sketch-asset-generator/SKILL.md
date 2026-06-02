---
name: sketch-asset-generator
description: Generate structured, modular, reusable, original visual asset packs from user-provided design sketches, wireframes, whiteboard photos, Figma or Sketch screenshots, low-fidelity UI mocks, moodboards, component layout sketches, or existing UI source (CSS, SVG, components). Prefer extracting assets directly from user-owned resources (design tokens, vectors, component code); use GPT Image generation only when an asset cannot be extracted from any user resource. Use when turning sketches or source UI into design-system-ready assets, asset-pack.yaml briefs, design tokens, SVG and component primitives, manifests, contact sheets, or validation reports, using public design systems only as structural references and never copying third-party brand visuals. Works whether the running agent is Claude or Codex.
---

# Sketch Asset Generator

## Overview

Use this skill to convert user-owned sketches and source UI into a reviewable asset pack. The user's sketch or source resource is the visual source of truth. Public design systems may inform taxonomy, governance, accessibility, and validation only.

Production is **extraction-first**: when an asset already exists in a user-owned resource (CSS tokens, SVGs, existing components, source files), extract or vectorize it directly with code. Use GPT Image generation only as a fallback, for original assets that cannot be extracted from any user resource. An agent that can author code and SVG (e.g. Claude) runs the default extraction path with no external image model.

## Hard Rules

- Prefer direct extraction. When an asset already exists in a user-owned resource (CSS variables, SVGs, existing components, source files), extract or vectorize it directly with code instead of generating an image. Use GPT Image only for assets that genuinely do not exist in any user resource, and only when image-generation access is available. Record in the manifest why a generated asset could not be extracted.
- Require at least one user-provided sketch, source resource, or visual direction artifact before producing final visual assets.
- If no sketch or source resource is available, create only an `asset-pack.yaml` draft and a missing-input question list. Do not call image generation.
- Do not use Stereolabs or any third-party brand's visual elements, colors, symbols, icons, product semantics, grid language, slogans, or distinctive design motifs.
- Do not copy public design-system visuals. Use public cases only to structure assets into foundations, components, patterns, accessibility, and governance.
- Record sketch references, source references, prompts, model settings, license notes, and originality checks in the manifest.

## Workflow

1. Intake sketches and purposes.
   - Load [references/sketch-intake.md](references/sketch-intake.md).
   - Inventory each sketch with a path, intended use, module target, and missing information.
2. Build or update the asset pack brief.
   - Start from [templates/asset-pack.yaml](templates/asset-pack.yaml).
   - Use [references/public-case-model.md](references/public-case-model.md) for module taxonomy.
3. Validate before generation.
   - Run `python3 scripts/validate_asset_pack.py <asset-pack.yaml>`.
   - Stop if validation reports missing sketches or originality-policy violations.
4. Produce assets — extraction-first.
   - Default path (direct extraction): load [references/direct-extraction-workflow.md](references/direct-extraction-workflow.md). Extract design tokens from user CSS/source, vectorize components to SVG, and author reusable assets as code. Set `generation.provider: direct-extraction` and `model: none`. This is the path Claude uses by default.
   - Fallback path (image generation): only when a module's asset cannot be extracted from any user-owned resource, and image-generation access exists, load [references/gpt-image-workflow.md](references/gpt-image-workflow.md) and use sketches as image inputs. Record the reason the asset required generation.
   - Keep generation settings explicit and configurable.
5. Package review outputs.
   - Save tokens under `tokens/`, vector/component assets under `assets/`, and packaged raster exports under `dist/` only when something is rasterized.
   - Create or update `manifest.json` and `validation.md`.
   - Run `python3 scripts/render_contact_sheet.py <manifest.json> --output <contact-sheet.svg>` when assets exist. The SVG renderer is dependency-free; use a `.png` output only when Pillow is installed.

## Reference Routing

- Need the default extraction method (tokens, SVG, component code): read [references/direct-extraction-workflow.md](references/direct-extraction-workflow.md).
- Need public design-system structure: read [references/public-case-model.md](references/public-case-model.md).
- Need sketch review criteria: read [references/sketch-intake.md](references/sketch-intake.md).
- Need Claude Design workflow mapping: read [references/claude-design-architecture.md](references/claude-design-architecture.md).
- Need GPT Image generation/editing choices (fallback only): read [references/gpt-image-workflow.md](references/gpt-image-workflow.md).
- Need originality or exclusion rules: read [references/originality-policy.md](references/originality-policy.md).
