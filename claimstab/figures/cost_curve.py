from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import FIG_H, FIG_W, apply_style, save_fig


def _majority_label(values: pd.Series) -> str:
    counts = values.astype(str).value_counts()
    return str(counts.index[0]) if not counts.empty else ""


def plot_stability_vs_shots(df_shots: pd.DataFrame, out_path: str | Path, threshold: float = 0.95) -> dict[str, str] | None:
    if df_shots.empty:
        return None
    required = {"shots", "stability_ci_low"}
    if not required.issubset(set(df_shots.columns)):
        return None

    frame = df_shots.copy()
    frame["shots"] = frame["shots"].astype(int)
    agg = {
        "stability_ci_low": "mean",
    }
    if "stability_hat" in frame.columns:
        agg["stability_hat"] = "mean"
    if "stability_ci_high" in frame.columns:
        agg["stability_ci_high"] = "mean"
    if "n_eval" in frame.columns:
        agg["n_eval"] = "median"
    if "decision" in frame.columns:
        agg["decision"] = _majority_label
    frame = frame.groupby("shots", as_index=False).agg(agg).sort_values("shots")
    xs = frame["shots"].tolist()
    y_low = frame["stability_ci_low"].astype(float).tolist()
    y_hat = frame["stability_hat"].astype(float).tolist() if "stability_hat" in frame.columns else y_low
    y_hi = frame["stability_ci_high"].astype(float).tolist() if "stability_ci_high" in frame.columns else y_low

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), layout="constrained")
    ax.fill_between(xs, y_low, y_hi, color="#98c1d9", alpha=0.25, linewidth=0.0, label="CI band")
    ax.plot(xs, y_low, marker="o", color="#1d3557", linewidth=2.2, label="CI lower bound")
    ax.plot(xs, y_hat, marker="o", color="#457b9d", alpha=0.85, linestyle=(0, (3, 2)), label="stability_hat")
    yerr_low = [max(0.0, h - l) for h, l in zip(y_hat, y_low)]
    yerr_high = [max(0.0, u - h) for h, u in zip(y_hat, y_hi)]
    ax.errorbar(xs, y_hat, yerr=[yerr_low, yerr_high], fmt="none", ecolor="#457b9d", elinewidth=1.0, alpha=0.8)
    ax.axhline(float(threshold), linestyle=(0, (5, 3)), color="#7a7a7a", linewidth=1.2, label="stability threshold")
    ax.set_xlabel("Shots")
    ax.set_ylabel("Stability (CI)")
    ax.set_title("Stability vs Cost (Shots)")
    ax.set_xscale("log", base=2)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])
    y_min = min(y_low) if y_low else 0.0
    y_max = max(y_hi) if y_hi else 1.0
    pad = 0.04 if y_max - y_min < 0.2 else 0.03
    ax.set_ylim(max(0.0, y_min - pad), min(1.0, y_max + pad))
    for i, (x, low) in enumerate(zip(xs, y_low)):
        label = ""
        if "decision" in frame.columns:
            label = str(frame.iloc[i].get("decision", ""))
        if "n_eval" in frame.columns:
            n_eval = frame.iloc[i].get("n_eval")
            if n_eval is not None:
                n_eval_text = str(int(float(n_eval)))
                label = f"{label}, n={n_eval_text}" if label else f"n={n_eval_text}"
        if label:
            ax.annotate(
                label,
                xy=(x, low),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#303030",
            )
    if len(xs) == 1:
        ax.text(
            xs[0],
            min(0.99, y_low[0] + 0.03),
            "single-point only",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    ax.legend(loc="lower right")
    return save_fig(fig, out_path)
