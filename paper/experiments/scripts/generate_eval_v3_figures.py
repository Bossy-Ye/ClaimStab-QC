from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from claimstab.figures.style import (
    FIG_H_WIDE,
    FIG_W_WIDE,
    PAPER_BLUE_MUTED,
    PAPER_GRAY_DARK,
    PAPER_GRAY_LIGHT,
    PAPER_GRAY_MEDIUM,
    PAPER_RED_DARK,
    PAPER_RED_LIGHT,
    apply_style,
    save_fig,
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _plot_w3_sensitivity(csv_path: Path, out_base: Path) -> dict[str, str]:
    df = pd.read_csv(csv_path).sort_values("sample_size")
    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), constrained_layout=False)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.16, top=0.78)

    ax.plot(
        df["sample_size"],
        df["conditional_false_reassurance_rate_mean"],
        color=PAPER_RED_DARK,
        marker="o",
        linewidth=2.0,
        markersize=5.8,
        zorder=3,
        label="metric baseline",
    )
    yerr_lower = df["conditional_false_reassurance_rate_mean"] - df["conditional_false_reassurance_rate_min"]
    yerr_upper = df["conditional_false_reassurance_rate_max"] - df["conditional_false_reassurance_rate_mean"]
    ax.errorbar(
        df["sample_size"],
        df["conditional_false_reassurance_rate_mean"],
        yerr=[yerr_lower, yerr_upper],
        fmt="none",
        ecolor=PAPER_RED_LIGHT,
        elinewidth=1.1,
        capsize=3.0,
        zorder=2,
    )
    ax.axhline(0.0, color=PAPER_GRAY_MEDIUM, linestyle=(0, (4, 3)), linewidth=1.0, zorder=1)
    ax.text(
        0.02,
        0.06,
        "ClaimStab-QC false reassurance = 0 by construction",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.4,
        color=PAPER_GRAY_MEDIUM,
    )
    ax.annotate(
        "Expanded full-grid baseline",
        xy=(df["sample_size"].iloc[-1], df["conditional_false_reassurance_rate_mean"].iloc[-1]),
        xytext=(-18, -20),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=8.3,
        color=PAPER_GRAY_DARK,
    )
    ax.set_xscale("log")
    ax.set_ylim(-0.02, 1.08)
    ax.set_xlabel("metric baseline size (sampled configurations)")
    ax.set_ylabel("false-reassurance rate")
    ax.grid(axis="y", alpha=0.18)
    ax.grid(axis="x", alpha=0.12)
    fig.text(0.12, 0.965, "Metric False Reassurance Persists as Baseline Size Grows", ha="left", va="top", fontsize=11.2, color=PAPER_GRAY_DARK)
    fig.text(0.12, 0.928, "Sensitivity over the expanded 495-configuration sampling grid used for E5.", ha="left", va="top", fontsize=8.6, color=PAPER_BLUE_MUTED)
    return save_fig(fig, out_base)


def _extract_strategy_points(summary: dict[str, Any], pack_label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy in summary.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        rows.append(
            {
                "pack": pack_label,
                "strategy": str(strategy.get("strategy")),
                "strategy_group": str(strategy.get("strategy_group")),
                "k_used": float(strategy.get("k_used") or 0.0),
                "agreement_rate": float((strategy.get("agreement_with_factorial") or {}).get("rate") or 0.0),
            }
        )
    return rows


def _plot_w5_tradeoff(e5_summary_path: Path, w5_summary_path: Path, out_base: Path) -> dict[str, str]:
    e5 = _read_json(e5_summary_path)
    w5 = _read_json(w5_summary_path)
    rows = _extract_strategy_points(e5, "baseline E5") + _extract_strategy_points(w5, "near-boundary W5")
    baseline = {row["strategy"]: row for row in rows if row["pack"] == "baseline E5"}
    near = {row["strategy"]: row for row in rows if row["pack"] == "near-boundary W5"}
    strategy_order = ["full_factorial", "random_k_32", "random_k_64", "adaptive_ci", "adaptive_ci_tuned"]
    labels = {
        "full_factorial": "full_factorial",
        "random_k_32": "random_k_32",
        "random_k_64": "random_k_64",
        "adaptive_ci": "adaptive_ci",
        "adaptive_ci_tuned": "adaptive_ci_tuned",
    }

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), constrained_layout=False)
    fig.subplots_adjust(left=0.24, right=0.98, bottom=0.14, top=0.82)

    y_positions = list(range(len(strategy_order)))
    bar_h = 0.34
    baseline_vals = [float((baseline.get(name) or {}).get("k_used", 0.0)) for name in strategy_order]
    near_vals = [float((near.get(name) or {}).get("k_used", 0.0)) for name in strategy_order]

    ax.barh(
        [y - bar_h / 2 for y in y_positions],
        baseline_vals,
        height=bar_h,
        color=PAPER_GRAY_LIGHT,
        edgecolor="white",
        linewidth=0.9,
        label="baseline E5",
        zorder=3,
    )
    ax.barh(
        [y + bar_h / 2 for y in y_positions],
        near_vals,
        height=bar_h,
        color=PAPER_RED_LIGHT,
        edgecolor="white",
        linewidth=0.9,
        label="near-boundary W5",
        zorder=3,
    )
    for idx, (b, n) in enumerate(zip(baseline_vals, near_vals)):
        ax.text(b + 6, y_positions[idx] - bar_h / 2, f"{int(b)}", va="center", ha="left", fontsize=8.0, color=PAPER_GRAY_DARK)
        ax.text(n + 6, y_positions[idx] + bar_h / 2, f"{int(n)}", va="center", ha="left", fontsize=8.0, color=PAPER_GRAY_DARK)

    ax.set_yticks(y_positions, [labels[name] for name in strategy_order])
    ax.set_xlabel("evaluated configurations (k_used)")
    ax.set_xlim(0, max(max(baseline_vals), max(near_vals)) * 1.12)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.12)
    ax.grid(axis="y", alpha=0.0)
    ax.legend(loc="lower right")
    fig.text(0.24, 0.965, "Near-Boundary Claims Require Larger Evaluation Budgets", ha="left", va="top", fontsize=11.2, color=PAPER_GRAY_DARK)
    fig.text(0.24, 0.928, "All strategies preserve full_factorial decisions; near-boundary claims consume more configurations.", ha="left", va="top", fontsize=8.6, color=PAPER_BLUE_MUTED)
    return save_fig(fig, out_base)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate evaluation_v3 figures for W3 and W5.")
    ap.add_argument("--root", default="output/paper/evaluation_v3")
    ap.add_argument("--source-e5-summary", default="output/paper/evaluation_v2/runs/E5_policy_comparison/rq4_policy_summary.json")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    derived = root / "derived_paper_evaluation"
    main_dir = root / "pack" / "figures" / "main"
    main_dir.mkdir(parents=True, exist_ok=True)

    refs = {
        "fig_w3_metric_baseline_sensitivity": _plot_w3_sensitivity(
            derived / "RQ1_necessity" / "metric_baseline_sensitivity_summary.csv",
            main_dir / "fig_w3_metric_baseline_sensitivity",
        ),
        "fig_w5_near_boundary_tradeoff": _plot_w5_tradeoff(
            Path(args.source_e5_summary),
            root / "runs" / "W5_near_boundary_policy" / "rq4_near_boundary_summary.json",
            main_dir / "fig_w5_near_boundary_tradeoff",
        ),
    }

    manifest = {
        "schema_version": "evaluation_v3_figures_v1",
        "figures": refs,
    }
    (root / "pack" / "figures").mkdir(parents=True, exist_ok=True)
    (root / "pack" / "figures" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote evaluation_v3 figures:")
    for name, ref in refs.items():
        print(f"  {name}: {ref['png']}")


if __name__ == "__main__":
    main()
