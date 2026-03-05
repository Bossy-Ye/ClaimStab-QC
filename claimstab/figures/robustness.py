from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


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

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    x = list(range(len(ordered_deltas)))
    ax.bar(x, stable, color="#2a9d8f", label="stable", edgecolor="#2f2f2f", linewidth=0.45)
    ax.bar(
        x,
        inconclusive,
        bottom=stable,
        color="#e9c46a",
        label="inconclusive",
        edgecolor="#2f2f2f",
        linewidth=0.45,
    )
    stacked_bottom = [s + i for s, i in zip(stable, inconclusive)]
    ax.bar(
        x,
        unstable,
        bottom=stacked_bottom,
        color="#e76f51",
        label="unstable",
        edgecolor="#2f2f2f",
        linewidth=0.45,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(ordered_deltas)
    ax.set_xlabel("delta")
    ax.set_ylabel("number of condition cells")
    ax.set_title("Robustness Map (RQ5): Cell Decisions by Delta")
    ax.legend(loc="upper right")
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

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    colors = ["#2a9d8f", "#e9c46a", "#e76f51"]
    bars = ax.bar(labels, values, color=colors, edgecolor="#2f2f2f", linewidth=0.55)
    ax.set_ylabel("Count")
    ax.set_title("Stratified Stability Decisions (RQ6)")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.1,
            str(value),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#2f2f2f",
        )
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

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    bars = ax.barh(labels, values, color="#4c78a8", edgecolor="#2f2f2f", linewidth=0.55)
    ax.set_xlabel("effect score (joint spread by dimension)")
    ax.set_ylabel("Dimension")
    ax.set_title("Top Main Effects (RQ7)")
    max_val = max(values) if values else 0.0
    ax.set_xlim(0.0, max(0.1, max_val * 1.18))
    for bar, value in zip(bars, values):
        ax.text(
            value + 0.01,
            bar.get_y() + bar.get_height() / 2.0,
            f"{value:.2f}",
            va="center",
            ha="left",
            fontsize=8.5,
            color="#2f2f2f",
        )
    return save_fig(fig, out_path)
