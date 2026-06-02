#!/usr/bin/env python3
"""Validate a sketch asset-pack YAML/JSON file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FORBIDDEN_TERMS = [
    "stereolabs",
    "zed camera",
    "terra ai",
    "precision through perception",
]

MODULE_TYPES = {
    "foundation",
    "icon",
    "diagram",
    "component",
    "pattern",
    "illustration",
    "background",
}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load_pack(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError:
        data = parse_simple_yaml(text)
        if not isinstance(data, dict):
            raise ValueError("asset pack must parse to an object")
        return data
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("asset pack must parse to an object")
    return data


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    return value


def yaml_lines(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        rows.append((indent, raw.strip()))
    return rows


def split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"expected key/value line: {text}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def parse_simple_yaml(text: str) -> Any:
    """Parse the constrained YAML shape used by templates/asset-pack.yaml.

    This is intentionally small: mappings, lists, scalars, and nested list
    items that are mappings. It is not a general YAML parser.
    """

    rows = yaml_lines(text)

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(rows):
            return {}, index
        if rows[index][0] < indent:
            return {}, index
        is_list = rows[index][0] == indent and rows[index][1].startswith("- ")
        if is_list:
            result: list[Any] = []
            while index < len(rows):
                row_indent, content = rows[index]
                if row_indent != indent or not content.startswith("- "):
                    break
                rest = content[2:].strip()
                index += 1
                if rest == "":
                    child, index = parse_block(index, indent + 2)
                    result.append(child)
                elif ":" in rest:
                    key, value = split_key_value(rest)
                    item: dict[str, Any] = {key: parse_scalar(value)} if value else {}
                    if not value:
                        child, index = parse_block(index, indent + 2)
                        item[key] = child
                    if index < len(rows) and rows[index][0] > indent:
                        child, index = parse_block(index, indent + 2)
                        if isinstance(child, dict):
                            item.update(child)
                    result.append(item)
                else:
                    result.append(parse_scalar(rest))
            return result, index

        result: dict[str, Any] = {}
        while index < len(rows):
            row_indent, content = rows[index]
            if row_indent != indent or content.startswith("- "):
                break
            key, value = split_key_value(content)
            index += 1
            if value:
                result[key] = parse_scalar(value)
            else:
                child, index = parse_block(index, indent + 2)
                result[key] = child
        return result, index

    parsed, end = parse_block(0, rows[0][0] if rows else 0)
    if end != len(rows):
        raise ValueError(f"could not parse YAML near line: {rows[end][1]}")
    return parsed


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(flatten_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten_strings(item))
        return out
    return []


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(pack: dict[str, Any], base_dir: Path, check_files: bool) -> list[str]:
    errors: list[str] = []

    pack_id = pack.get("pack_id")
    require(isinstance(pack_id, str) and bool(ID_RE.match(pack_id)), "pack_id must be lowercase hyphen-case", errors)
    require(pack.get("status") in {"draft", "ready", "generated", "reviewed"}, "status must be draft, ready, generated, or reviewed", errors)

    source_refs = pack.get("source_refs")
    require(isinstance(source_refs, dict), "source_refs is required", errors)
    if isinstance(source_refs, dict):
        require(isinstance(source_refs.get("public_structure_refs"), list), "source_refs.public_structure_refs must be a list", errors)
        require(isinstance(source_refs.get("excluded_visual_refs"), list), "source_refs.excluded_visual_refs must be a list", errors)

    sketches = pack.get("sketches")
    require(isinstance(sketches, list) and len(sketches) > 0, "at least one sketch is required before final generation", errors)
    sketch_ids: set[str] = set()
    if isinstance(sketches, list):
        for index, sketch in enumerate(sketches):
            prefix = f"sketches[{index}]"
            require(isinstance(sketch, dict), f"{prefix} must be an object", errors)
            if not isinstance(sketch, dict):
                continue
            sketch_id = sketch.get("id")
            require(isinstance(sketch_id, str) and bool(ID_RE.match(sketch_id)), f"{prefix}.id must be lowercase hyphen-case", errors)
            if isinstance(sketch_id, str):
                sketch_ids.add(sketch_id)
            for key in ("path", "purpose", "rights"):
                require(isinstance(sketch.get(key), str) and bool(sketch.get(key).strip()), f"{prefix}.{key} is required", errors)
            require(isinstance(sketch.get("module_targets"), list) and len(sketch.get("module_targets", [])) > 0, f"{prefix}.module_targets must be a non-empty list", errors)
            sketch_path = sketch.get("path")
            if check_files and isinstance(sketch_path, str):
                require((base_dir / sketch_path).exists(), f"{prefix}.path does not exist: {sketch_path}", errors)

    generation = pack.get("generation")
    require(isinstance(generation, dict), "generation is required", errors)
    if isinstance(generation, dict):
        for key in ("provider", "model", "quality", "size", "output_format"):
            require(isinstance(generation.get(key), str) and bool(generation.get(key).strip()), f"generation.{key} is required", errors)
        require(isinstance(generation.get("dry_run"), bool), "generation.dry_run must be true or false", errors)

    modules = pack.get("modules")
    require(isinstance(modules, list) and len(modules) > 0, "modules must be a non-empty list", errors)
    if isinstance(modules, list):
        for index, module in enumerate(modules):
            prefix = f"modules[{index}]"
            require(isinstance(module, dict), f"{prefix} must be an object", errors)
            if not isinstance(module, dict):
                continue
            require(isinstance(module.get("id"), str) and bool(ID_RE.match(module.get("id", ""))), f"{prefix}.id must be lowercase hyphen-case", errors)
            require(module.get("type") in MODULE_TYPES, f"{prefix}.type must be one of {sorted(MODULE_TYPES)}", errors)
            refs = module.get("sketch_refs")
            require(isinstance(refs, list) and len(refs) > 0, f"{prefix}.sketch_refs must be a non-empty list", errors)
            if isinstance(refs, list):
                for ref in refs:
                    require(ref in sketch_ids, f"{prefix}.sketch_refs contains unknown sketch id: {ref}", errors)
            require(isinstance(module.get("outputs"), list) and len(module.get("outputs", [])) > 0, f"{prefix}.outputs must be a non-empty list", errors)
            require(isinstance(module.get("prompt_brief"), str) and bool(module.get("prompt_brief").strip()), f"{prefix}.prompt_brief is required", errors)
            require(isinstance(module.get("acceptance_criteria"), list) and len(module.get("acceptance_criteria", [])) > 0, f"{prefix}.acceptance_criteria must be non-empty", errors)
            require(isinstance(module.get("license_notes"), str) and bool(module.get("license_notes").strip()), f"{prefix}.license_notes is required", errors)

    haystack = "\n".join(flatten_strings(pack)).lower()
    for term in FORBIDDEN_TERMS:
        require(term not in haystack, f"forbidden originality-policy term found: {term}", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_pack", type=Path)
    parser.add_argument("--check-files", action="store_true", help="Require sketch paths to exist.")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="Base directory for sketch paths when --check-files is used.")
    args = parser.parse_args()

    try:
        pack = load_pack(args.asset_pack)
        errors = validate(pack, args.base_dir, args.check_files)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("Asset pack validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Asset pack validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
