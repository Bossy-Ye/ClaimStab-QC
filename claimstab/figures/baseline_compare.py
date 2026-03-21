from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.adaptive import plot_compact_table, plot_ordered_lollipop, plot_stat_card
from claimstab.figures.style import FIG_H, FIG_W, PAPER_RED_DARK, apply_style, save_fig


def plot_naive_vs_claimstab(df_compare: pd.DataFrame, out_path: str | Path) -> dict[str, str] | None:
    if df_compare.empty:
        return None
    if "comparison" not in df_compare.columns:
        return None
    labels = ["naive_overclaim", "naive_underclaim", "agree", "naive_uninformative"]

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), layout="constrained")
    global_counts = df_compare["comparison"].value_counts().to_dict()
    nonzero_global = [label for label in labels if int(global_counts.get(label, 0)) > 0]
    if len(nonzero_global) <= 1:
        dominant = nonzero_global[0] if nonzero_global else "none"
        plot_stat_card(
            ax,
            title="Naive baseline vs ClaimStab",
            lines=[
                ("dominant outcome", dominant),
                ("count", str(int(global_counts.get(dominant, 0))) if dominant != "none" else "0"),
                ("total rows", str(int(len(df_compare)))),
            ],
            note="Grouped bars suppressed because only one comparison outcome appears.",
        )
        return save_fig(fig, out_path)

    if "policy" in df_compare.columns and df_compare["policy"].nunique() > 1:
        policies = [str(p) for p in sorted(df_compare["policy"].dropna().unique())]
        counts_by_policy: dict[str, list[int]] = {}
        for policy in policies:
            counts = df_compare[df_compare["policy"] == policy]["comparison"].value_counts().to_dict()
            counts_by_policy[policy] = [int(counts.get(label, 0)) for label in labels]
        matrix = []
        for policy in policies:
            matrix.append([float(v) for v in counts_by_policy[policy]])
        import numpy as np

        plot_compact_table(
            ax,
            row_labels=policies,
            col_labels=labels,
            matrix=np.array(matrix, dtype=float),
            title="Naive baseline vs ClaimStab",
            note="Compact table used to compare policy-specific counts without sparse grouped bars.",
        )
    else:
        counts = df_compare["comparison"].value_counts().to_dict()
        values = [int(counts.get(label, 0)) for label in labels]
        plot_ordered_lollipop(
            ax,
            labels=labels,
            values=values,
            xlabel="count",
            title="Naive baseline vs ClaimStab",
            color=PAPER_RED_DARK,
        )
        ax.set_ylabel("comparison")
    return save_fig(fig, out_path)
