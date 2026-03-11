from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from claimstab.figures.adaptive import plot_compact_table
from claimstab.figures.style import (
    FIG_H_WIDE,
    FIG_W_WIDE,
    PAPER_GRAY_DARK,
    PAPER_GRAY_LIGHT,
    PAPER_GRAY_MEDIUM,
    PAPER_RED_DARK,
    PAPER_RED_LIGHT,
    apply_style,
    save_fig,
)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"RQ4 summary must be a mapping/object: {path}")
    return payload


def _strategy_points(summary: dict[str, Any]) -> list[dict[str, Any]]:
    strategies = summary.get("strategies", [])
    if not isinstance(strategies, list):
        return []
    points: list[dict[str, Any]] = []
    for row in strategies:
        if not isinstance(row, dict):
            continue
        per_delta = row.get("rows_by_delta", [])
        if not isinstance(per_delta, list):
            continue
        ci_widths: list[float] = []
        costs: list[float] = []
        for drow in per_delta:
            if not isinstance(drow, dict):
                continue
            ci_low = _as_float(drow.get("stability_ci_low"), 0.0)
            ci_high = _as_float(drow.get("stability_ci_high"), 0.0)
            ci_widths.append(max(0.0, ci_high - ci_low))
            costs.append(_as_float(drow.get("n_claim_evals"), 0.0))
        if not ci_widths:
            continue
        points.append(
            {
                "strategy": str(row.get("strategy", "unknown")),
                "strategy_group": str(row.get("strategy_group", "unknown")),
                "k_used": _as_float(row.get("k_used"), 0.0),
                "cost_mean": (sum(costs) / len(costs)) if costs else 0.0,
                "ci_width_mean": sum(ci_widths) / len(ci_widths),
                "agreement_rate": _as_float((row.get("agreement_with_factorial") or {}).get("rate"), 0.0),
            }
        )
    return points


def _plot_ci_width_vs_cost(points: list[dict[str, Any]], out_path: Path) -> dict[str, str] | None:
    if not points:
        return None

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    strategy_style = {
        "full_factorial": {"color": PAPER_GRAY_MEDIUM, "marker": "s", "size": 58.0, "label": "full_factorial"},
        "random_k_32": {"color": PAPER_GRAY_LIGHT, "marker": "o", "size": 56.0, "label": "random_k_32"},
        "random_k_64": {"color": PAPER_GRAY_DARK, "marker": "o", "size": 56.0, "label": "random_k_64"},
        "adaptive_ci": {"color": PAPER_RED_DARK, "marker": "D", "size": 64.0, "label": "adaptive_ci"},
        "adaptive_ci_tuned": {"color": PAPER_RED_LIGHT, "marker": "D", "size": 64.0, "label": "adaptive_ci_tuned"},
    }
    rows_sorted = sorted(points, key=lambda r: (_as_float(r.get("cost_mean")), str(r.get("strategy"))))
    for row in rows_sorted:
        strategy = str(row.get("strategy", "unknown"))
        style = strategy_style.get(
            strategy,
            {"color": PAPER_GRAY_DARK, "marker": "o", "size": 54.0, "label": strategy},
        )
        x = _as_float(row.get("cost_mean"))
        y = _as_float(row.get("ci_width_mean"))
        ax.vlines(x, 0.0, y, color=PAPER_GRAY_LIGHT, linewidth=1.0, alpha=0.55, zorder=1)
        ax.scatter(
            [x],
            [y],
            marker=str(style["marker"]),
            s=float(style["size"]),
            color=str(style["color"]),
            edgecolors="white",
            linewidths=0.8,
            label=str(style["label"]),
            zorder=3,
        )
    ax.set_xlabel("cost (n_claim_evals)")
    ax.set_ylabel("mean CI width")
    ax.set_ylim(bottom=0.0)
    ax.set_title("RQ4 CI width vs cost", loc="left")
    ax.legend(loc="upper right", ncol=2, frameon=False, fontsize=10, handletextpad=0.4, columnspacing=1.2)
    return save_fig(fig, out_path)


def _plot_agreement_vs_cost(points: list[dict[str, Any]], out_path: Path) -> dict[str, str] | None:
    if not points:
        return None
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in points:
        grouped.setdefault(str(row.get("strategy_group", "unknown")), []).append(row)

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    palette = {
        "full_factorial": PAPER_GRAY_MEDIUM,
        "random_k": PAPER_GRAY_DARK,
        "adaptive_ci": PAPER_RED_DARK,
        "adaptive_ci_tuned": PAPER_RED_LIGHT,
    }
    all_agreement: list[float] = []
    for group, rows in sorted(grouped.items()):
        rows_sorted = sorted(rows, key=lambda r: (_as_float(r.get("k_used")), _as_float(r.get("cost_mean"))))
        xs = [_as_float(r.get("cost_mean")) for r in rows_sorted]
        ys = [_as_float(r.get("agreement_rate")) for r in rows_sorted]
        all_agreement.extend(ys)
        ax.plot(
            xs,
            ys,
            marker="o",
            linewidth=2.0,
            color=palette.get(group, "#666666"),
            label=group,
        )
    if all_agreement and (max(all_agreement) - min(all_agreement) < 0.005):
        rows = []
        for row in sorted(points, key=lambda r: str(r.get("strategy"))):
            rows.append([_as_float(row.get("agreement_rate")), _as_float(row.get("cost_mean"))])
        import numpy as np

        ax.cla()
        plot_compact_table(
            ax,
            row_labels=[str(r.get("strategy")) for r in sorted(points, key=lambda r: str(r.get("strategy")))],
            col_labels=["agreement", "cost"],
            matrix=np.array(rows, dtype=float),
            title="RQ4 agreement vs cost",
            note="Line chart replaced by compact table because agreement is nearly constant across strategies.",
        )
        return save_fig(fig, out_path)
    ax.set_ylim(0.0, 1.03)
    ax.set_xlabel("cost (n_claim_evals)")
    ax.set_ylabel("decision agreement vs full_factorial")
    ax.set_title("RQ4 agreement vs cost", loc="left")
    ax.legend(loc="lower right")
    return save_fig(fig, out_path)


def plot_rq4_adaptive(summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    points = _strategy_points(summary)
    ci_ref = _plot_ci_width_vs_cost(points, out_dir / "fig_rq4_ci_width_vs_cost")
    agree_ref = _plot_agreement_vs_cost(points, out_dir / "fig_rq4_agreement_vs_cost")
    return {
        "points": len(points),
        "ci_width_vs_cost": ci_ref,
        "agreement_vs_cost": agree_ref,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Plot RQ4 adaptive sampling tradeoff figures from summary JSON.")
    ap.add_argument("--input", required=True, help="Path to rq4_adaptive_summary.json.")
    ap.add_argument("--out", required=True, help="Output directory for figures.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    summary = _load_summary(Path(args.input))
    refs = plot_rq4_adaptive(summary, Path(args.out))
    print("Wrote RQ4 figures:")
    if isinstance(refs.get("ci_width_vs_cost"), dict):
        print(" ", refs["ci_width_vs_cost"].get("pdf"))
        print(" ", refs["ci_width_vs_cost"].get("png"))
    if isinstance(refs.get("agreement_vs_cost"), dict):
        print(" ", refs["agreement_vs_cost"].get("pdf"))
        print(" ", refs["agreement_vs_cost"].get("png"))


if __name__ == "__main__":
    main()
