from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

FIG_W = 6.0
FIG_H = 3.5
FIG_W_WIDE = 7.2
FIG_H_WIDE = 4.0

SERIF_FALLBACK = [
    "Times New Roman",
    "Times",
    "Nimbus Roman",
    "Liberation Serif",
    "DejaVu Serif",
]

# Restrained paper palette (monochrome + muted red accent).
PAPER_RED_DARK = "#6f1d1b"
PAPER_RED_MEDIUM = "#8a3a37"
PAPER_RED_LIGHT = "#c8a6a4"
PAPER_GRAY_DARK = "#2f2f2f"
PAPER_GRAY_MEDIUM = "#707070"
PAPER_GRAY_LIGHT = "#d2d2d2"
PAPER_BLUE_MUTED = "#5f6f7a"

DECISION_COLOR_MAP = {
    "stable": "#2ca02c",
    "inconclusive": "#7f7f7f",
    "unstable": "#d62728",
    "missing": "#b8b8b8",
}


def apply_style() -> None:
    plt.rcParams.update(
        {
            # Paper-friendly typography with robust fallback if Times is unavailable.
            "font.family": "serif",
            "font.serif": SERIF_FALLBACK,
            "mathtext.fontset": "stix",
            "font.size": 10.0,
            "axes.labelsize": 10.5,
            "axes.titlesize": 11.0,
            "axes.titleweight": "normal",
            "axes.titlepad": 5.0,
            "axes.labelweight": "normal",
            "axes.facecolor": "white",
            "figure.facecolor": "white",
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "xtick.color": PAPER_GRAY_DARK,
            "ytick.color": PAPER_GRAY_DARK,
            "axes.labelcolor": PAPER_GRAY_DARK,
            "axes.edgecolor": "#8a8a8a",
            "axes.linewidth": 0.75,
            "legend.fontsize": 9.0,
            "legend.frameon": False,
            "legend.borderpad": 0.2,
            "legend.labelspacing": 0.3,
            "legend.handlelength": 1.6,
            "legend.handletextpad": 0.5,
            "axes.grid": True,
            "grid.alpha": 0.12,
            "grid.color": "#a8a8a8",
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.axisbelow": True,
            "lines.linewidth": 2.0,
            "lines.markersize": 4.6,
            "errorbar.capsize": 3.0,
            "figure.figsize": (FIG_W, FIG_H),
            "figure.constrained_layout.use": True,
            # Keep vector text editable and improve raster clarity.
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
        }
    )


def plot_line_with_ci(
    ax: Any,
    *,
    x: list[float],
    y: list[float],
    ci_low: list[float] | None = None,
    ci_high: list[float] | None = None,
    label: str = "estimate",
    ci_label: str = "95% CI",
    color: str = PAPER_RED_DARK,
    alpha: float = 0.18,
    linewidth: float = 2.1,
) -> None:
    if ci_low is not None and ci_high is not None and len(ci_low) == len(x) and len(ci_high) == len(x):
        ax.fill_between(x, ci_low, ci_high, color=color, alpha=alpha, linewidth=0.0, label=ci_label)
    ax.plot(x, y, color=color, linewidth=linewidth, label=label, zorder=3)
    ax.scatter(x, y, s=28, color=color, edgecolor="white", linewidth=0.55, zorder=4)


def add_reference_lines(
    ax: Any,
    *,
    event_x: float | None = 0.0,
    zero_y: float | None = 0.0,
    color: str = PAPER_GRAY_MEDIUM,
) -> None:
    if event_x is not None:
        ax.axvline(float(event_x), linestyle=(0, (4, 4)), color=color, linewidth=1.0)
    if zero_y is not None:
        ax.axhline(float(zero_y), linestyle="-", color=color, linewidth=0.9, alpha=0.9)


def decision_color(decision: str) -> str:
    return DECISION_COLOR_MAP.get(str(decision).strip().lower(), DECISION_COLOR_MAP["missing"])


def save_fig(fig, out_base_path: str | Path) -> dict[str, str]:
    out = Path(out_base_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out.with_suffix(".pdf")
    png_path = out.with_suffix(".png")
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=320)
    plt.close(fig)
    return {"pdf": str(pdf_path), "png": str(png_path)}
