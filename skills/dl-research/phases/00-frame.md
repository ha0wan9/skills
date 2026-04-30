# Phase: frame

Use when a study is first articulated or when an existing study lacks a stable
question, scope, adapter, or success criteria.

## Steps

1. Resolve `study-id`. If absent, propose 2-3 kebab-case names and ask the
   user to choose.
2. Confirm or create the study root. If a project adapter exists, use its
   `research_root_pattern`; otherwise default to
   `.research/studies/<study-id>/`.
3. If this is a real project and no project adapter exists, stop and run
   `init`. Load `references/adapter-contract.md` only to explain the missing
   adapter. Do not proceed with launch-capable phases while launch, metric,
   protected-file, or data-version fields are unknown.
4. Scaffold `index.md` from `templates/study-index.md`.
5. Fill the immutable protocol:
   - research question and decision it feeds;
   - success criteria and primary metric direction;
   - baseline/control requirement;
   - in-scope and out-of-scope work;
   - data split/version source;
   - budget and stop policy;
   - editable surface and protected files.
6. Record the adapter path, resolved study root, and branch pattern in
   `index.md`. For the preferred convention, branch is `res/<study-id>` and
   root is `agents/research/<study-id>/`.
7. Create `runs.jsonl`, `artifacts/`, `audits/`, `research_graph.mmd`, and
   `research_graph.json` placeholders under the study root if missing.
8. If multiple hypothesis routes are already known, create only the necessary
   `Hn-<track-name>/index.md` skeletons. Do not create `En` directories before
   design/prepare identifies concrete experiments.

## Hand Off

Set status to `framed`. The next phase is usually `survey`, with the specific
unknowns that must be resolved before designing experiments.
