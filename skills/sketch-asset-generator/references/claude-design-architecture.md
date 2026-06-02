# Claude Design Architecture Mapping

Use this reference to mirror the useful parts of Claude Design's design-system flow without depending on private Claude projects.

## Workflow Mapping

- Source upload: user provides sketches, screenshots, files, or brand direction.
- Extraction: classify foundations, components, patterns, and visual rules.
- Generated UI kit: produce structured modules and reusable assets from the source.
- Review: create a contact sheet and validation report for human approval.
- Test project: generate representative modules that prove the system works across contexts.
- Publish: package outputs with a manifest so future agents can reuse them.

## Generation Method (Extraction-First)

When the running agent is Claude, the "Generated UI kit" step is performed by **direct
extraction**, not by an external image model:

- Default: extract tokens from user CSS/source and author SVG/component code. See
  [direct-extraction-workflow.md](direct-extraction-workflow.md). Set
  `generation.provider: direct-extraction`, `model: none`.
- Fallback: only when an asset cannot be extracted from any user resource, use GPT
  Image. See [gpt-image-workflow.md](gpt-image-workflow.md).

## Skill Adaptation

This skill differs from Claude Design in four important ways:

- The user's sketch or source resource is mandatory before final asset production.
- Public design systems are structural references, not visual sources.
- Assets are extracted directly from user-owned resources by default; image generation is a fallback.
- Outputs are file-based and auditable: `asset-pack.yaml`, extracted/generated assets, `manifest.json`, `contact-sheet.svg`, and `validation.md`.

## Review Loop

Use a short loop:

1. Draft asset pack from sketches.
2. Validate structure and originality.
3. Generate a small proof set.
4. Review contact sheet.
5. Expand modules only after the proof set passes.
