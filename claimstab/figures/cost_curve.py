from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.adaptive import plot_stat_card
from claimstab.figures.style import (
    FIG_H,
    FIG_W,
    PAPER_GRAY_MEDIUM,
    apply_style,
    plot_line_with_ci,
    save_fig,
)


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
    if len(xs) <= 1 or len(set(xs)) <= 1:
        single_shot = int(xs[0]) if xs else 0
        decision = ""
        if "decision" in frame.columns:
            decision = str(frame.iloc[0].get("decision", "")) if not frame.empty else ""
        plot_stat_card(
            ax,
            title="Stability vs shots (single cost level)",
            lines=[
                ("shots", str(single_shot)),
                ("stability_hat", f"{float(y_hat[0]):.3f}" if y_hat else "NA"),
                ("CI", f"[{float(y_low[0]):.3f}, {float(y_hi[0]):.3f}]" if y_low and y_hi else "NA"),
                ("decision", decision or "n/a"),
            ],
            note="Curve suppressed because only one shot level is available for this run.",
        )
        return save_fig(fig, out_path)

    plot_line_with_ci(
        ax,
        x=xs,
        y=y_hat,
        ci_low=y_low,
        ci_high=y_hi,
        label="stability estimate",
        ci_label="95% CI",
    )
    ax.axhline(
        float(threshold),
        linestyle=(0, (5, 3)),
        color=PAPER_GRAY_MEDIUM,
        linewidth=1.1,
        label="stability threshold",
    )
    ax.set_xlabel("Shots")
    ax.set_ylabel("Stability (CI)")
    ax.set_title("Stability vs shots", loc="left")
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
    ax.legend(loc="lower right")
    return save_fig(fig, out_path)
