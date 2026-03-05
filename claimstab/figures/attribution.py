from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


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

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    bars = ax.barh(
        frame["dimension"].astype(str),
        frame[metric_col].astype(float),
        color="#4c78a8",
        edgecolor="#2f2f2f",
        linewidth=0.5,
    )
    ax.set_xlabel(metric_label)
    ax.set_ylabel("Dimension")
    ax.set_title("Top Perturbation Drivers")
    max_val = float(frame[metric_col].max()) if not frame.empty else 1.0
    if metric_col == "flip_rate":
        ax.set_xlim(0.0, max(0.1, min(1.0, max_val * 1.18)))
    else:
        ax.set_xlim(0.0, max(0.1, max_val * 1.18))
    for bar in bars:
        w = float(bar.get_width())
        ax.text(
            w + 0.01,
            bar.get_y() + bar.get_height() / 2.0,
            f"{w:.2f}",
            va="center",
            ha="left",
            fontsize=8.5,
            color="#2f2f2f",
        )
    return save_fig(fig, out_path)
