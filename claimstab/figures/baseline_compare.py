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

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.bar(labels, values)
    ax.set_ylabel("count")
    ax.set_title("Naive Baseline vs ClaimStab")
    ax.tick_params(axis="x", rotation=20)
    return save_fig(fig, out_path)
