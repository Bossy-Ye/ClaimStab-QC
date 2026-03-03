from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import FIG_H, FIG_W, apply_style, save_fig


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

    x = frame["selected_configurations_with_baseline"].astype(float).tolist()
    y = frame["achieved_ci_width"].astype(float).tolist()
    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.plot(x, y, marker="o")
    ax.set_xlabel("n_eval (selected configurations)")
    ax.set_ylabel("CI width")
    ax.set_title("CI Width Shrink (Adaptive Sampling)")
    return save_fig(fig, out_path)
