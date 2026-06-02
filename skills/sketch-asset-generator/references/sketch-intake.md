# Sketch Intake

Sketch intake turns user-owned visual direction into a generation-ready asset plan.

## Required Fields Per Sketch

- `id`: stable identifier, lowercase with hyphens.
- `path`: local path or attachment reference.
- `purpose`: what the sketch is meant to drive.
- `module_targets`: asset modules informed by the sketch.
- `notes`: composition, hierarchy, interaction state, desired mood, or constraints.
- `rights`: confirmation that the user owns or may use the sketch as input.

## Intake Procedure

1. Confirm at least one sketch or visual direction artifact exists.
2. Assign each sketch to one or more modules.
3. Identify reusable elements: layout, hierarchy, states, marks, icons, components, diagrams, or scene composition.
4. Identify missing information before final generation:
   - target audience
   - output sizes
   - module purpose
   - required formats
   - accessibility constraints
   - license or usage limits
5. If information is missing, generate a question list and keep the workflow in draft mode.

## No-Sketch Behavior

When no sketch exists:

- Create an `asset-pack.yaml` draft with `status: draft`.
- Add `questions` describing exactly what sketch material is needed.
- Do not produce final image prompts for execution.
- Do not call GPT Image or any other image generator.

## Prompt Extraction Notes

When converting sketches to prompts, describe generic visual facts:

- layout structure
- relative hierarchy
- shape language
- density
- interaction state
- intended asset role

Avoid naming third-party brands, copying a known design system's visual appearance, or importing distinctive source motifs not present in the user's sketch.
