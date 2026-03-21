from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.adaptive import plot_ordered_lollipop, plot_stat_card
from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, PAPER_GRAY_DARK, PAPER_RED_MEDIUM, apply_style, save_fig


def _select_attribution_metric(frame: pd.DataFrame) -> tuple[str | None, str]:
    if "driver_score" in frame.columns:
        return "driver_score", "Driver Score (std of flip rate across knob values)"
    if "flip_rate" in frame.columns:
        return "flip_rate", "Flip Contribution (Rate)"
    if {"flips", "total"}.issubset(set(frame.columns)):
        frame["flip_rate"] = frame["flips"] / frame["total"].replace(0, 1)
        return "flip_rate", "Flip Contribution (Rate)"
    return None, ""


def plot_top_attribution_bars(attrib_df: pd.DataFrame, out_path: str | Path, top_k: int = 10) -> dict[str, str] | None:
    if attrib_df.empty:
        return None
    if "dimension" not in attrib_df.columns:
        return None
    frame = attrib_df.copy()
    metric_col, metric_label = _select_attribution_metric(frame)
    if metric_col is None:
        return None
    frame = frame.sort_values(metric_col, ascending=False).head(max(1, int(top_k)))
    frame = frame.iloc[::-1]
    values = frame[metric_col].astype(float).tolist()
    labels = frame["dimension"].astype(str).tolist()
    value_min = min(values) if values else 0.0
    value_max = max(values) if values else 0.0
    value_range = value_max - value_min

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    if len(values) <= 1 or value_range < 1e-6:
        plot_stat_card(
            ax,
            title="Perturbation driver summary",
            lines=[
                ("metric", metric_label),
                ("dimensions", str(len(values))),
                ("observed range", f"{value_min:.4f} .. {value_max:.4f}"),
            ],
            note="Top-driver bar chart suppressed because all dimensions have indistinguishable scores.",
        )
        return save_fig(fig, out_path)

    plot_ordered_lollipop(
        ax,
        labels=labels,
        values=values,
        xlabel=metric_label,
        title="Top perturbation drivers",
        color=PAPER_RED_MEDIUM,
    )
    ax.set_ylabel("dimension")
    return save_fig(fig, out_path)
