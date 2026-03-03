from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


def plot_top_attribution_bars(attrib_df: pd.DataFrame, out_path: str | Path, top_k: int = 10) -> dict[str, str] | None:
    if attrib_df.empty:
        return None
    if "dimension" not in attrib_df.columns:
        return None
    frame = attrib_df.copy()
    if "flip_rate" not in frame.columns and {"flips", "total"}.issubset(set(frame.columns)):
        frame["flip_rate"] = frame["flips"] / frame["total"].replace(0, 1)
    if "flip_rate" not in frame.columns:
        return None
    frame = frame.sort_values("flip_rate", ascending=False).head(max(1, int(top_k)))

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE))
    ax.barh(frame["dimension"].astype(str), frame["flip_rate"].astype(float))
    ax.invert_yaxis()
    ax.set_xlabel("flip contribution (rate)")
    ax.set_ylabel("dimension")
    ax.set_title("Top Perturbation Drivers")
    return save_fig(fig, out_path)
