#!/usr/bin/env python3
"""Chart generator for stereo-matching-edge-fm survey v1.

Reads `chart_data.csv` and produces:
  1. params_vs_accuracy.png  — params (log) on x, error % on y (lower better),
                               color = arch family
  2. speed_torch_vs_accuracy.png  — runtime (ms) on x, error % on y. Uses
                                    PyTorch-eager runtime as a Torch-Compile
                                    proxy when no torch.compile number is
                                    reported (this is a known gap, see
                                    survey §10).
  3. speed_trt_vs_accuracy.png    — TensorRT version. Currently has no data
                                    (literature gap SQ6); renders an
                                    explanation panel.

Y-axis is the zero-shot Mean error metric from FoundationStereo's Stereo
Anything Table II = avg(KITTI-12 D1, KITTI-15 D1, Middlebury Bad-2, ETH3D
Bad-1). Lower is better. We plot it with an inverted-axis convention so
that "higher on the chart = better model".

Usage:
    python3 generate_charts.py [chart_data.csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ARCH_COLORS = {
    "CNN": "#1f77b4",
    "Transformer": "#ff7f0e",
    "Hybrid": "#2ca02c",
    "Foundation-VFM": "#d62728",
    "SSM-Mamba": "#9467bd",
    "Recurrent-RAFT": "#8c564b",
}

ARCH_MARKERS = {
    "CNN": "s",
    "Transformer": "o",
    "Hybrid": "^",
    "Foundation-VFM": "D",
    "SSM-Mamba": "P",
    "Recurrent-RAFT": "v",
}


def f(v):
    if v in (None, "", "—"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load(path: Path) -> list[dict]:
    rows = []
    with path.open() as h:
        for r in csv.DictReader(h):
            r["params_M"] = f(r.get("params_M"))
            r["accuracy_inv"] = f(r.get("accuracy_inv"))
            r["latency_torch_ms"] = f(r.get("latency_torch_ms"))
            r["latency_trt_ms"] = f(r.get("latency_trt_ms"))
            rows.append(r)
    return rows


def _scatter(ax, rows, x_key):
    seen = set()
    for r in rows:
        x = r.get(x_key)
        y = r.get("accuracy_inv")
        if x is None or y is None:
            continue
        arch = r.get("architecture", "Unknown")
        ax.scatter(
            x, y,
            c=ARCH_COLORS.get(arch, "#7f7f7f"),
            marker=ARCH_MARKERS.get(arch, "x"),
            s=140, edgecolors="black", linewidths=0.5, alpha=0.85,
            label=arch if arch not in seen else None,
        )
        seen.add(arch)
        ax.annotate(
            r.get("model", ""), (x, y),
            xytext=(6, 4), textcoords="offset points", fontsize=8,
        )


def plot_params(rows, out: Path):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    _scatter(ax, rows, "params_M")
    ax.set_xscale("log")
    ax.set_xlabel("Parameters (M, log scale)")
    ax.set_ylabel("Zero-shot Mean error (%) — lower = better")
    ax.invert_yaxis()
    ax.set_title(
        "Stereo Matching: Parameters vs Zero-shot Accuracy (2020+)\n"
        "Y axis = Mean of (KITTI-12 D1, KITTI-15 D1, Middlebury Bad-2, ETH3D Bad-1) — Stereo Anything Table II"
    )
    n_plotted = sum(1 for r in rows if r["params_M"] is not None and r["accuracy_inv"] is not None)
    ax.text(
        0.02, 0.02, f"{n_plotted}/{len(rows)} models plotted (rest miss params or accuracy)",
        transform=ax.transAxes, fontsize=8, va="bottom",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
    )
    if any(r.get("architecture") for r in rows):
        ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()


def plot_speed(rows, baseline: str, out: Path):
    key = "latency_torch_ms" if baseline == "torch" else "latency_trt_ms"
    label = "PyTorch eager (proxy for Torch Compile — no paper reports torch.compile)" if baseline == "torch" else "TensorRT"
    fig, ax = plt.subplots(figsize=(11, 6.5))
    available = [r for r in rows if r.get(key) is not None and r["accuracy_inv"] is not None]
    if not available:
        ax.text(
            0.5, 0.5,
            f"No {label} latency × accuracy pairs found in indexed papers.\n\n"
            "This is a confirmed literature gap: in 2020-2026 stereo matching\n"
            "abstracts, no paper reports TensorRT engine latency on a common\n"
            "hardware tier. To populate this chart, open repo READMEs of the\n"
            "deployment-friendly models (P001/P002/P011/P016) and grep for\n"
            "TensorRT / Jetson / engine — see survey §13 task R2-H.",
            ha="center", va="center", transform=ax.transAxes, fontsize=11,
            bbox=dict(boxstyle="round", facecolor="lightyellow"),
        )
        ax.set_title(f"Stereo Matching: Speed vs Accuracy under {label.split('—')[0].strip()} baseline")
        plt.tight_layout()
        plt.savefig(out, dpi=120)
        plt.close()
        return
    _scatter(ax, rows, key)
    ax.set_xlabel(f"Inference latency (ms; {label})")
    ax.set_ylabel("Zero-shot Mean error (%) — lower = better")
    ax.invert_yaxis()
    ax.set_title(
        f"Stereo Matching: Speed vs Zero-shot Accuracy under {label.split('—')[0].strip()} baseline\n"
        "Hardware varies across papers (RAFT-Stereo / IGEV / Selective: HW unspecified; DEFOM: RTX 4090). "
        "Cross-paper comparison is approximate."
    )
    ax.text(
        0.02, 0.02,
        f"{len(available)}/{len(rows)} models plotted; HW heterogeneous (see legend annotations).",
        transform=ax.transAxes, fontsize=8, va="bottom",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
    )
    if any(r.get("architecture") for r in rows):
        ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()


def main(argv: list[str]) -> int:
    csv_path = Path(argv[1] if len(argv) > 1 else "chart_data.csv")
    if not csv_path.is_file():
        print(f"missing: {csv_path}", file=sys.stderr)
        return 2
    rows = load(csv_path)
    plot_params(rows, csv_path.parent / "01_params_vs_accuracy.png")
    plot_speed(rows, "torch", csv_path.parent / "02_speed_torch_vs_accuracy.png")
    plot_speed(rows, "trt", csv_path.parent / "03_speed_trt_vs_accuracy.png")
    print(f"wrote 3 charts under {csv_path.parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
