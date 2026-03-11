from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from claimstab.figures.adaptive import plot_compact_table, plot_ordered_lollipop, plot_stat_card
from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, PAPER_GRAY_DARK, PAPER_GRAY_LIGHT, PAPER_GRAY_MEDIUM, PAPER_RED_MEDIUM, apply_style, decision_color, save_fig


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
        }
    )


def plot_rq5_robustness_map(payload: dict[str, Any], out_path: str | Path) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    experiments = payload.get("experiments", [])
    if not isinstance(experiments, list):
        return None

    decision_counts_by_delta: dict[str, dict[str, int]] = {}
    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        overall = exp.get("overall", {})
        if not isinstance(overall, dict):
            continue
        robustness = overall.get("conditional_robustness", {})
        if not isinstance(robustness, dict):
            continue
        cells_by_delta = robustness.get("cells_by_delta", {})
        if not isinstance(cells_by_delta, dict):
            continue
        for delta, cells in cells_by_delta.items():
            if not isinstance(cells, list):
                continue
            dkey = str(delta)
            slot = decision_counts_by_delta.setdefault(dkey, {"stable": 0, "inconclusive": 0, "unstable": 0})
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                decision = str(cell.get("decision", "inconclusive"))
                if decision not in slot:
                    decision = "inconclusive"
                slot[decision] += 1

    if not decision_counts_by_delta:
        return None

    ordered_deltas = sorted(
        decision_counts_by_delta.keys(),
        key=lambda token: float(token),
    )
    stable = [decision_counts_by_delta[d]["stable"] for d in ordered_deltas]
    inconclusive = [decision_counts_by_delta[d]["inconclusive"] for d in ordered_deltas]
    unstable = [decision_counts_by_delta[d]["unstable"] for d in ordered_deltas]
    if sum(stable) + sum(inconclusive) + sum(unstable) <= 0:
        return None

    _apply_camera_ready_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    if (
        len(ordered_deltas) <= 1
        or (
            max(stable) - min(stable) == 0
            and max(inconclusive) - min(inconclusive) == 0
            and max(unstable) - min(unstable) == 0
        )
    ):
        matrix = []
        for idx in range(len(ordered_deltas)):
            matrix.append([float(stable[idx]), float(inconclusive[idx]), float(unstable[idx])])
        import numpy as np

        plot_compact_table(
            ax,
            row_labels=ordered_deltas,
            col_labels=["stable", "inconclusive", "unstable"],
            matrix=np.array(matrix, dtype=float),
            title="",
            note="Stacked bars suppressed because decision counts are near-constant across deltas.",
        )
        return save_fig(fig, out_path)

    x = list(range(len(ordered_deltas)))
    ax.bar(x, stable, color=decision_color("stable"), label="stable", edgecolor=PAPER_GRAY_DARK, linewidth=0.45)
    ax.bar(
        x,
        inconclusive,
        bottom=stable,
        color=decision_color("inconclusive"),
        label="inconclusive",
        edgecolor=PAPER_GRAY_DARK,
        linewidth=0.45,
    )
    stacked_bottom = [s + i for s, i in zip(stable, inconclusive)]
    ax.bar(
        x,
        unstable,
        bottom=stacked_bottom,
        color=decision_color("unstable"),
        label="unstable",
        edgecolor=PAPER_GRAY_DARK,
        linewidth=0.45,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(ordered_deltas)
    ax.set_xlabel("delta")
    ax.set_ylabel("number of condition cells")
    totals = [max(1, s + i + u) for s, i, u in zip(stable, inconclusive, unstable)]
    for idx, (s, i, u, tot) in enumerate(zip(stable, inconclusive, unstable, totals)):
        dominant = max([("stable", s), ("inconclusive", i), ("unstable", u)], key=lambda item: item[1])
        pct = int(round((float(dominant[1]) / float(tot)) * 100.0))
        if pct >= 60:
            ax.text(idx, s + i + u + max(0.2, (s + i + u) * 0.015), f"{pct}%", ha="center", va="bottom", fontsize=7.8, color="#303030")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.10), ncol=3, frameon=False, fontsize=8.0)
    ax.grid(axis="y", alpha=0.2, linewidth=0.45)
    ax.grid(axis="x", alpha=0.0)
    return save_fig(fig, out_path)


def plot_rq6_decision_counts(rq6: dict[str, Any], out_path: str | Path) -> dict[str, str] | None:
    if not isinstance(rq6, dict):
        return None
    counts = rq6.get("decision_counts", {})
    if not isinstance(counts, dict):
        return None
    labels = ["stable", "inconclusive", "unstable"]
    values = [int(counts.get(label, 0)) for label in labels]
    if sum(values) <= 0:
        return None

    _apply_camera_ready_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    nonzero = sum(1 for v in values if v > 0)
    if nonzero <= 1:
        dominant_idx = max(range(len(values)), key=lambda i: values[i])
        plot_stat_card(
            ax,
            title="",
            lines=[
                ("stable", str(values[0])),
                ("inconclusive", str(values[1])),
                ("unstable", str(values[2])),
                ("dominant", labels[dominant_idx]),
            ],
            note="Bar chart suppressed because only one decision category is informative.",
        )
        return save_fig(fig, out_path)
    plot_ordered_lollipop(
        ax,
        labels=labels,
        values=values,
        xlabel="count",
        title="",
        color=PAPER_RED_MEDIUM,
    )
    ax.set_ylabel("decision")
    return save_fig(fig, out_path)


def plot_rq7_top_main_effects(
    rq7: dict[str, Any],
    out_path: str | Path,
    *,
    top_k: int = 8,
) -> dict[str, str] | None:
    if not isinstance(rq7, dict):
        return None
    rows = rq7.get("top_main_effects", [])
    if not isinstance(rows, list) or not rows:
        return None

    seen: set[str] = set()
    selected: list[tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        dim = str(row.get("dimension", "")).strip()
        if not dim or dim in seen:
            continue
        seen.add(dim)
        score = float(row.get("effect_score", 0.0))
        selected.append((dim, score))
        if len(selected) >= max(1, int(top_k)):
            break
    if not selected:
        return None

    selected.sort(key=lambda item: item[1], reverse=False)
    labels = [item[0] for item in selected]
    values = [item[1] for item in selected]

    _apply_camera_ready_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    min_v = min(values) if values else 0.0
    max_v = max(values) if values else 0.0
    if max_v - min_v < 1e-6:
        plot_stat_card(
            ax,
            title="",
            lines=[
                ("dimensions", str(len(values))),
                ("effect score", f"{min_v:.3f}"),
            ],
            note="Ranking chart suppressed because all effect scores are identical.",
        )
        return save_fig(fig, out_path)
    plot_ordered_lollipop(
        ax,
        labels=labels,
        values=values,
        xlabel="effect score (joint spread by dimension)",
        title="",
        color=PAPER_RED_MEDIUM,
    )
    ax.set_ylabel("dimension")
    return save_fig(fig, out_path)
