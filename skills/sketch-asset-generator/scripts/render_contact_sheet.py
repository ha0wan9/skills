#!/usr/bin/env python3
"""Render a contact sheet from a generated asset manifest."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def asset_entries(manifest: dict) -> list[dict]:
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        raise ValueError("manifest.assets must be a list")
    return [asset for asset in assets if isinstance(asset, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thumb-size", type=int, default=220)
    parser.add_argument("--columns", type=int, default=4)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    entries = asset_entries(manifest)
    if not entries:
        raise SystemExit("No assets found in manifest.")

    base_dir = args.manifest.parent
    if args.output.suffix.lower() == ".svg":
        return render_svg(entries, base_dir, args.output, args.thumb_size, args.columns)

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise SystemExit("Pillow is required for raster contact sheets. Use --output contact-sheet.svg for the dependency-free renderer.")

    columns = max(1, args.columns)
    rows = math.ceil(len(entries) / columns)
    label_h = 58
    padding = 20
    cell_w = args.thumb_size + padding * 2
    cell_h = args.thumb_size + label_h + padding * 2
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, entry in enumerate(entries):
        col = index % columns
        row = index // columns
        x = col * cell_w + padding
        y = row * cell_h + padding
        rel_path = entry.get("path") or entry.get("output_path")
        name = str(entry.get("name") or Path(str(rel_path)).stem)
        module = str(entry.get("module") or entry.get("type") or "asset")
        if not isinstance(rel_path, str):
            raise ValueError(f"asset {index} is missing path")
        image_path = Path(rel_path)
        if not image_path.is_absolute():
            image_path = base_dir / image_path
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".ppm", ".bmp"}:
            continue
        with Image.open(image_path) as img:
            img.thumbnail((args.thumb_size, args.thumb_size))
            tx = x + (args.thumb_size - img.width) // 2
            ty = y + (args.thumb_size - img.height) // 2
            sheet.paste(img.convert("RGB"), (tx, ty))
        draw.rectangle((x, y, x + args.thumb_size, y + args.thumb_size), outline="#d0d0d0")
        draw.text((x, y + args.thumb_size + 10), name[:40], fill="black", font=font)
        draw.text((x, y + args.thumb_size + 28), module[:40], fill="#555555", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(f"Contact sheet written to {args.output}")
    return 0


def render_svg(entries: list[dict], base_dir: Path, output: Path, thumb_size: int, columns: int) -> int:
    columns = max(1, columns)
    rows = math.ceil(len(entries) / columns)
    label_h = 58
    padding = 20
    cell_w = thumb_size + padding * 2
    cell_h = thumb_size + label_h + padding * 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{columns * cell_w}" height="{rows * cell_h}" viewBox="0 0 {columns * cell_w} {rows * cell_h}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
    ]
    for index, entry in enumerate(entries):
        col = index % columns
        row = index // columns
        x = col * cell_w + padding
        y = row * cell_h + padding
        rel_path = entry.get("path") or entry.get("output_path")
        if not isinstance(rel_path, str):
            raise ValueError(f"asset {index} is missing path")
        image_path = Path(rel_path)
        href = image_path if image_path.is_absolute() else (base_dir / image_path).resolve()
        name = escape_xml(str(entry.get("name") or image_path.stem))[:80]
        module = escape_xml(str(entry.get("module") or entry.get("type") or "asset"))[:80]
        ext = image_path.suffix.lower()
        parts.append(f'<rect x="{x}" y="{y}" width="{thumb_size}" height="{thumb_size}" fill="#f8f8f8" stroke="#d0d0d0"/>')
        if ext in {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            parts.append(f'<image href="{escape_xml(str(href))}" x="{x}" y="{y}" width="{thumb_size}" height="{thumb_size}" preserveAspectRatio="xMidYMid meet"/>')
        else:
            parts.append(f'<text x="{x + 16}" y="{y + 52}" font-family="Arial, sans-serif" font-size="22" fill="#555">{escape_xml(ext.lstrip(".").upper() or "FILE")}</text>')
            parts.append(f'<text x="{x + 16}" y="{y + 82}" font-family="Arial, sans-serif" font-size="12" fill="#777">non-visual asset</text>')
        parts.append(f'<text x="{x}" y="{y + thumb_size + 22}" font-family="Arial, sans-serif" font-size="13" fill="#111">{name}</text>')
        parts.append(f'<text x="{x}" y="{y + thumb_size + 42}" font-family="Arial, sans-serif" font-size="12" fill="#555">{module}</text>')
    parts.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    print(f"SVG contact sheet written to {output}")
    return 0


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
