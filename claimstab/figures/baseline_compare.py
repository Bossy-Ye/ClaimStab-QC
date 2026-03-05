from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import FIG_H, FIG_W, apply_style, save_fig


def plot_naive_vs_claimstab(df_compare: pd.DataFrame, out_path: str | Path) -> dict[str, str] | None:
    if df_compare.empty:
        return None
    if "comparison" not in df_compare.columns:
        return None
    counts = df_compare["comparison"].value_counts().to_dict()
    labels = ["naive_overclaim", "naive_underclaim", "agree", "naive_uninformative"]
    values = [int(counts.get(label, 0)) for label in labels]
    colors = ["#d73027", "#fc8d59", "#1a9850", "#999999"]

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), layout="constrained")
    bars = ax.bar(labels, values, color=colors, edgecolor="#2f2f2f", linewidth=0.55)
    ax.set_ylabel("Count")
    ax.set_title("Naive Baseline vs ClaimStab")
    ax.tick_params(axis="x", rotation=14)
    ax.set_ylim(0, max(values + [1]) * 1.2)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + max(values + [1]) * 0.03,
            str(v),
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    return save_fig(fig, out_path)
