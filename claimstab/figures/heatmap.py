from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


def plot_fliprate_heatmap(df: pd.DataFrame, out_path: str | Path, *, metric: str = "flip_rate_mean") -> dict[str, str] | None:
    if df.empty:
        return None
    if "claim_pair" not in df.columns or "delta" not in df.columns or metric not in df.columns:
        return None

    apply_style()
    claims = sorted({str(v) for v in df["claim_pair"].tolist()})
    deltas = sorted({str(v) for v in df["delta"].tolist()})
    if not claims or not deltas:
        return None
    matrix = np.full((len(claims), len(deltas)), np.nan, dtype=float)
    for _, row in df.iterrows():
        i = claims.index(str(row["claim_pair"]))
        j = deltas.index(str(row["delta"]))
        try:
            matrix[i, j] = float(row[metric])
        except Exception:
            matrix[i, j] = np.nan

    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    if metric.startswith("flip_rate") or metric.startswith("stability"):
        im = ax.imshow(matrix, aspect="auto", cmap="cividis", vmin=0.0, vmax=1.0)
    else:
        im = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_yticks(range(len(claims)))
    ax.set_yticklabels(claims)
    ax.set_xticks(range(len(deltas)))
    ax.set_xticklabels(deltas)
    ax.set_xlabel("Delta")
    ax.set_ylabel("Claim Pair")
    ax.set_title("Flip Rate Heatmap")
    for i in range(len(claims)):
        for j in range(len(deltas)):
            val = matrix[i, j]
            if np.isfinite(val):
                txt_color = "white" if val >= 0.55 else "#1f1f1f"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8.5, color=txt_color)
    cbar = fig.colorbar(im, ax=ax, label=metric.replace("_", " "))
    cbar.ax.tick_params(labelsize=9)
    return save_fig(fig, out_path)
