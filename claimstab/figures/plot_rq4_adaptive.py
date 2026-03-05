from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


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
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in points:
        grouped.setdefault(str(row.get("strategy_group", "unknown")), []).append(row)

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    palette = {
        "full_factorial": "#4c78a8",
        "random_k": "#f58518",
        "adaptive_ci": "#54a24b",
    }
    for group, rows in sorted(grouped.items()):
        rows_sorted = sorted(rows, key=lambda r: (_as_float(r.get("k_used")), _as_float(r.get("cost_mean"))))
        xs = [_as_float(r.get("cost_mean")) for r in rows_sorted]
        ys = [_as_float(r.get("ci_width_mean")) for r in rows_sorted]
        labels = [str(r.get("strategy")) for r in rows_sorted]
        ax.plot(
            xs,
            ys,
            marker="o",
            linewidth=1.7,
            color=palette.get(group, "#666666"),
            label=group,
        )
        for x, y, label in zip(xs, ys, labels):
            ax.text(x, y + 0.0015, label, fontsize=8, ha="center", va="bottom", color="#2f2f2f")
    ax.set_xlabel("cost (n_claim_evals)")
    ax.set_ylabel("mean CI width")
    ax.set_title("RQ4: CI Width vs Cost")
    ax.legend(loc="best")
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
        "full_factorial": "#4c78a8",
        "random_k": "#f58518",
        "adaptive_ci": "#54a24b",
    }
    for group, rows in sorted(grouped.items()):
        rows_sorted = sorted(rows, key=lambda r: (_as_float(r.get("k_used")), _as_float(r.get("cost_mean"))))
        xs = [_as_float(r.get("cost_mean")) for r in rows_sorted]
        ys = [_as_float(r.get("agreement_rate")) for r in rows_sorted]
        labels = [str(r.get("strategy")) for r in rows_sorted]
        ax.plot(
            xs,
            ys,
            marker="o",
            linewidth=1.7,
            color=palette.get(group, "#666666"),
            label=group,
        )
        for x, y, label in zip(xs, ys, labels):
            ax.text(x, y + 0.01, label, fontsize=8, ha="center", va="bottom", color="#2f2f2f")
    ax.set_ylim(0.0, 1.03)
    ax.set_xlabel("cost (n_claim_evals)")
    ax.set_ylabel("decision agreement vs full_factorial")
    ax.set_title("RQ4: Agreement vs Cost")
    ax.legend(loc="best")
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
