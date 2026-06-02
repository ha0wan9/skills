# GPT Image Workflow (Fallback Path)

This is the **fallback** path, not the default. Before using it, confirm the asset
cannot be extracted from a user-owned resource — see
[direct-extraction-workflow.md](direct-extraction-workflow.md). Use GPT Image only for
original assets that are genuinely absent from every user resource (e.g. a new
illustration or hero scene) and only when image-generation access is available. Record
in the manifest why the asset required generation rather than extraction.

Use GPT Image for original assets derived from user sketches.

## API Choice

- Use the Image API when one prompt and one sketch context can produce or edit a single asset.
- Use the Responses API when the user needs multi-turn refinement, previous image context, or iterative edits.
- Keep the GPT Image model configurable. Do not hardcode a model unless the user's environment requires one.

## Required Prompt Inputs

Each generation prompt must include:

- asset module and type
- sketch reference IDs
- intended use
- visual constraints derived from the sketch
- output size, format, background, and quality
- originality instruction
- forbidden references, including Stereolabs and any third-party visual identity not owned by the user

## Generation Settings

Store settings in `asset-pack.yaml`:

- `model`
- `quality`
- `size`
- `output_format`
- `background`
- `moderation`
- optional `mask`
- optional `style_reference_strength`

## Manifest Requirements

For every generated asset, record:

- source sketch IDs
- prompt
- revised prompt, when available
- model and settings
- output path
- license notes
- originality check result
- reviewer status

## Safety Stop

Stop before generation if:

- no sketch is referenced
- the prompt asks to copy a third-party design system or brand
- Stereolabs or another excluded brand appears in prompt text
- license notes are missing
- output ownership is unclear
