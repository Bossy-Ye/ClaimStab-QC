from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import FIG_H, FIG_W, apply_style, save_fig


def plot_stability_vs_shots(df_shots: pd.DataFrame, out_path: str | Path, threshold: float = 0.95) -> dict[str, str] | None:
    if df_shots.empty:
        return None
    required = {"shots", "stability_ci_low"}
    if not required.issubset(set(df_shots.columns)):
        return None

    frame = df_shots.copy()
    frame["shots"] = frame["shots"].astype(int)
    frame = frame.sort_values("shots")
    xs = frame["shots"].tolist()
    y_low = frame["stability_ci_low"].astype(float).tolist()
    y_hat = frame["stability_hat"].astype(float).tolist() if "stability_hat" in frame.columns else y_low
    y_hi = frame["stability_ci_high"].astype(float).tolist() if "stability_ci_high" in frame.columns else y_low

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.plot(xs, y_low, marker="o", label="CI lower bound")
    ax.plot(xs, y_hat, marker="o", alpha=0.5, linestyle="--", label="stability_hat")
    yerr_low = [max(0.0, h - l) for h, l in zip(y_hat, y_low)]
    yerr_high = [max(0.0, u - h) for h, u in zip(y_hat, y_hi)]
    ax.errorbar(xs, y_hat, yerr=[yerr_low, yerr_high], fmt="none", capsize=3)
    ax.axhline(float(threshold), linestyle="--", label="stability threshold")
    ax.set_xlabel("shots")
    ax.set_ylabel("stability (CI)")
    ax.set_title("Stability vs Cost (Shots)")
    if len(xs) == 1:
        ax.text(
            xs[0],
            min(0.99, y_low[0] + 0.03),
            "single-point only",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.legend()
    return save_fig(fig, out_path)
