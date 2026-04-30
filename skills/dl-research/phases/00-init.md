# Phase: init

Use when a project needs to map the project-agnostic `dl-research` protocol to
its local infrastructure, or when an existing adapter is missing required
fields.

This phase creates or repairs only the project adapter. It must not create a
research direction, study root, branch, run ledger, or H/E directories unless
the user explicitly invokes `frame` afterward.

## Steps

1. Resolve the project root by locating the repository bootstrap file
   (`AGENTS.md`, `README.md`, or equivalent). Prefer existing project memory
   over guessing infra details.
2. Inspect the minimum project facts needed to fill the adapter:
   - native config system;
   - launch / execution backend;
   - tracking backend;
   - artifact backend;
   - metric parser or eval command;
   - data version source;
   - editable surfaces and protected protocol files.
3. Create or repair `agents/research/adapter.yaml` from
   `templates/adapter.yaml`. Use `agents/research/adapter.md` only for human
   notes that do not fit cleanly in YAML.
4. The adapter must include the required fields listed in
   `references/adapter-contract.md` and present in `templates/adapter.yaml`.
   At time of writing:
   - `research_root_pattern`, `branch_pattern`, `run_name_pattern`;
   - `config_backend`, `execution_backend`, `launch_command`;
   - `metric_parser`, `primary_metric`, `metric_direction`;
   - `tracking_backend`, `artifact_backend`, `data_version_source`;
   - `editable_surface`, `protected_files`;
   - `budget`, `stop_policy`, `seed_policy`;
   - `graph_backend`.
   If contract and template diverge, the contract wins; reconcile both before
   proceeding.
5. Record provenance in the adapter:
   - `instantiated_from`;
   - `adapter_version`;
   - `created_utc` or `last_reviewed_utc`;
   - `owner` when known.
6. Validate that the adapter is project-specific. Do not leave example values
   such as "Hydra here" or "ClearML here" unless they are true project facts.
7. If any required field cannot be derived from project files, write
   `<unknown>` and list the blocking question in `adapter.md`; do not proceed
   to launch-capable phases while launch, metric, protected-file, or
   data-version fields are unknown.

## Hand Off

Set adapter status to `ready` when required fields are concrete. The next phase
is `frame <study-id>` only when the user wants to start a research direction.
