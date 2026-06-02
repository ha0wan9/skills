# Originality Policy

Generated assets must be original and based on user-provided sketches.

## Forbidden

- Using Stereolabs as an example, source, style target, prompt keyword, token name, or visual reference.
- Copying third-party brand colors, logos, symbols, icons, product semantics, typography, slogans, grid systems, illustrations, or distinctive motifs.
- Asking GPT Image to create an asset "in the style of" a named design system, brand, artist, or proprietary product.
- Treating public design-system screenshots as visual source material.

## Allowed

- Learning structural categories from public design systems.
- Naming generic modules such as foundations, components, patterns, icons, diagrams, or governance.
- Using user-owned sketches as visual inputs.
- Producing original visual systems with documented prompts and review status.

## Required Checks

Before generation:

- Verify every final asset references at least one user sketch.
- Verify prompts contain no forbidden brand names or copying instructions.
- Verify `license_notes` are present.
- Verify the manifest can explain why each asset is original.

Use `scripts/validate_asset_pack.py` to run automated checks.
