from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
RQ1_DATASET = REPO_ROOT / "output" / "paper" / "icse_pack" / "derived" / "RQ1" / "metric_claim_comparison_dataset.csv"

OUT_ROOT = REPO_ROOT / "output" / "paper" / "icse_pack"
DERIVED_DIR = OUT_ROOT / "derived" / "RQ2"
TABLE_DIR = OUT_ROOT / "tables"
FIG_DIR = OUT_ROOT / "figures" / "main"

FAMILY_ORDER = ["MaxCut QAOA", "Max-2-SAT QAOA", "VQE/H2"]
OUTCOME_ORDER = ["validated", "refuted", "unstable", "inconclusive"]
OUTCOME_LABELS = {
    "validated": "Validated",
    "refuted": "Refuted",
    "unstable": "Unstable",
    "inconclusive": "Inconclusive",
}
OUTCOME_COLORS = {
    "validated": "#365c4a",
    "refuted": "#34435e",
    "unstable": "#9f3d2f",
    "inconclusive": "#ead7d2",
}
MISMATCH_ORDER = [
    "false_confidence",
    "direction_reversal_refutation",
    "near_threshold_inconclusive",
]
MISMATCH_LABELS = {
    "false_confidence": "False\nconfidence",
    "direction_reversal_refutation": "Direction reversal /\nrefutation",
    "near_threshold_inconclusive": "Near-threshold\ninconclusive",
}
MISMATCH_COLORS = {
    "false_confidence": OUTCOME_COLORS["unstable"],
    "direction_reversal_refutation": OUTCOME_COLORS["refuted"],
    "near_threshold_inconclusive": OUTCOME_COLORS["inconclusive"],
}
TAU = 0.95


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
        }
    )


def _load_dataset() -> pd.DataFrame:
    df = pd.read_csv(RQ1_DATASET)
    claim_families = sorted(set(df["claim_family"].astype(str)))
    if claim_families != ["comparative"] and claim_families != ["ranking"]:
        # Keep the current task honest: this evidence surface is only for the
        # comparative/ranking population already frozen in RQ1.
        raise ValueError(f"Unexpected claim_family surface for RQ2 cross-family derivation: {claim_families}")
    return df


def _make_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILY_ORDER:
        family_df = df[df["algorithm_family"] == family].copy()
        rows.append(
            {
                "algorithm_family": family,
                "claim_family_surface": "comparative/ranking only",
                "total_variants": int(len(family_df)),
                "metric_positive_count": int((family_df["metric_verdict"] == "positive").sum()),
                "false_reassurance_count": int((family_df["false_reassurance_type"] != "none").sum()),
                "stable_count": int((family_df["claim_stability_verdict"] == "stable").sum()),
                "unstable_count": int((family_df["claim_stability_verdict"] == "unstable").sum()),
                "inconclusive_count": int((family_df["claim_stability_verdict"] == "inconclusive").sum()),
                "validated_count": int((family_df["claim_validation_outcome"] == "validated").sum()),
                "refuted_count": int((family_df["claim_validation_outcome"] == "refuted").sum()),
                "outcome_unstable_count": int((family_df["claim_validation_outcome"] == "unstable").sum()),
                "outcome_inconclusive_count": int((family_df["claim_validation_outcome"] == "inconclusive").sum()),
            }
        )
    return rows


def _make_mismatch_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    counts = {
        "false_confidence": int(
            ((df["metric_verdict"] == "positive") & (df["claim_validation_outcome"] != "validated")).sum()
        ),
        "direction_reversal_refutation": int((df["claim_validation_outcome"] == "refuted").sum()),
        "near_threshold_inconclusive": int(
            (
                (df["claim_validation_outcome"] == "inconclusive")
                & (df["claim_ci_lower"] < TAU)
                & (df["claim_ci_upper"] >= TAU)
            ).sum()
        ),
    }
    return [
        {
            "mismatch_kind": mismatch_kind,
            "label": MISMATCH_LABELS[mismatch_kind].replace("\n", " "),
            "n_cases": counts[mismatch_kind],
        }
        for mismatch_kind in MISMATCH_ORDER
    ]


def _plot_outcomes(df: pd.DataFrame, mismatch_rows: list[dict[str, Any]], out_png: Path, out_pdf: Path) -> None:
    _set_style()
    fig, (ax_left, ax_right) = plt.subplots(
        1,
        2,
        figsize=(11.4, 4.3),
        constrained_layout=False,
        gridspec_kw={"width_ratios": [2.05, 1.25]},
    )
    fig.subplots_adjust(left=0.18, right=0.97, top=0.82, bottom=0.18, wspace=0.26)

    y_positions = list(range(len(FAMILY_ORDER)))
    lefts = [0.0] * len(FAMILY_ORDER)
    for outcome in OUTCOME_ORDER:
        shares = []
        counts = []
        for family in FAMILY_ORDER:
            family_df = df[df["algorithm_family"] == family]
            total = max(1, len(family_df))
            count = int((family_df["claim_validation_outcome"] == outcome).sum())
            share = 100.0 * float(count) / total
            shares.append(share)
            counts.append(count)
        ax_left.barh(
            y_positions,
            shares,
            left=lefts,
            color=OUTCOME_COLORS[outcome],
            edgecolor="white",
            linewidth=0.8,
            height=0.64,
            label=OUTCOME_LABELS[outcome],
        )
        for idx, (share, count) in enumerate(zip(shares, counts)):
            if share >= 9.0:
                ax_left.text(
                    lefts[idx] + share / 2.0,
                    idx,
                    f"{count}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if outcome in {"validated", "refuted", "unstable"} else "#222222",
                    fontweight="bold",
                )
            lefts[idx] += share

    family_tick_labels = []
    for family in FAMILY_ORDER:
        total = int(len(df[df["algorithm_family"] == family]))
        family_tick_labels.append(f"{family} (n={total})")

    ax_left.set_xlim(0, 100)
    ax_left.set_xlabel("Share of comparative claim variants")
    ax_left.set_yticks(y_positions)
    ax_left.set_yticklabels(family_tick_labels)
    ax_left.invert_yaxis()
    ax_left.grid(axis="x", color="#dddddd", linewidth=0.6)
    ax_left.grid(axis="y", visible=False)
    ax_left.set_axisbelow(True)
    ax_left.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.10), ncol=4)
    for spine in ["top", "right"]:
        ax_left.spines[spine].set_visible(False)
    ax_left.tick_params(axis="x", top=False)

    mismatch_labels = [MISMATCH_LABELS[str(row["mismatch_kind"])] for row in mismatch_rows]
    mismatch_counts = [int(row["n_cases"]) for row in mismatch_rows]
    mismatch_colors = [MISMATCH_COLORS[str(row["mismatch_kind"])] for row in mismatch_rows]
    mismatch_x = list(range(len(mismatch_rows)))
    ax_right.bar(
        mismatch_x,
        mismatch_counts,
        color=mismatch_colors,
        edgecolor="white",
        linewidth=0.8,
        width=0.62,
    )
    for idx, count in enumerate(mismatch_counts):
        ax_right.text(
            idx,
            count + 0.55,
            f"{count}",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#222222",
            fontweight="bold",
        )
    ax_right.set_ylim(0, max(mismatch_counts) + 4)
    ax_right.set_ylabel("Count of claim variants")
    ax_right.set_xticks(mismatch_x)
    ax_right.set_xticklabels(mismatch_labels)
    ax_right.tick_params(axis="x", labelsize=9)
    ax_right.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax_right.grid(axis="x", visible=False)
    ax_right.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax_right.spines[spine].set_visible(False)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def _write_note(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    maxcut = next(row for row in summary_rows if row["algorithm_family"] == "MaxCut QAOA")
    max2sat = next(row for row in summary_rows if row["algorithm_family"] == "Max-2-SAT QAOA")
    vqe = next(row for row in summary_rows if row["algorithm_family"] == "VQE/H2")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# RQ2 Interpretation: Cross-Family Heterogeneity",
                "",
                "This RQ2 surface covers comparative/ranking claims only. It should be read as cross-algorithm-family evidence, not as full claim-family coverage.",
                "",
                "Current pattern:",
                f"- MaxCut QAOA is dominated by unstable outcomes ({maxcut['outcome_unstable_count']}/{maxcut['total_variants']})",
                f"- Max-2-SAT QAOA contains many validated variants ({max2sat['validated_count']}/{max2sat['total_variants']}) together with unstable and inconclusive cases",
                f"- VQE/H2 is mostly refuted rather than unstable ({vqe['refuted_count']}/{vqe['total_variants']} refuted)",
                "",
                "Safe paper-facing takeaway:",
                "ClaimStab-QC is not uniformly pessimistic. Across comparative claims, the outcome mix differs substantially by algorithm family, so the main RQ1 mismatch is structural but population-dependent.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    df = _load_dataset()
    summary_rows = _make_summary(df)
    mismatch_rows = _make_mismatch_summary(df)
    dataset_rows = df[
        [
            "claim_id",
            "algorithm_family",
            "claim_family",
            "scope",
            "delta",
            "metric_verdict",
            "claim_stability_verdict",
            "claim_validation_outcome",
            "false_reassurance_type",
        ]
    ].to_dict(orient="records")

    _write_csv(DERIVED_DIR / "cross_family_dataset.csv", dataset_rows)
    _write_json(DERIVED_DIR / "cross_family_dataset.json", dataset_rows)
    _write_csv(TABLE_DIR / "tab_rq2_cross_family_summary.csv", summary_rows)
    _write_csv(DERIVED_DIR / "rq2_mismatch_counts_for_figure.csv", mismatch_rows)
    _plot_outcomes(
        df,
        mismatch_rows,
        FIG_DIR / "fig5_cross_family_outcomes.png",
        FIG_DIR / "fig5_cross_family_outcomes.pdf",
    )
    _write_note(DERIVED_DIR / "cross_family_interpretation.md", summary_rows)
    _write_json(
        DERIVED_DIR / "cross_family_summary.json",
        {
            "schema_version": "rq2_cross_family_icse_v1",
            "source_dataset": str(RQ1_DATASET),
            "rows": {"dataset": len(dataset_rows), "summary": len(summary_rows)},
        },
    )
    print("Wrote RQ2 cross-family outputs to", DERIVED_DIR)


if __name__ == "__main__":
    main()
