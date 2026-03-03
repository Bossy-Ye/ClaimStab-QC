from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

FIG_W = 6.0
FIG_H = 3.5
FIG_W_WIDE = 7.2
FIG_H_WIDE = 4.0


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (FIG_W, FIG_H),
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )


def save_fig(fig, out_base_path: str | Path) -> dict[str, str]:
    out = Path(out_base_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out.with_suffix(".pdf")
    png_path = out.with_suffix(".png")
    fig.tight_layout()
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    return {"pdf": str(pdf_path), "png": str(png_path)}
