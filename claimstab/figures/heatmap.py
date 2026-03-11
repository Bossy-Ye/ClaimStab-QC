from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from claimstab.figures.adaptive import (
    classify_matrix_encoding,
    diagnose_matrix,
    plot_compact_table,
    plot_ordered_lollipop,
    plot_stat_card,
)
from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


def _delta_label(value: object) -> str:
    if value is None:
        return "n/a"
    token = str(value)
    if token.lower() in {"nan", "none", ""}:
        return "n/a"
    return token


def _delta_sort_key(token: str) -> tuple[int, float | str]:
    low = token.lower()
    if low in {"n/a", "nan", "none"}:
        return (1, token)
    try:
        return (0, float(token))
    except Exception:
        return (1, token)


def _resolve_row_key(df: pd.DataFrame) -> pd.Series:
    if {"claim_pair", "delta", "metric_name"}.issubset(set(df.columns)):
        grouped = df.groupby(["claim_pair", "delta"], dropna=False).size()
        dup_count = int(grouped.max()) if not grouped.empty else 1
        if dup_count > 1 and df["metric_name"].astype(str).nunique() > 1:
            return df["claim_pair"].astype(str) + " | " + df["metric_name"].astype(str)
    return df["claim_pair"].astype(str)


def plot_fliprate_heatmap(df: pd.DataFrame, out_path: str | Path, *, metric: str = "flip_rate_mean") -> dict[str, str] | None:
    if df.empty:
        return None
    if "claim_pair" not in df.columns or "delta" not in df.columns or metric not in df.columns:
        return None

    frame = df.copy()
    frame = frame.dropna(subset=["claim_pair"])
    if frame.empty:
        return None

    frame = frame.copy()
    frame["row_key"] = _resolve_row_key(frame)
    frame["col_key"] = frame["delta"].map(_delta_label)
    pivot = frame.pivot_table(index="row_key", columns="col_key", values=metric, aggfunc="mean")
    if pivot.empty:
        return None
    row_labels = [str(v) for v in pivot.index.tolist()]
    col_labels = sorted([str(v) for v in pivot.columns.tolist()], key=_delta_sort_key)
    pivot = pivot.reindex(columns=col_labels)
    matrix = pivot.to_numpy(dtype=float)

    diag = diagnose_matrix(matrix)
    encoding = classify_matrix_encoding(diag, near_constant_tol=0.01)

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    metric_label = metric.replace("_", " ")
    if encoding == "empty":
        return None
    if encoding == "single_value":
        value = f"{diag.value_min:.2f}"
        plot_stat_card(
            ax,
            title=f"{metric_label}: single-value summary",
            lines=[("value", value), ("rows x cols", f"{diag.rows} x {diag.cols}")],
            note="Only one informative cell; chart replaced by compact statistic panel.",
        )
        return save_fig(fig, out_path)
    if encoding in {"strip", "strip_constant"}:
        labels: list[str] = []
        values: list[float] = []
        for i, row_name in enumerate(row_labels):
            for j, col_name in enumerate(col_labels):
                value = matrix[i, j]
                if np.isfinite(value):
                    labels.append(f"{row_name} | Δ={col_name}")
                    values.append(float(value))
        plot_ordered_lollipop(
            ax,
            labels=labels,
            values=values,
            xlabel=metric_label,
            title=f"{metric_label}: ordered profile",
        )
        if encoding == "strip_constant":
            ax.text(
                0.01,
                0.01,
                "Near-constant values; lollipop view used instead of a low-contrast heatmap.",
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=8.1,
                color="#707070",
            )
        ax.set_ylabel("claim/delta cell")
        return save_fig(fig, out_path)
    if encoding == "constant_table":
        plot_compact_table(
            ax,
            row_labels=row_labels,
            col_labels=col_labels,
            matrix=matrix,
            title=f"{metric_label}: near-constant matrix",
            note="Heatmap suppressed because variation is too small to support color comparison.",
        )
        return save_fig(fig, out_path)

    finite = matrix[np.isfinite(matrix)]
    if finite.size == 0:
        return None
    if metric.startswith("flip_rate") or metric.startswith("stability"):
        if diag.value_range >= 0.2:
            vmin, vmax = 0.0, 1.0
        else:
            margin = max(0.02, diag.value_range * 0.35)
            vmin = max(0.0, diag.value_min - margin)
            vmax = min(1.0, diag.value_max + margin)
            if vmax - vmin < 0.05:
                center = (vmin + vmax) / 2.0
                vmin = max(0.0, center - 0.03)
                vmax = min(1.0, center + 0.03)
        im = ax.imshow(matrix, aspect="auto", cmap="cividis", vmin=vmin, vmax=vmax)
        contrast_cut = (vmin + vmax) / 2.0
    else:
        im = ax.imshow(matrix, aspect="auto", cmap="Greys")
        contrast_cut = float(np.nanmean(finite))
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels)
    ax.set_xlabel("delta")
    ax.set_ylabel("claim pair")
    ax.set_title("Flip-rate by claim and delta", loc="left")
    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            val = matrix[i, j]
            if np.isfinite(val):
                txt_color = "white" if val >= contrast_cut else "#1f1f1f"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8.2, color=txt_color)
    cbar = fig.colorbar(im, ax=ax, label=metric_label)
    cbar.ax.tick_params(labelsize=8.5)
    return save_fig(fig, out_path)


def plot_space_profile_composite(df: pd.DataFrame, out_path: str | Path, *, metric: str = "flip_rate_mean") -> dict[str, str] | None:
    required = {"space_preset", "claim_pair", "delta", metric}
    if df.empty or not required.issubset(set(df.columns)):
        return None

    frame = df.copy()
    frame["delta_label"] = frame["delta"].map(_delta_label)
    frame["cell_label"] = frame["claim_pair"].astype(str) + " | Δ=" + frame["delta_label"].astype(str)
    frame = frame.dropna(subset=[metric, "space_preset", "cell_label"])
    if frame.empty:
        return None

    pivot = frame.pivot_table(index="cell_label", columns="space_preset", values=metric, aggfunc="mean")
    if pivot.empty or len(pivot.columns) < 2:
        return None
    spaces = sorted([str(v) for v in pivot.columns.tolist()])
    labels = sorted([str(v) for v in pivot.index.tolist()])
    pivot = pivot.reindex(index=labels, columns=spaces)

    apply_style()
    fig, axes = plt.subplots(1, len(spaces), figsize=(max(FIG_W_WIDE, 2.7 * len(spaces)), FIG_H_WIDE), layout="constrained", sharey=True)
    if len(spaces) == 1:
        axes = [axes]

    global_max = float(np.nanmax(pivot.to_numpy(dtype=float))) if np.isfinite(pivot.to_numpy(dtype=float)).any() else 1.0
    for idx, space in enumerate(spaces):
        ax = axes[idx]
        vals = [float(v) if np.isfinite(v) else np.nan for v in pivot[space].tolist()]
        finite = [v for v in vals if np.isfinite(v)]
        if not finite:
            plot_stat_card(
                ax,
                title=f"{space}",
                lines=[("status", "no finite values")],
                note="No data for this space.",
            )
            continue
        plot_ordered_lollipop(
            ax,
            labels=labels,
            values=[float(v) if np.isfinite(v) else 0.0 for v in vals],
            xlabel=metric.replace("_", " "),
            title=f"{space}",
        )
        ax.set_xlim(0.0, max(0.05, global_max * 1.12))
        if idx > 0:
            ax.set_ylabel("")
    fig.suptitle("Merged space profile", x=0.5, y=1.01, fontsize=10.6)
    return save_fig(fig, out_path)
