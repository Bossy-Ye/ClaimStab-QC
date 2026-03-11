from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.adaptive import plot_stat_card
from claimstab.figures.style import FIG_H, FIG_W, PAPER_GRAY_MEDIUM, apply_style, add_reference_lines, save_fig


def plot_ci_width_vs_budget(df_adaptive: pd.DataFrame, out_path: str | Path) -> dict[str, str] | None:
    if df_adaptive.empty:
        return None
    required = {"selected_configurations_with_baseline", "achieved_ci_width"}
    if not required.issubset(set(df_adaptive.columns)):
        return None

    frame = df_adaptive.copy()
    frame = frame.dropna(subset=["selected_configurations_with_baseline", "achieved_ci_width"])
    if frame.empty:
        return None
    frame = frame.sort_values("selected_configurations_with_baseline")

    x = frame["selected_configurations_with_baseline"].astype(float).tolist()
    y = frame["achieved_ci_width"].astype(float).tolist()
    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), layout="constrained")
    if len(x) <= 1:
        target = None
        if "target_ci_width" in frame.columns:
            non_null_targets = frame["target_ci_width"].dropna()
            if not non_null_targets.empty:
                target = float(non_null_targets.iloc[0])
        plot_stat_card(
            ax,
            title="Adaptive CI width summary",
            lines=[
                ("n_eval", str(int(x[0])) if x else "0"),
                ("achieved width", f"{float(y[0]):.3f}" if y else "NA"),
                ("target width", f"{target:.3f}" if target is not None else "n/a"),
            ],
            note="Trend plot suppressed because only one adaptive sample is available.",
        )
        return save_fig(fig, out_path)

    ax.plot(x, y, marker="o", color="#6f1d1b", linewidth=2.0, label="achieved CI width")
    if "target_ci_width" in frame.columns:
        non_null_targets = frame["target_ci_width"].dropna()
        if not non_null_targets.empty:
            target = float(non_null_targets.iloc[0])
            ax.axhline(
                target,
                color=PAPER_GRAY_MEDIUM,
                linestyle=(0, (5, 3)),
                linewidth=1.1,
                label="target CI width",
            )
    add_reference_lines(ax, event_x=0.0, zero_y=0.0)
    ax.set_xlabel("n_eval (selected configurations)")
    ax.set_ylabel("CI width")
    ax.set_title("Adaptive CI width vs budget", loc="left")
    if x and y:
        ax.scatter([x[-1]], [y[-1]], marker="o", color="#6f1d1b", s=30, zorder=5)
        ax.annotate(
            f"stop @ n={int(x[-1])}, w={y[-1]:.3f}",
            xy=(x[-1], y[-1]),
            xytext=(6, 8),
            textcoords="offset points",
            fontsize=8.5,
            color="#303030",
        )
    ax.legend(loc="upper right")
    return save_fig(fig, out_path)
