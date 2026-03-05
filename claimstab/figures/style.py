from __future__ import annotations

from pathlib import Path

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


def apply_style() -> None:
    plt.rcParams.update(
        {
            # Paper-friendly typography with robust fallback if Times is unavailable.
            "font.family": "serif",
            "font.serif": SERIF_FALLBACK,
            "mathtext.fontset": "stix",
            "font.size": 10.5,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.labelweight": "semibold",
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 9.5,
            "legend.frameon": True,
            "legend.framealpha": 0.95,
            "legend.facecolor": "white",
            "legend.edgecolor": "#c7c7c7",
            "legend.fancybox": False,
            "legend.borderpad": 0.35,
            "legend.labelspacing": 0.35,
            "legend.handlelength": 1.7,
            "axes.grid": True,
            "grid.alpha": 0.24,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.axisbelow": True,
            "lines.linewidth": 1.8,
            "lines.markersize": 5.5,
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


def save_fig(fig, out_base_path: str | Path) -> dict[str, str]:
    out = Path(out_base_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out.with_suffix(".pdf")
    png_path = out.with_suffix(".png")
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=320)
    return {"pdf": str(pdf_path), "png": str(png_path)}
