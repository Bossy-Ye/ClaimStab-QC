from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from claimstab.figures.style import PAPER_BLUE_MUTED, PAPER_GRAY_DARK, PAPER_GRAY_MEDIUM, apply_style, decision_color
from claimstab.spec import load_spec


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return load_spec(path, validate=False)


def _experiments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    experiments = payload.get("experiments", [])
    if not isinstance(experiments, list) or not experiments:
        raise ValueError("claim_stability.json does not contain any experiments")
    return experiments


def _sorted_delta_rows(experiment: dict[str, Any]) -> list[dict[str, Any]]:
    rows = experiment.get("overall", {}).get("delta_sweep", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("No overall.delta_sweep rows found in claim_stability.json")
    return sorted(rows, key=lambda row: float(row.get("delta", 0.0)))


def _space_label(space: str) -> str:
    return str(space).replace("_", " ")


def _task_card_lines(spec: dict[str, Any], experiments: list[dict[str, Any]]) -> list[str]:
    experiment = experiments[0]
    rows = _sorted_delta_rows(experiment)
    claim = experiment.get("claim", {})
    params = spec.get("task", {}).get("params", {}) if isinstance(spec.get("task"), dict) else {}
    first_row = rows[0]

    lines = [
        f"Claim: {claim.get('method_a')} vs {claim.get('method_b')}",
        f"Metric: {claim.get('metric_name', 'objective')} ({'higher' if claim.get('higher_is_better', True) else 'lower'} is better)",
        f"Claim evals per delta: {first_row.get('n_claim_evals', 'n/a')}",
    ]
    if params:
        lines.extend(
            [
                f"Code distance: {params.get('distance', 'n/a')}",
                f"Physical error rate: {params.get('physical_error_rate', 'n/a')}",
                f"Instances: {params.get('num_instances', 'n/a')}",
            ]
        )
    lines.append("Scopes:")
    for experiment in experiments:
        sampling = experiment.get("sampling", {})
        lines.append(
            "  "
            + f"{_space_label(str(sampling.get('space_preset', 'n/a')))}: "
            + f"{sampling.get('sampled_configurations_with_baseline', 'n/a')}/"
            + f"{sampling.get('perturbation_space_size', 'n/a')} configs"
        )
    return lines


def _key_findings(experiments: list[dict[str, Any]]) -> list[str]:
    by_delta: dict[float, list[tuple[str, str]]] = {}
    for experiment in experiments:
        space = str(experiment.get("sampling", {}).get("space_preset", "unknown"))
        for row in _sorted_delta_rows(experiment):
            delta = float(row.get("delta", 0.0))
            by_delta.setdefault(delta, []).append((space, str(row.get("decision", "unknown"))))

    findings: list[str] = []
    for delta in sorted(by_delta):
        decisions = by_delta[delta]
        decision_set = {decision for _, decision in decisions}
        if len(decision_set) == 1:
            findings.append(f"delta={delta:.2f}: {next(iter(decision_set))} in all shown scopes")
        else:
            detail = ", ".join(f"{_space_label(space)}={decision}" for space, decision in decisions)
            findings.append(f"delta={delta:.2f}: {detail}")
    return findings


def _save_figure_bundle(fig, out_base: Path) -> dict[str, str]:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = out_base.with_suffix(".pdf")
    svg_path = out_base.with_suffix(".svg")
    png_path = out_base.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.03)
    return {"pdf": str(pdf_path), "svg": str(svg_path), "png": str(png_path)}


def plot_qec_pilot_summary(
    payload: dict[str, Any],
    *,
    out_base: Path,
    spec: dict[str, Any] | None = None,
) -> dict[str, str]:
    spec = spec or {}
    experiments = _experiments(payload)
    claim = experiments[0].get("claim", {})
    all_rows = [_sorted_delta_rows(experiment) for experiment in experiments]
    threshold = float(all_rows[0][0].get("decision_explanation", {}).get("threshold", 0.95))
    y_labels = [f"delta = {float(row.get('delta', 0.0)):.2f}" for row in all_rows[0]]
    y_pos = list(range(len(y_labels)))

    apply_style()
    plt.rcParams.update(
        {
            "font.size": 9.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.0,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 9.0,
            "figure.constrained_layout.use": False,
        }
    )

    n_spaces = len(experiments)
    fig = plt.figure(figsize=(3.2 * n_spaces + 3.2, 4.8), constrained_layout=False)
    fig.set_constrained_layout(False)
    gs = fig.add_gridspec(1, n_spaces + 1, width_ratios=([2.15] * n_spaces) + [1.95])
    axes = [fig.add_subplot(gs[0, idx]) for idx in range(n_spaces)]
    card_ax = fig.add_subplot(gs[0, n_spaces])
    fig.subplots_adjust(left=0.12, right=0.97, top=0.82, bottom=0.14, wspace=0.12)

    for idx, (ax, experiment, rows) in enumerate(zip(axes, experiments, all_rows)):
        sampling = experiment.get("sampling", {})
        ax.axvspan(0.0, threshold, color="#d62728", alpha=0.035, zorder=0)
        ax.axvspan(threshold, 1.02, color="#2ca02c", alpha=0.035, zorder=0)
        ax.axvline(threshold, color=PAPER_GRAY_MEDIUM, linestyle=(0, (4, 3)), linewidth=1.2, zorder=1)

        for y, row in zip(y_pos, rows):
            low = float(row.get("stability_ci_low", row.get("decision_explanation", {}).get("ci_low", 0.0)))
            high = float(row.get("stability_ci_high", row.get("decision_explanation", {}).get("ci_high", 1.0)))
            est = float(row.get("stability_hat", row.get("decision_explanation", {}).get("estimate", 0.0)))
            decision = str(row.get("decision", row.get("decision_explanation", {}).get("decision", "inconclusive")))
            hold_rate = float(row.get("holds_rate_mean", 0.0))
            color = decision_color(decision)

            ax.hlines(y, low, high, color=PAPER_GRAY_DARK, linewidth=2.2, zorder=2)
            ax.vlines([low, high], y - 0.09, y + 0.09, color=PAPER_GRAY_DARK, linewidth=1.5, zorder=2)
            ax.scatter([est], [y], s=58, color=color, edgecolor="white", linewidth=0.8, zorder=3)
            ax.text(
                min(est + 0.03, 0.97),
                y - 0.14,
                decision,
                ha="left",
                va="center",
                color=color,
                fontsize=8.2,
            )
            ax.text(
                min(est + 0.03, 0.97),
                y + 0.14,
                f"hold={hold_rate:.2f}",
                ha="left",
                va="center",
                color=PAPER_GRAY_MEDIUM,
                fontsize=7.6,
            )

        ax.set_xlim(0.0, 1.02)
        ax.set_ylim(-0.5, len(rows) - 0.5)
        ax.set_yticks(y_pos)
        if idx == 0:
            ax.set_yticklabels(y_labels)
        else:
            ax.set_yticklabels([])
        ax.invert_yaxis()
        ax.set_xlabel("stability estimate")
        ax.set_title(_space_label(str(sampling.get("space_preset", "n/a"))), loc="left", pad=8.0)
        ax.text(
            0.0,
            0.98,
            f"{sampling.get('sampled_configurations_with_baseline', 'n/a')}/{sampling.get('perturbation_space_size', 'n/a')} sampled/space",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.1,
            color=PAPER_BLUE_MUTED,
        )
        ax.grid(axis="x", alpha=0.22)
        ax.grid(axis="y", alpha=0.0)

    axes[0].set_ylabel("claim margin")
    fig.text(
        0.12,
        0.95,
        "QEC Pilot Scope Comparison",
        ha="left",
        va="bottom",
        fontsize=12.2,
        color=PAPER_GRAY_DARK,
    )
    fig.text(
        0.12,
        0.915,
        f"{claim.get('method_a')} vs {claim.get('method_b')} on {claim.get('metric_name', 'objective')}",
        ha="left",
        va="bottom",
        fontsize=9.4,
        color=PAPER_BLUE_MUTED,
    )

    card_ax.axis("off")
    card_title = "Setup and Findings"
    card_body = "\n".join(_task_card_lines(spec, experiments))
    card_ax.text(
        0.02,
        0.98,
        card_title,
        ha="left",
        va="top",
        fontsize=10.4,
        color=PAPER_GRAY_DARK,
        fontweight="semibold",
    )
    card_ax.text(
        0.02,
        0.90,
        card_body,
        ha="left",
        va="top",
        fontsize=8.9,
        color=PAPER_GRAY_DARK,
        linespacing=1.45,
        bbox={"facecolor": "#f6f3ee", "edgecolor": "#ddd5ca", "boxstyle": "round,pad=0.5"},
    )
    findings_text = "\n".join(_key_findings(experiments))
    card_ax.text(
        0.02,
        0.33,
        "Readout:\n" + findings_text,
        ha="left",
        va="top",
        fontsize=8.5,
        color=PAPER_GRAY_DARK,
        linespacing=1.45,
    )
    card_ax.text(
        0.02,
        0.12,
        "Interpretation:\nStable means the reported ranking is conditionally robust under the declared scope. This pilot is repetition-code-style only, not a surface-code study.",
        ha="left",
        va="top",
        fontsize=8.2,
        color=PAPER_GRAY_MEDIUM,
        linespacing=1.4,
    )

    refs = _save_figure_bundle(fig, out_base)
    plt.close(fig)
    return refs


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Plot a paper-style summary figure for the external QEC pilot result.")
    ap.add_argument("--json", required=True, help="Path to claim_stability.json")
    ap.add_argument("--spec", default=None, help="Optional spec YAML/JSON for metadata card")
    ap.add_argument("--out", required=True, help="Output base path without extension")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    payload = _load_payload(Path(args.json))
    spec = _load_spec(Path(args.spec)) if args.spec else {}
    refs = plot_qec_pilot_summary(
        payload,
        out_base=Path(args.out),
        spec=spec,
    )
    print("Wrote QEC pilot figure files:")
    for key in ("pdf", "svg", "png"):
        print(" ", refs[key])


if __name__ == "__main__":
    main()
