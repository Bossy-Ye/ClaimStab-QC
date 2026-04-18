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
    "validated": "#4d4d4d",
    "refuted": "#7f7f7f",
    "unstable": "#b0b0b0",
    "inconclusive": "#d9d9d9",
}


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
            "font.family": "Times New Roman",
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


def _plot_outcomes(df: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    _set_style()
    fig, ax = plt.subplots(figsize=(7.6, 3.9), constrained_layout=False)
    fig.subplots_adjust(left=0.12, right=0.98, top=0.80, bottom=0.20)

    x_positions = list(range(len(FAMILY_ORDER)))
    bottoms = [0.0] * len(FAMILY_ORDER)
    for outcome in OUTCOME_ORDER:
        shares = []
        for family in FAMILY_ORDER:
            family_df = df[df["algorithm_family"] == family]
            total = max(1, len(family_df))
            share = 100.0 * float((family_df["claim_validation_outcome"] == outcome).sum()) / total
            shares.append(share)
        ax.bar(
            x_positions,
            shares,
            bottom=bottoms,
            color=OUTCOME_COLORS[outcome],
            edgecolor="white",
            linewidth=0.8,
            width=0.70,
            label=OUTCOME_LABELS[outcome],
        )
        for idx, share in enumerate(shares):
            if share >= 12.0:
                ax.text(
                    idx,
                    bottoms[idx] + share / 2.0,
                    f"{share:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if outcome in {"validated", "refuted"} else "#222222",
                )
            bottoms[idx] += share

    for idx, family in enumerate(FAMILY_ORDER):
        total = int(len(df[df["algorithm_family"] == family]))
        ax.text(idx, 102.0, f"n={total}", ha="center", va="bottom", fontsize=9, color="#555555")

    ax.set_ylim(0, 108)
    ax.set_ylabel("Share of comparative claim variants")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(FAMILY_ORDER)
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.10), ncol=4)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.suptitle("Comparative-Claim Outcomes Vary Across Algorithm Families", y=0.99, fontsize=13)

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
    _plot_outcomes(
        df,
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
