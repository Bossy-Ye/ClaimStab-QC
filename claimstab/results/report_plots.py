from __future__ import annotations

from pathlib import Path
from typing import Any

from claimstab.results.report_helpers import numeric_sort_key, report_plot_rc


def plot_delta_curve(delta_rows: list[dict[str, Any]], out_path: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    ordered = sorted(delta_rows, key=lambda r: float(r.get("delta", 0.0)))
    xs = [float(r["delta"]) for r in ordered]
    ys = [float(r["flip_rate_mean"]) for r in ordered]
    ymin = [float(r.get("flip_rate_min", y)) for r, y in zip(ordered, ys)]
    ymax = [float(r.get("flip_rate_max", y)) for r, y in zip(ordered, ys)]

    with plt.rc_context(report_plot_rc()):
        fig, ax = plt.subplots(figsize=(7.1, 4.25))
        ax.plot(xs, ys, marker="o", markersize=6.8, color="#2f5f89", linewidth=2.2, label="mean flip rate")
        band = ax.fill_between(xs, ymin, ymax, color="#7aa6c2", alpha=0.24)
        band.set_hatch("////")
        band.set_edgecolor("#4e718f")
        band.set_linewidth(0.0)
        ax.set_xlabel("delta", fontweight="semibold")
        ax.set_ylabel("mean flip rate", fontweight="semibold")
        ax.set_title("Delta Sweep: Ranking Flip Rate")
        y_min_data = float(np.nanmin(ymin))
        y_max_data = float(np.nanmax(ymax))
        y_span = y_max_data - y_min_data
        if y_span < 1e-6:
            pad = 0.03
        else:
            pad = max(0.02, 0.18 * y_span)
        lo = max(0.0, y_min_data - pad)
        hi = min(1.0, y_max_data + pad)
        if hi - lo < 0.08:
            hi = min(1.0, lo + 0.08)
        ax.set_ylim(lo, hi)
        if len(xs) == 1:
            ax.set_xlim(xs[0] - 0.02, xs[0] + 0.02)
        else:
            xspan = max(xs) - min(xs)
            xpad = max(0.002, 0.06 * xspan)
            ax.set_xlim(min(xs) - xpad, max(xs) + xpad)
        ax.legend(loc="upper left")

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320, bbox_inches="tight")
        plt.close(fig)


def plot_shots_curve(shots_rows: list[dict[str, Any]], out_path: Path, *, threshold: float = 0.95) -> bool:
    if not shots_rows:
        return False
    import matplotlib.pyplot as plt
    import numpy as np

    bucket: dict[int, list[dict[str, Any]]] = {}
    for row in shots_rows:
        shot = int(row.get("shots", 0))
        bucket.setdefault(shot, []).append(row)

    ordered: list[dict[str, Any]] = []
    decision_order = {"stable": 3, "inconclusive": 2, "unstable": 1}
    for shot in sorted(bucket.keys()):
        rows = bucket[shot]
        n = len(rows)
        mean_hat = sum(float(r.get("stability_hat", 0.0)) for r in rows) / n
        mean_low = sum(float(r.get("stability_ci_low", 0.0)) for r in rows) / n
        mean_high = sum(float(r.get("stability_ci_high", 0.0)) for r in rows) / n
        mean_eval = int(round(sum(float(r.get("n_eval", 0.0)) for r in rows) / n))
        labels = [str(r.get("decision", "inconclusive")) for r in rows]
        labels.sort(key=lambda x: decision_order.get(x, 0), reverse=True)
        ordered.append(
            {
                "shots": shot,
                "stability_hat": mean_hat,
                "stability_ci_low": mean_low,
                "stability_ci_high": mean_high,
                "n_eval": mean_eval,
                "decision": labels[0] if labels else "inconclusive",
            }
        )

    xs = [int(r["shots"]) for r in ordered]
    ys = [float(r["stability_hat"]) for r in ordered]
    lows = [float(r["stability_ci_low"]) for r in ordered]
    highs = [float(r["stability_ci_high"]) for r in ordered]
    decisions = [str(r.get("decision", "inconclusive")) for r in ordered]
    eval_counts = [int(r.get("n_eval", 0)) for r in ordered]

    with plt.rc_context(report_plot_rc()):
        fig, ax = plt.subplots(figsize=(7.1, 4.25))
        band = ax.fill_between(xs, lows, highs, color="#8ab6d6", alpha=0.24)
        band.set_hatch("\\\\\\\\")
        band.set_edgecolor("#4b7090")
        band.set_linewidth(0.0)
        ax.plot(
            xs,
            lows,
            color="#204d74",
            linewidth=2.35,
            linestyle="-",
            marker="o",
            markersize=6.8,
            markerfacecolor="#204d74",
            markeredgecolor="#2f2f2f",
            markeredgewidth=0.35,
            label="CI lower bound",
        )
        ax.plot(
            xs,
            ys,
            color="#5f84a6",
            linewidth=1.4,
            linestyle=(0, (2, 2)),
            marker="o",
            markersize=4.6,
            markerfacecolor="#5f84a6",
            markeredgecolor="#415869",
            markeredgewidth=0.3,
            alpha=0.75,
            label="stability_hat",
        )
        yerr_low = [max(0.0, y - lo) for y, lo in zip(ys, lows)]
        yerr_high = [max(0.0, hi - y) for y, hi in zip(ys, highs)]
        ax.errorbar(xs, ys, yerr=[yerr_low, yerr_high], fmt="none", ecolor="#6688a3", elinewidth=1.0, alpha=0.7, capsize=3)

        ax.axhline(threshold, color="#6b6b6b", linewidth=1.2, linestyle=(0, (4, 3)), label="stability threshold")
        ax.set_xlabel("shots", fontweight="semibold")
        ax.set_ylabel("stability (CI)", fontweight="semibold")
        ax.set_title("Stability vs Cost (Shots)")
        ax.set_xscale("log", base=2)
        lo = max(0.0, float(np.nanmin(lows)) - 0.04)
        hi = min(1.0, float(np.nanmax(highs)) + 0.03)
        if hi - lo < 0.12:
            lo = max(0.0, hi - 0.12)
        ax.set_ylim(lo, hi)
        ax.set_xticks(xs)
        ax.set_xticklabels([str(x) for x in xs])
        if len(xs) == 1:
            x = xs[0]
            pad = max(1.0, 0.06 * x)
            ax.set_xlim(x - pad, x + pad)

        y_annot_top = ax.get_ylim()[1]
        for x, low, decision, n_eval in zip(xs, lows, decisions, eval_counts):
            y = min(y_annot_top - 0.01, low + 0.012)
            ax.text(
                x,
                y,
                f"{decision}, n={n_eval}",
                fontsize=7.3,
                color="#2f2f2f",
                ha="center",
                va="bottom",
            )
        ax.legend(loc="lower right")
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320, bbox_inches="tight")
        plt.close(fig)
    return True


def plot_factor_attribution(
    per_graph: dict[str, Any],
    *,
    selected_delta: str,
    out_path: Path,
) -> bool:
    import matplotlib.pyplot as plt

    if not per_graph:
        return False
    graph_id, graph_payload = next(iter(per_graph.items()))
    attrib = graph_payload.get("factor_attribution", {}).get(selected_delta)
    if not attrib:
        return False

    dim_payload = attrib.get("by_dimension", {})
    dimensions = list(dim_payload.keys())
    if not dimensions:
        return False

    with plt.rc_context(report_plot_rc()):
        fig, axes = plt.subplots(len(dimensions), 1, figsize=(7.8, 2.9 * len(dimensions)))
        if len(dimensions) == 1:
            axes = [axes]

        stem_color = "#2f6690"
        marker_style = "o"

        for ax, dim in zip(axes, dimensions):
            values = dim_payload.get(dim, {})
            labels = sorted(list(values.keys()), key=numeric_sort_key)
            rates = [float(values[label].get("flip_rate", 0.0)) for label in labels]
            x = list(range(len(labels)))
            for xi, rate in zip(x, rates):
                ax.vlines(
                    xi,
                    0.0,
                    rate,
                    color=stem_color,
                    linewidth=2.4,
                    linestyles=(0, (4, 2)),
                    alpha=0.95,
                )
                ax.scatter(
                    [xi],
                    [rate],
                    s=80,
                    marker=marker_style,
                    facecolor=stem_color,
                    edgecolor="#2f2f2f",
                    linewidth=0.45,
                    zorder=4,
                )
                ax.text(xi, rate + 0.01, f"{rate:.2f}", ha="center", va="bottom", fontsize=7.8, color="#2f2f2f")
            max_rate = max(rates) if rates else 0.0
            upper = 0.12 if max_rate == 0.0 else min(1.0, max(0.12, max_rate + 0.1))
            ax.set_ylim(0.0, upper)
            ax.set_xticks(x)
            ax.set_xticklabels([str(v) for v in labels])
            ax.set_ylabel("flip rate", fontweight="semibold")
            ax.set_title(f"{graph_id}: {dim} (delta={selected_delta})", fontsize=11.2)

        axes[-1].set_xlabel("dimension value", fontweight="semibold")
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320, bbox_inches="tight")
        plt.close(fig)
    return True
