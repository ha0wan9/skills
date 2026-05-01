# skills

Agent harness skills published as a Claude Code plugin marketplace. The repo follows the [`anthropics/skills`](https://github.com/anthropics/skills) layout: a flat `skills/<name>/` directory plus a `.claude-plugin/marketplace.json` declaring each installable plugin.

Each skill in `skills/` is independently installable by name. The plugin manifest at [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) declares two plugins (`project-meta`, `dl-research`), each pointing at one skill directory.

## Skills

| Plugin | Path | Description |
|---|---|---|
| `project-meta` | [`skills/project-meta/`](skills/project-meta/) | Bootstrap, audit, and evolve a repository agent-work harness — canonical memory, execution rules, multi-agent protocols, project-specific artifact instantiation, pre-commit delivery. Surface commands: `/project-meta init`, `/project-meta status`, `/project-meta validate`, `/project-meta deliver`, `/project-meta audit`. |
| `dl-research` | [`skills/dl-research/`](skills/dl-research/) | Rigorous Deep Learning research workflows: frame, survey, design, prepare, launch, monitor, evaluate, synthesize, audit, plus a bounded autonomous ratchet loop. Project-agnostic; uses an adapter for backend integration. |
| `deep-survey-bfs` | [`skills/deep-survey-bfs/`](skills/deep-survey-bfs/) | Breadth-first literature surveys with hard coverage gates: frame → Round 1 broad search → gap audit (sub-question × dimension matrix) → Round N gap-fill → synthesize multi-axis taxonomy + per-paper deep-dives + multi-tier reading list. Anti-hallucination via `claims.jsonl` contract. |

## Install

This repo is a Claude Code plugin marketplace. Install the marketplace once, then install one or both plugins by name.

From a git repo URL (`git@github.com:ha0wan9/skills.git` or `https://github.com/ha0wan9/skills`):

```text
/plugin marketplace add ha0wan9/skills
/plugin install project-meta@ha0wan9-skills
/plugin install dl-research@ha0wan9-skills
/plugin install deep-survey-bfs@ha0wan9-skills
```

Each `/plugin install` resolves the plugin name from `.claude-plugin/marketplace.json` and copies the referenced skill directory into the user's plugin store. Skills install independently; you can install one without the other.

For users who do not use the plugin marketplace, manual install copies one skill subdirectory into the agent's skills directory:

```bash
cp -R /path/to/skills/skills/project-meta    ~/.claude/skills/project-meta
cp -R /path/to/skills/skills/dl-research     ~/.claude/skills/dl-research
cp -R /path/to/skills/skills/deep-survey-bfs ~/.claude/skills/deep-survey-bfs
```

## Bounded Doc Loading

The `project-meta` skill ships `scripts/extract_doc_context.py` for heading-first bounded reads of long shared docs. From a target repo:

```bash
python3 ~/.claude/skills/project-meta/scripts/extract_doc_context.py README.md --index
python3 ~/.claude/skills/project-meta/scripts/extract_doc_context.py README.md --heading "Install" --query "git repo" --within-lines 80 --max-lines 40
```

The extractor reads Markdown headings first, searches within the selected heading window, and prints a heading-first line-numbered excerpt. It uses only the Python standard library.

## Local Development

Skills here are versioned with the marketplace. Both skills are dependency-free Python where applicable, and ship their own validators inside `skills/<name>/scripts/` when the validator is for end users (e.g. `dl-research/scripts/validate_ledger.py`, `project-meta/scripts/validate_target_harness.py`).

The dev-only validator at `scripts/validate_project_meta.py` (this repo's root, not shipped) validates the project-meta skill content under `skills/project-meta/`:

```bash
python3 scripts/validate_project_meta.py
```

It checks skill metadata, reference routing, canonical memory boundaries, protocol completeness, UI metadata, prompt-based trigger cases, template provenance, the bounded doc context extractor, and the user preference renderer.

## Repo Layout

```text
skills/
├── .claude-plugin/
│   └── marketplace.json           # plugin manifest declaring project-meta and dl-research
├── README.md                      # this file
├── AGENTS.md                      # repo-meta routing for agents working on the marketplace
├── .gitignore
├── scripts/
│   └── validate_project_meta.py   # dev validator for the project-meta skill (NOT shipped)
└── skills/                        # flat skill directory, Anthropic-pattern
    ├── project-meta/
    │   ├── SKILL.md
    │   ├── USER.template.md
    │   ├── .gitignore.template
    │   ├── agents/openai.yaml
    │   ├── references/
    │   ├── templates/
    │   └── scripts/
    │       ├── extract_doc_context.py
    │       ├── render_user_preferences.py
    │       └── validate_target_harness.py
    ├── dl-research/
    │   ├── SKILL.md
    │   ├── agents/openai.yaml
    │   ├── modes/
    │   ├── phases/
    │   ├── references/
    │   ├── templates/
    │   └── scripts/validate_ledger.py
    └── deep-survey-bfs/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── phases/      # 00-frame, 01-round1, 02-gap-audit, 03-roundN, 04-synthesize, 05-version
        ├── references/  # source-coverage, paper-rating-rubric, coverage-matrix, claims-discipline, taxonomy-revision, bias-audit
        ├── templates/   # survey-index, paper-index, coverage-matrix, survey-skeleton, claims.schema.json
        └── scripts/     # arxiv_search, coverage_check, claims_validate, bias_audit
```

The `skills/<name>/` flat layout mirrors `anthropics/skills` and is what `/plugin install` expects when reading `marketplace.json`.

## License

Skills published in this repo are MIT-licensed by the repo owner unless a `LICENSE` file inside a particular skill says otherwise.
