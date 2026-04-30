#!/usr/bin/env python3
"""Render local USER.md from the Project Meta preference questionnaire.

The script treats USER.template.md as input, not as a target-project artifact.
It writes only selected preferences into target-root USER.md unless the user
explicitly asks for a full editable checklist.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "USER.template.md"
IGNORE_RULES = ("/USER.md", "/USER.template.md")

PRESET_RE = re.compile(r"^- \[ \] ([^:]+): (.+)$")
ITEM_RE = re.compile(r"^- \[ \] (.+)$")


@dataclass(frozen=True)
class Preset:
    name: str
    description: str


@dataclass(frozen=True)
class PreferenceItem:
    category: str
    text: str


@dataclass(frozen=True)
class PreferenceTemplate:
    presets: list[Preset]
    items: list[PreferenceItem]


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def split_values(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def parse_template(path: Path) -> PreferenceTemplate:
    section = ""
    category = ""
    presets: list[Preset] = []
    items: list[PreferenceItem] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading in {"Presets", "Preference Checklist"}:
                section = heading
            else:
                section = ""
            continue

        if section == "Presets":
            match = PRESET_RE.match(line)
            if match:
                presets.append(Preset(match.group(1).strip(), match.group(2).strip()))
            continue

        if section == "Preference Checklist":
            if line.startswith("### "):
                category = line[4:].strip()
                continue
            match = ITEM_RE.match(line)
            if match and category:
                items.append(PreferenceItem(category, match.group(1).strip()))

    if not presets:
        raise ValueError(f"No presets found in {path}")
    if not items:
        raise ValueError(f"No preference checklist items found in {path}")
    return PreferenceTemplate(presets=presets, items=items)


def resolve_preset(value: str, template: PreferenceTemplate) -> Preset:
    wanted = normalize(value)
    for preset in template.presets:
        if normalize(preset.name) == wanted:
            return preset
    choices = ", ".join(preset.name for preset in template.presets)
    raise ValueError(f"Unknown preset {value!r}. Choose one of: {choices}")


def index_items(template: PreferenceTemplate) -> dict[str, list[PreferenceItem]]:
    by_category: dict[str, list[PreferenceItem]] = {}
    for item in template.items:
        by_category.setdefault(normalize(item.category), []).append(item)
    return by_category


def resolve_enabled_items(values: list[str], template: PreferenceTemplate) -> set[PreferenceItem]:
    enabled: set[PreferenceItem] = set()
    by_category = index_items(template)
    by_item = {normalize(item.text): item for item in template.items}

    for value in split_values(values):
        key = normalize(value)
        if key in by_category:
            enabled.update(by_category[key])
            continue
        if key in by_item:
            enabled.add(by_item[key])
            continue
        raise ValueError(f"Unknown preference category or item: {value!r}")

    return enabled


def print_questionnaire(template: PreferenceTemplate) -> None:
    print("Presets:")
    for index, preset in enumerate(template.presets, start=1):
        print(f"  {index}. {preset.name}: {preset.description}")

    print("\nChecklist:")
    current = ""
    for index, item in enumerate(template.items, start=1):
        if item.category != current:
            current = item.category
            print(f"\n{current}:")
        print(f"  {index}. {item.text}")


def choose_preset_interactively(template: PreferenceTemplate) -> Preset:
    while True:
        raw = input("Choose preset by name or number: ").strip()
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(template.presets):
                return template.presets[index - 1]
        try:
            return resolve_preset(raw, template)
        except ValueError as exc:
            print(exc, file=sys.stderr)


def choose_items_interactively(template: PreferenceTemplate) -> set[PreferenceItem]:
    if not sys.stdin.isatty():
        return set()

    raw = input(
        "Enable optional categories or item numbers "
        "(comma-separated, blank for none): "
    ).strip()
    if not raw:
        return set()

    enabled: set[PreferenceItem] = set()
    values = split_values([raw])
    named_values: list[str] = []
    for value in values:
        if value.isdigit():
            index = int(value)
            if 1 <= index <= len(template.items):
                enabled.add(template.items[index - 1])
            else:
                raise ValueError(f"Unknown item number: {value}")
        else:
            named_values.append(value)

    enabled.update(resolve_enabled_items(named_values, template))
    return enabled


def render_user_md(
    preset: Preset,
    template: PreferenceTemplate,
    enabled_items: set[PreferenceItem],
    freeform: list[str],
    full_checklist: bool,
) -> str:
    lines = [
        "# User Preferences",
        "",
        "Generated by Project Meta from the installed preference questionnaire.",
        "Local-only target configuration. Do not commit this file.",
        "",
        f"Selected preset: {preset.name}",
        "",
        "## Preset",
        "",
        f"- [x] {preset.name}: {preset.description}",
        "",
    ]

    if full_checklist:
        lines.extend(["## Preference Checklist", ""])
        categories = {item.category for item in template.items}
        for category in sorted(categories, key=lambda name: [i.category for i in template.items].index(name)):
            lines.extend([f"### {category}", ""])
            for item in [item for item in template.items if item.category == category]:
                mark = "x" if item in enabled_items else " "
                lines.append(f"- [{mark}] {item.text}")
            lines.append("")
    elif enabled_items:
        lines.extend(["## Selected Preferences", ""])
        categories = {item.category for item in enabled_items}
        for category in sorted(categories, key=lambda name: [i.category for i in template.items].index(name)):
            lines.extend([f"### {category}", ""])
            for item in [item for item in template.items if item.category == category and item in enabled_items]:
                lines.append(f"- [x] {item.text}")
            lines.append("")

    if freeform:
        lines.extend(["## Free-Form Preferences", ""])
        for item in freeform:
            lines.append(f"- [x] {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def ensure_ignore_rules(target_root: Path) -> None:
    gitignore = target_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing = [rule for rule in IGNORE_RULES if rule not in existing.splitlines()]
    if not missing:
        return

    prefix = "" if not existing or existing.endswith("\n") else "\n"
    block = "\n# Project Meta local user preferences\n" + "\n".join(missing) + "\n"
    gitignore.write_text(existing + prefix + block, encoding="utf-8")


def should_overwrite(output: Path, reset: bool, yes: bool) -> bool:
    if not output.exists() or reset or yes:
        return True
    if not sys.stdin.isatty():
        raise ValueError(f"{output} already exists; pass --reset to overwrite it")
    raw = input(f"{output} exists. Overwrite? [y/N] ").strip().lower()
    return raw in {"y", "yes"}


def resolve_output_path(output: Path | None, target_root: Path) -> Path:
    path = target_root / "USER.md" if output is None else output
    if not path.is_absolute():
        path = target_root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(target_root)
    except ValueError as exc:
        raise ValueError(f"output must stay under target root: {path}") from exc
    if resolved.name != "USER.md":
        raise ValueError("output filename must be USER.md")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Preference template to read")
    parser.add_argument("--target-root", type=Path, default=Path.cwd(), help="Target project root")
    parser.add_argument("--output", type=Path, default=None, help="Output USER.md path")
    parser.add_argument("--preset", help="Preset name for non-interactive rendering")
    parser.add_argument("--enable", action="append", default=[], help="Category or item to enable; repeatable")
    parser.add_argument("--freeform", action="append", default=[], help="Extra selected preference line; repeatable")
    parser.add_argument("--full-checklist", action="store_true", help="Render unselected checklist items too")
    parser.add_argument("--reset", action="store_true", help="Overwrite an existing USER.md")
    parser.add_argument("--yes", action="store_true", help="Assume yes for overwrite prompts")
    parser.add_argument("--ensure-ignore", action="store_true", help="Ensure USER.md ignore rules exist")
    parser.add_argument("--list", action="store_true", help="Print presets and checklist without writing")
    parser.add_argument("--dry-run", action="store_true", help="Print rendered USER.md instead of writing")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        template_path = args.template.resolve(strict=True)
        target_root = args.target_root.resolve(strict=True)
        template = parse_template(template_path)

        if args.list:
            print_questionnaire(template)
            return 0

        if args.preset:
            preset = resolve_preset(args.preset, template)
        else:
            print_questionnaire(template)
            preset = choose_preset_interactively(template)

        enabled_items = resolve_enabled_items(args.enable, template)
        if not args.enable and not args.preset:
            enabled_items = choose_items_interactively(template)

        rendered = render_user_md(
            preset=preset,
            template=template,
            enabled_items=enabled_items,
            freeform=args.freeform,
            full_checklist=args.full_checklist,
        )

        if args.dry_run:
            print(rendered, end="")
            return 0

        output = resolve_output_path(args.output, target_root)
        if not should_overwrite(output, args.reset, args.yes):
            print("Aborted.", file=sys.stderr)
            return 1

        if args.ensure_ignore:
            ensure_ignore_rules(target_root)
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote {output}")
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
