from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from claimstab.figures.style import (
    DECISION_COLOR_MAP,
    FIG_H_WIDE,
    FIG_W_WIDE,
    PAPER_GRAY_DARK,
    PAPER_GRAY_LIGHT,
    PAPER_GRAY_MEDIUM,
    PAPER_RED_DARK,
    PAPER_RED_LIGHT,
    PAPER_BLUE_MUTED,
    apply_style,
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _save_bundle(fig, out_base: Path) -> dict[str, str]:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out_base.with_suffix(".pdf")
    png_path = out_base.with_suffix(".png")
    svg_path = out_base.with_suffix(".svg")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png_path, dpi=320, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return {"pdf": str(pdf_path), "png": str(png_path), "svg": str(svg_path)}


def _decision_stack_order() -> list[str]:
    return ["stable", "inconclusive", "unstable"]


def _decision_color(decision: str) -> str:
    return DECISION_COLOR_MAP.get(str(decision), PAPER_GRAY_MEDIUM)


def plot_e1_prevalence_by_scope(csv_path: Path, out_base: Path) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    order = ["compilation_only_exact", "sampling_only_exact", "combined_light_exact"]
    df["space_preset"] = pd.Categorical(df["space_preset"], categories=order, ordered=True)
    df = df.sort_values("space_preset")

    labels = {
        "compilation_only_exact": "Compilation",
        "sampling_only_exact": "Sampling",
        "combined_light_exact": "Combined",
    }

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), constrained_layout=False)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.16, top=0.88)
    x = range(len(df))
    bottom = [0.0] * len(df)
    bar_width = 0.62
    totals = df["total"].astype(float).tolist()

    for decision in _decision_stack_order():
        counts = [float(v) for v in df[decision].tolist()]
        heights = [(count / total) if total else 0.0 for count, total in zip(counts, totals)]
        ax.bar(
            list(x),
            heights,
            bottom=bottom,
            width=bar_width,
            color=_decision_color(decision),
            edgecolor="white",
            linewidth=0.9,
            label=decision,
            zorder=3,
        )
        for idx, (b, h, count) in enumerate(zip(bottom, heights, counts)):
            if h <= 0:
                continue
            if h >= 0.12:
                ax.text(
                    idx,
                    b + h / 2.0,
                    f"{int(count)}\n({int(round(h * 100))}%)",
                    ha="center",
                    va="center",
                    fontsize=9.0,
                    color="white" if decision == "unstable" else PAPER_GRAY_DARK,
                    fontweight="semibold",
                )
        bottom = [b + h for b, h in zip(bottom, heights)]

    ax.set_xticks(list(x), [labels.get(str(v), str(v)) for v in df["space_preset"].tolist()])
    ax.set_ylim(0.0, 1.02)
    ax.set_ylabel("share of E1 claim-space-delta variants")
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.legend(loc="upper right", ncol=3, bbox_to_anchor=(0.98, 1.05))
    ax.grid(axis="x", alpha=0.0)
    ax.grid(axis="y", alpha=0.14)
    fig.text(0.10, 0.955, "Fragility Prevalence in E1 Across Perturbation Scopes", ha="left", va="top", fontsize=11.5, color=PAPER_GRAY_DARK)

    return _save_bundle(fig, out_base)


def plot_claim_metric_mismatch(json_path: Path, out_base: Path) -> dict[str, str]:
    payload = _read_json(json_path)
    case = payload["selected_case"]

    metric_mean = float(case["metric_mean_diff"])
    metric_low = float(case["metric_ci_low"])
    metric_high = float(case["metric_ci_high"])
    stability_hat = float(case["stability_hat"])
    stability_low = float(case["stability_ci_low"])
    stability_high = float(case["stability_ci_high"])
    tau = 0.95

    metric_xmin = min(-0.01, metric_low - 0.02)
    metric_xmax = max(metric_high + 0.02, 0.16)

    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(FIG_W_WIDE + 1.0, FIG_H_WIDE), constrained_layout=False)
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.18, top=0.84, wspace=0.08)

    left, right = axes
    left.axvline(0.0, color=PAPER_GRAY_MEDIUM, linestyle=(0, (4, 3)), linewidth=1.0)
    left.hlines(0.5, metric_low, metric_high, color=PAPER_GRAY_DARK, linewidth=2.2)
    left.vlines([metric_low, metric_high], 0.42, 0.58, color=PAPER_GRAY_DARK, linewidth=1.4)
    left.scatter([metric_mean], [0.5], s=66, color=PAPER_BLUE_MUTED, edgecolor="white", linewidth=0.8, zorder=3)
    left.set_xlim(metric_xmin, metric_xmax)
    left.set_ylim(0.0, 1.0)
    left.set_yticks([])
    left.set_xlabel("metric mean difference")
    left.text(0.02, 0.92, "Traditional metric view", transform=left.transAxes, ha="left", va="top", fontsize=10.0, color=PAPER_GRAY_DARK)
    left.text(
        0.02,
        0.84,
        "Consistent advantage",
        transform=left.transAxes,
        ha="left",
        va="top",
        fontsize=9.2,
        color="#2ca02c",
        fontweight="semibold",
    )
    left.text(
        0.02,
        0.18,
        f"mean diff = {metric_mean:.4f}\n95% CI = [{metric_low:.4f}, {metric_high:.4f}]",
        transform=left.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.8,
        color=PAPER_GRAY_DARK,
        bbox={"facecolor": "#f7f7f7", "edgecolor": "#d7d7d7", "boxstyle": "round,pad=0.34"},
    )
    left.text(0.0, 0.02, "0", transform=left.get_xaxis_transform(), ha="center", va="bottom", fontsize=8.3, color=PAPER_GRAY_MEDIUM)
    left.grid(axis="x", alpha=0.10)
    left.grid(axis="y", alpha=0.0)

    right.axvspan(tau, 1.02, color="#e6f3e1", alpha=0.26, zorder=0)
    right.axvline(tau, color=PAPER_RED_DARK, linestyle=(0, (4, 3)), linewidth=1.2)
    right.hlines(0.5, stability_low, stability_high, color=PAPER_GRAY_DARK, linewidth=2.2)
    right.vlines([stability_low, stability_high], 0.42, 0.58, color=PAPER_GRAY_DARK, linewidth=1.4)
    right.scatter([stability_hat], [0.5], s=66, color=_decision_color("unstable"), edgecolor="white", linewidth=0.8, zorder=3)
    right.set_xlim(0.0, 1.02)
    right.set_ylim(0.0, 1.0)
    right.set_yticks([])
    right.set_xlabel(r"claim stability estimate $\hat{s}$")
    right.text(0.02, 0.92, "Claim-centric view", transform=right.transAxes, ha="left", va="top", fontsize=10.0, color=PAPER_GRAY_DARK)
    right.text(
        0.02,
        0.84,
        "Unstable claim",
        transform=right.transAxes,
        ha="left",
        va="top",
        fontsize=9.2,
        color=_decision_color("unstable"),
        fontweight="semibold",
    )
    right.text(
        0.02,
        0.18,
        f"$\\hat{{s}}$ = {stability_hat:.4f}\nWilson 95% CI = [{stability_low:.4f}, {stability_high:.4f}]",
        transform=right.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.8,
        color=PAPER_GRAY_DARK,
        bbox={"facecolor": "#f7f7f7", "edgecolor": "#d7d7d7", "boxstyle": "round,pad=0.34"},
    )
    right.text(
        tau + 0.01,
        0.08,
        "stable region",
        color=PAPER_BLUE_MUTED,
        fontsize=8.1,
        ha="left",
        va="bottom",
    )
    right.text(
        tau,
        0.02,
        r"$\tau = 0.95$",
        transform=right.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=8.3,
        color=PAPER_RED_DARK,
    )
    right.grid(axis="x", alpha=0.10)
    right.grid(axis="y", alpha=0.0)

    fig.text(0.50, 0.965, "Claim–Metric Mismatch", ha="center", va="top", fontsize=11.2, color=PAPER_GRAY_DARK)
    fig.text(
        0.50,
        0.04,
        f"{case['claim_pair']} | {case['space_preset']} | δ = {float(case['delta']):.2f}",
        ha="center",
        va="bottom",
        fontsize=8.5,
        color=PAPER_BLUE_MUTED,
    )

    return _save_bundle(fig, out_base)


def plot_claim_family_verdicts(csv_path: Path, out_base: Path) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    order = ["ranking", "decision", "distribution"]
    df["claim_family"] = pd.Categorical(df["claim_family"], categories=order, ordered=True)
    df = df.sort_values("claim_family")

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), constrained_layout=False)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.16, top=0.88)

    x = range(len(df))
    bottom = [0.0] * len(df)
    totals = df["total"].astype(float).tolist()

    for decision in _decision_stack_order():
        shares = [
            (float(count) / total) if total else 0.0
            for count, total in zip(df[decision].astype(float).tolist(), totals)
        ]
        ax.bar(
            list(x),
            shares,
            bottom=bottom,
            width=0.62,
            color=_decision_color(decision),
            edgecolor="white",
            linewidth=0.9,
            label=decision,
            zorder=3,
        )
        for idx, (b, h, count) in enumerate(zip(bottom, shares, df[decision].astype(int).tolist())):
            if h < 0.08:
                continue
            ax.text(
                idx,
                b + h / 2.0,
                f"{int(round(h * 100))}%",
                ha="center",
                va="center",
                fontsize=10.0,
                color="white" if decision == "unstable" else PAPER_GRAY_DARK,
                fontweight="semibold",
            )
            ax.text(
                idx,
                b + h / 2.0 - 0.10,
                f"(n={count})",
                ha="center",
                va="center",
                fontsize=8.2,
                color="white" if decision == "unstable" else PAPER_GRAY_DARK,
            )
        bottom = [b + h for b, h in zip(bottom, shares)]

    ax.set_xticks(
        list(x),
        [f"{str(v).capitalize()}\n(n={total})" for v, total in zip(df["claim_family"].tolist(), df["total"].astype(int).tolist())],
    )
    ax.set_ylim(0.0, 1.08)
    ax.set_ylabel("share of verdicts within claim family")
    ax.legend(loc="upper right", ncol=3)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="y", alpha=0.18)
    ax.grid(axis="x", alpha=0.0)
    fig.text(0.12, 0.955, "Verdict Distribution Across Claim Families", ha="left", va="top", fontsize=11.5, color=PAPER_GRAY_DARK)

    return _save_bundle(fig, out_base)


def _update_manifest(manifest_path: Path, refs: dict[str, dict[str, str]]) -> None:
    manifest = _read_json(manifest_path) if manifest_path.exists() else {"figures": {}, "icse_main": {}}
    manifest.setdefault("figures", {})
    manifest.setdefault("icse_main", {})
    manifest["figures"]["fig4_e1_prevalence_by_scope"] = refs["fig4_e1_prevalence_by_scope"]
    manifest["figures"]["fig5_claim_metric_mismatch"] = refs["fig5_claim_metric_mismatch"]
    manifest["figures"]["fig6_claim_family_verdicts"] = refs["fig6_claim_family_verdicts"]
    manifest["icse_main"]["fig4_e1_prevalence_by_scope"] = refs["fig4_e1_prevalence_by_scope"]
    manifest["icse_main"]["fig5_claim_metric_mismatch"] = refs["fig5_claim_metric_mismatch"]
    manifest["icse_main"]["fig6_claim_family_verdicts"] = refs["fig6_claim_family_verdicts"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate focused evaluation_v2 main-paper figures.")
    ap.add_argument("--root", default="output/paper/evaluation_v2")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    derived = root / "derived_paper_evaluation"
    main_dir = root / "pack" / "figures" / "main"
    manifest_path = root / "pack" / "figures" / "manifest.json"

    refs = {
        "fig4_e1_prevalence_by_scope": plot_e1_prevalence_by_scope(
            derived / "RQ1_necessity" / "e1_verdicts_by_scope.csv",
            main_dir / "fig4_e1_prevalence_by_scope",
        ),
        "fig5_claim_metric_mismatch": plot_claim_metric_mismatch(
            derived / "RQ1_necessity" / "claim_metric_mismatch_case.json",
            main_dir / "fig5_claim_metric_mismatch",
        ),
        "fig6_claim_family_verdicts": plot_claim_family_verdicts(
            derived / "RQ2_semantics" / "verdicts_by_claim_family.csv",
            main_dir / "fig6_claim_family_verdicts",
        ),
    }
    _update_manifest(manifest_path, refs)
    print("Wrote focused evaluation_v2 figures:")
    for name, ref in refs.items():
        print(f"  {name}: {ref['png']}")


if __name__ == "__main__":
    main()
