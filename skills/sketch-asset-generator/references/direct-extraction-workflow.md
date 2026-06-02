# Direct Extraction Workflow

This is the **default** asset-production path. Prefer it whenever the asset already
exists, in whole or in part, inside a user-owned resource. Only fall back to image
generation (see [gpt-image-workflow.md](gpt-image-workflow.md)) for assets that
genuinely cannot be extracted.

This is the path an agent uses when it can author code, SVG, and tokens directly
(e.g. Claude). No external image model is required.

## When To Extract vs Generate

Extract directly when the source contains the asset or its building blocks:

- CSS / SCSS variables, theme files, or `:root` token blocks → design tokens.
- Existing SVGs, icon fonts, favicons, or vector components → reusable vectors.
- Live UI source (HTML/JSX/components) → component primitives and patterns.
- Screenshots or concept images with clear geometry → vectorize structure by hand.

Escalate to GPT Image **only** when:

- The asset is genuinely new and absent from every user resource (e.g. an original
  hero illustration, spot art, or conceptual scene), and
- image-generation access is available in the environment.

Record in the manifest *why* any generated asset could not be extracted.

## Extraction Method

1. Read the user-owned source resources listed in the pack's `sketches`/`source_refs`.
2. Tokens: parse color, type, spacing, radius, elevation, and motion values into
   `tokens/<pack-id>.tokens.json` and a matching `tokens/<pack-id>.tokens.css`.
3. Components & patterns: author reusable, original SVG (or component code) primitives
   that reuse the extracted token values. Keep them modular and resolution-independent.
4. Keep a build script (e.g. `scripts/build_assets.py`) so extraction is repeatable and
   auditable rather than a one-off manual edit.
5. Preserve structure and hierarchy from the source; do not import third-party brand
   motifs that are not present in the user's own resources.

## Generation Settings For This Path

Set the `generation` block to reflect that no image model was used:

- `provider: direct-extraction`
- `model: none`
- `quality: source-vector`
- `size: scalable-svg` (or the source's native size)
- `output_format: svg` (or `json` / `css` for token modules)
- `dry_run: true`

## Output Layout

- `tokens/` — extracted design tokens (`*.tokens.json`, `*.tokens.css`).
- `assets/` — vector/component primitives (e.g. `assets/svg/*.svg`).
- `dist/` — packaged raster exports, only when something needs rasterizing.
- `manifest.json`, `validation.md`, `contact-sheet.svg` — review outputs.

## Manifest Requirements

For every extracted asset, record:

- source resource paths (the user-owned files it was derived from)
- sketch reference IDs
- `model: none` and `method: direct-extraction`
- output path
- license notes (user-owned source)
- originality check result (derived from user resources only)
- reviewer status

## Contact Sheet

Use the dependency-free SVG renderer; it needs no Pillow:

```
python3 scripts/render_contact_sheet.py <manifest.json> --output contact-sheet.svg
```
