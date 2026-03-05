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
    labels = ["naive_overclaim", "naive_underclaim", "agree", "naive_uninformative"]
    colors = ["#d73027", "#fc8d59", "#1a9850", "#999999"]

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), layout="constrained")
    if "policy" in df_compare.columns and df_compare["policy"].nunique() > 1:
        policies = [str(p) for p in sorted(df_compare["policy"].dropna().unique())]
        x = range(len(labels))
        width = 0.35
        max_v = 0
        for idx, policy in enumerate(policies):
            counts = df_compare[df_compare["policy"] == policy]["comparison"].value_counts().to_dict()
            values = [int(counts.get(label, 0)) for label in labels]
            max_v = max(max_v, max(values + [0]))
            shift = -width / 2.0 + idx * width
            bars = ax.bar(
                [v + shift for v in x],
                values,
                width=width,
                label=policy,
                color=colors,
                edgecolor="#2f2f2f",
                linewidth=0.55,
                alpha=0.85,
            )
            for bar, v in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bar.get_height() + max(max_v, 1) * 0.03,
                    str(v),
                    ha="center",
                    va="bottom",
                    fontsize=8.0,
                )
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=14)
        ax.legend(fontsize=8, frameon=False)
        values_for_ylim = [max_v]
    else:
        counts = df_compare["comparison"].value_counts().to_dict()
        values = [int(counts.get(label, 0)) for label in labels]
        bars = ax.bar(labels, values, color=colors, edgecolor="#2f2f2f", linewidth=0.55)
        ax.tick_params(axis="x", rotation=14)
        for bar, v in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + max(values + [1]) * 0.03,
                str(v),
                ha="center",
                va="bottom",
                fontsize=8.5,
            )
        values_for_ylim = values

    ax.set_ylabel("Count")
    ax.set_title("Naive Baseline vs ClaimStab")
    ax.set_ylim(0, max(values_for_ylim + [1]) * 1.25)
    return save_fig(fig, out_path)
