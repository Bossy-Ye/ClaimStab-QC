from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from claimstab.figures.style import apply_style

# Paper-wide semantic decision colors (fixed contract).
DECISION_COLORS: dict[str, str] = {
    "stable": "#2ca02c",
    "unstable": "#d62728",
    "inconclusive": "#7f7f7f",
}

SPACE_ORDER = ["compilation_only", "combined_light", "sampling_only"]
TASK_ORDER = ["MaxCut", "GHZ", "BV", "Grover"]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _delta_token(value: Any) -> str:
    if value is None:
        return "n/a"
    token = str(value)
    if token.lower() in {"nan", "none", ""}:
        return "n/a"
    return token


def _delta_sort_key(value: Any) -> tuple[int, float | str]:
    token = _delta_token(value)
    if token == "n/a":
        return (1, token)
    try:
        return (0, float(token))
    except Exception:
        return (1, token)


def _apply_camera_ready_style() -> None:
    apply_style()
    plt.rcParams.update(
        {
            "font.size": 9.0,
            "axes.labelsize": 9.2,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 8.2,
            "grid.alpha": 0.2,
            "errorbar.capsize": 3.0,
        }
    )


def save_publication_figure(fig: Figure, out_base_path: str | Path) -> dict[str, str]:
    out_base = Path(out_base_path)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out_base.with_suffix(".pdf")
    svg_path = out_base.with_suffix(".svg")
    png_path = out_base.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.03)
    return {"pdf": str(pdf_path), "svg": str(svg_path), "png": str(png_path)}


def plot_stability_profile(df: pd.DataFrame, *, threshold: float = 0.95) -> Figure:
    required = {
        "claim_pair",
        "space_preset",
        "delta",
        "stability_hat",
        "stability_ci_low",
        "stability_ci_high",
        "decision",
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"plot_stability_profile missing columns: {missing}")

    frame = df.copy()
    frame["delta_label"] = frame["delta"].map(_delta_token)
    frame["claim_delta"] = frame["claim_pair"].astype(str) + " | delta=" + frame["delta_label"].astype(str)
    frame["sort_claim"] = frame["claim_pair"].astype(str)
    frame["sort_delta"] = frame["delta"].map(_delta_sort_key)
    frame = frame.sort_values(["sort_claim", "sort_delta", "space_preset"]).reset_index(drop=True)

    spaces = [space for space in SPACE_ORDER if space in set(frame["space_preset"].astype(str).tolist())]
    if not spaces:
        spaces = sorted(frame["space_preset"].astype(str).unique().tolist())
    n_panels = max(1, len(spaces))
    panel_height = max(3.0, min(8.8, 0.24 * max(1, int(frame["claim_delta"].nunique())) + 1.5))

    _apply_camera_ready_style()
    fig, axes = plt.subplots(
        1,
        n_panels,
        sharex=True,
        figsize=(3.9 * n_panels + 1.6, panel_height),
        constrained_layout=False,
    )
    if n_panels == 1:
        axes = [axes]
    fig.subplots_adjust(left=0.22, right=0.79, top=0.90, bottom=0.11, wspace=0.02)

    for idx, (ax, space) in enumerate(zip(axes, spaces)):
        sframe = frame[frame["space_preset"].astype(str) == space].copy()
        sframe = sframe.sort_values("stability_hat", ascending=False).reset_index(drop=True)
        labels = sframe["claim_delta"].astype(str).tolist()
        y_pos = np.arange(len(labels), dtype=float)
        ax.axvspan(0.0, float(threshold), color=DECISION_COLORS["unstable"], alpha=0.045, zorder=0)
        for y, (_, row) in zip(y_pos, sframe.iterrows()):
            low = _as_float(row.get("stability_ci_low"))
            high = _as_float(row.get("stability_ci_high"))
            hat = _as_float(row.get("stability_hat"))
            decision = str(row.get("decision", "inconclusive")).strip().lower()
            color = DECISION_COLORS.get(decision, DECISION_COLORS["inconclusive"])
            ax.hlines(y, low, high, color="#5e5e5e", linewidth=1.5, alpha=0.95, zorder=1)
            ax.plot(
                [hat],
                [y],
                marker="o",
                markersize=2.8,
                color=color,
                markeredgewidth=0.0,
                linestyle="None",
                zorder=3,
            )

        ax.axvline(float(threshold), color="#3f3f3f", linestyle=(0, (4, 2)), linewidth=2.0, alpha=0.95, zorder=2)
        ax.set_xlim(0.0, 1.0)
        ax.set_title(space.replace("_", " "), loc="left", fontsize=9.2)
        ax.grid(axis="x", alpha=0.2, linewidth=0.45)
        ax.grid(axis="y", alpha=0.0)
        ax.set_yticks(y_pos)
        if idx == 0:
            ax.set_yticklabels(labels, fontsize=8.0)
            ax.set_ylabel("claim comparison", fontsize=9.2)
        else:
            ax.set_yticklabels([])
    axes[0].invert_yaxis()
    for ax in axes:
        ax.set_xlabel("stability_hat", fontsize=9.2)

    # Minimal legend in first panel.
    handles = []
    for key in ("stable", "unstable", "inconclusive"):
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=DECISION_COLORS[key],
                markeredgewidth=0.0,
                markersize=5.0,
                label=key,
            )
        )
    fig.legend(
        handles=handles,
        frameon=False,
        loc="center left",
        bbox_to_anchor=(0.80, 0.50),
        ncol=1,
        fontsize=8.2,
        title="decision",
        title_fontsize=8.4,
    )
    return fig


def plot_space_flip_rate(df: pd.DataFrame) -> Figure:
    required = {"space_preset", "flip_rate_mean"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"plot_space_flip_rate missing columns: {missing}")

    frame = df.copy()
    frame["flip_rate_mean"] = frame["flip_rate_mean"].map(_as_float)
    grouped = (
        frame.groupby("space_preset", as_index=False)
        .agg(
            mean=("flip_rate_mean", "mean"),
            std=("flip_rate_mean", "std"),
            count=("flip_rate_mean", "count"),
        )
        .reset_index(drop=True)
    )
    grouped["se"] = grouped.apply(lambda r: (_as_float(r["std"]) / max(1.0, np.sqrt(_as_float(r["count"])))), axis=1)
    grouped["ci95"] = grouped["se"] * 1.96
    grouped["ci95"] = grouped["ci95"].fillna(0.0)
    grouped["order"] = grouped["space_preset"].map({k: i for i, k in enumerate(SPACE_ORDER)}).fillna(99).astype(int)
    grouped = grouped.sort_values(["order", "space_preset"]).reset_index(drop=True)

    _apply_camera_ready_style()
    fig, ax = plt.subplots(figsize=(6.4, 2.8), layout="constrained")
    y = np.arange(len(grouped), dtype=float)
    means = grouped["mean"].astype(float).to_numpy()
    errs = grouped["ci95"].astype(float).to_numpy()
    labels = grouped["space_preset"].astype(str).tolist()

    ax.errorbar(
        means,
        y,
        xerr=errs,
        fmt="o",
        markersize=3.6,
        color="#3e3e3e",
        ecolor="#595959",
        elinewidth=0.8,
        capsize=3.0,
        capthick=0.8,
        linestyle="None",
        zorder=2,
    )
    for yi, mean in zip(y, means):
        ax.text(float(mean) + 0.008, yi, f"{mean:.3f}", va="center", ha="left", fontsize=8.4, color="#2f2f2f")

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_ylabel("perturbation space", fontsize=9.2)
    ax.set_xlabel("mean flip rate (95% CI)", fontsize=9.2)
    x_hi = max(0.02, float(np.nanmax(means + errs) * 1.22))
    ax.set_xlim(0.0, x_hi)
    ax.grid(axis="x", alpha=0.2, linewidth=0.45)
    ax.grid(axis="y", alpha=0.0)
    ax.invert_yaxis()
    return fig


def plot_claim_distribution(df: pd.DataFrame) -> Figure:
    task_col = "task" if "task" in df.columns else ("experiment_group" if "experiment_group" in df.columns else None)
    if task_col is None or "decision" not in df.columns:
        raise ValueError("plot_claim_distribution requires columns: task/experiment_group and decision")

    frame = df.copy()
    frame["task"] = frame[task_col].astype(str)
    frame["decision"] = frame["decision"].astype(str).str.lower()
    pivot = (
        frame.groupby(["task", "decision"], as_index=False)
        .size()
        .pivot(index="task", columns="decision", values="size")
        .fillna(0)
    )
    for key in ("stable", "unstable", "inconclusive"):
        if key not in pivot.columns:
            pivot[key] = 0
    pivot = pivot[["stable", "inconclusive", "unstable"]]
    ordered = [task for task in TASK_ORDER if task in pivot.index]
    for task in pivot.index:
        if task not in ordered:
            ordered.append(task)
    pivot = pivot.reindex(ordered)

    # Normalize to proportions per task to avoid sample-size distortion.
    denom = pivot.sum(axis=1).replace(0, 1.0)
    prop = pivot.div(denom, axis=0) * 100.0

    _apply_camera_ready_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.4), layout="constrained")
    x = np.arange(len(prop.index), dtype=float)
    width = 0.22
    decisions = ["stable", "inconclusive", "unstable"]
    offsets = {"stable": -width, "inconclusive": 0.0, "unstable": width}
    for decision in decisions:
        vals = prop[decision].astype(float).to_numpy()
        ax.bar(
            x + offsets[decision],
            vals,
            width=width,
            color=DECISION_COLORS[decision],
            edgecolor="none",
            label=decision,
        )
        for task_name, xi, yi in zip(prop.index.tolist(), x + offsets[decision], vals):
            if yi <= 0:
                continue
            if str(task_name) in {"BV", "Grover"} and yi >= 95.0:
                ax.text(xi, yi + 1.8, f"{int(round(yi))}%", ha="center", va="bottom", fontsize=8.0, color="#2f2f2f")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index.tolist())
    ax.set_xlabel("task / experiment group", fontsize=9.2)
    ax.set_ylabel("percentage (%)", fontsize=9.2)
    ax.set_ylim(0.0, 100.0)
    ax.grid(axis="y", alpha=0.2, linewidth=0.45)
    ax.grid(axis="x", alpha=0.0)
    ax.legend(frameon=False, fontsize=8.0, loc="center left", bbox_to_anchor=(1.01, 0.5))
    return fig


def plot_cost_confidence_tradeoff(df: pd.DataFrame) -> Figure:
    required = {"strategy", "cost", "ci_width"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"plot_cost_confidence_tradeoff missing columns: {missing}")

    frame = df.copy()
    frame["strategy"] = frame["strategy"].astype(str)
    frame["cost"] = frame["cost"].map(_as_float)
    frame["ci_width"] = frame["ci_width"].map(_as_float)
    frame = frame.sort_values(["cost", "strategy"]).reset_index(drop=True)

    _apply_camera_ready_style()
    fig, ax = plt.subplots(figsize=(6.6, 3.4), layout="constrained")
    x = frame["cost"].to_numpy(dtype=float)
    y = frame["ci_width"].to_numpy(dtype=float)
    labels = frame["strategy"].tolist()
    marker_map = {
        "full_factorial": "s",
        "random_k_32": "o",
        "random_k_64": "^",
        "adaptive_ci": "D",
        "adaptive_ci_tuned": "P",
    }
    tab10 = plt.get_cmap("tab10").colors
    color_map = {
        "full_factorial": tab10[0],
        "random_k_32": tab10[1],
        "random_k_64": tab10[2],
        "adaptive_ci": tab10[3],
        "adaptive_ci_tuned": tab10[4],
    }
    draw_order = {"full_factorial": 0, "random_k_32": 1, "random_k_64": 2, "adaptive_ci": 3, "adaptive_ci_tuned": 4}
    points = sorted(zip(x, y, labels), key=lambda item: draw_order.get(item[2], 99))
    plotted_labels: set[str] = set()
    for xi, yi, label in points:
        ax.plot(
            [xi],
            [yi],
            marker=marker_map.get(label, "o"),
            markersize=4.6,
            color=color_map.get(label, "#404040"),
            linestyle="None",
            zorder=3,
            label=label if label not in plotted_labels else None,
        )
        plotted_labels.add(label)

    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, title="strategy", title_fontsize=8.4, fontsize=8.1)

    ax.set_xlabel("evaluation cost", fontsize=9.2)
    ax.set_ylabel("CI width", fontsize=9.2)
    ax.set_xlim(0.0, float(max(x) * 1.08) if len(x) else 1.0)
    ax.grid(axis="both", alpha=0.2, linewidth=0.45)
    return fig
