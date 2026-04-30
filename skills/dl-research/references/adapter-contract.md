# Adapter Contract

Use an adapter to map the generic research protocol onto the current project.
For real projects, prefer a project-local adapter at
`agents/research/adapter.yaml` with optional human notes in
`agents/research/adapter.md`. A study `index.md` links to this adapter and
records the resolved study root. Inline adapter fields in `index.md` are
allowed only for small one-off studies without a project harness.

`dl-research` is a meta skill. Do not put project-specific defaults such as
ClearML queue names, Hydra config paths, dataset IDs, or eval scripts in the
global skill files; put them in the project adapter.

## Required Fields

These match `templates/adapter.yaml` one-to-one. Any addition or removal must
be applied in both places and in `phases/00-init.md`.

- `research_root_pattern`: where study files live, for example
  `agents/research/<study-id>/`.
- `branch_pattern`: branch/worktree identity for a research direction, for
  example `res/<study-id>`.
- `run_name_pattern`: run prefix including the H/E slug, for example
  `<study-id>-<HnEn>-<experiment-name>`.
- `config_backend`: how experiment settings are represented.
- `execution_backend`: how jobs run.
- `launch_command`: exact command or template for launching runs.
- `metric_parser`: deterministic command, script, or query that extracts the
  primary metric. Avoid manual extraction rules; if extraction is manual,
  capture the exact procedure here so the parser is reproducible.
- `primary_metric`: metric name (string).
- `metric_direction`: `minimize` or `maximize`.
- `tracking_backend`: where run status and metrics are observed.
- `artifact_backend`: where checkpoints, logs, plots, and reports are stored.
- `data_version_source`: how train/eval data and splits are identified.
- `editable_surface`: files, config groups, notebooks, or scripts the workflow
  may change.
- `protected_files`: eval harness, metric parser, data split definitions,
  secrets, and other files that require protocol-change approval.
- `budget`: wall-clock, compute, trial, or cost limit.
- `stop_policy`: timeout, early-stop, crash, and retry rules.
- `seed_policy`: fixed seed, seed sweep, or repeated-trial rule.
- `graph_backend`: graph formats and generation rule for synthesis. The
  default expected outputs are `research_graph.mmd` and
  `research_graph.json`.

## Optional Fields

- `baseline_source`: checkpoint, run ID, paper number, or command.
- `reporting_target`: issue, doc, paper, dashboard, or project memory.
- `remote_constraints`: queues, accelerators, containers, package sync, or
  scheduler limits.
- `adapter_version`, `instantiated_from`, `created_utc`, `last_reviewed_utc`,
  `owner`: provenance and review metadata.

## Example Backend Values

These are examples only, not required behavior:

- config backend: Hydra, argparse, YAML, Python dataclass, notebook parameters;
- execution backend: local shell, Slurm, Kubernetes, ClearML, W&B Launch;
- tracking backend: ClearML, W&B, MLflow, TensorBoard, CSV ledger;
- artifact backend: local filesystem, object storage, tracker artifacts,
  model hub.

## Protocol-Change Rule

Changing protected files, eval data, primary metric, parser, baseline source,
or seed policy changes the study protocol. Record the proposed change, reason,
approval, and effective run ID before using it.

## H/E ID Rule

For multi-route studies, the adapter's run-name pattern must support:

- display IDs like `H1.E1`;
- slugs like `H1E1`;
- directory paths like `H1-<track-name>/E1-<experiment-name>/`.

The root ledger remains global and must include enough H/E fields to compare
routes without opening every nested artifact.
