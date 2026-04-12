from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
E5_SUMMARY = (
    REPO_ROOT
    / "output"
    / "paper"
    / "evaluation_v2"
    / "derived_paper_evaluation"
    / "RQ4_practicality"
    / "e5_policy_summary.csv"
)
W5_SUMMARY = (
    REPO_ROOT
    / "output"
    / "paper"
    / "evaluation_v3"
    / "derived_paper_evaluation"
    / "RQ4_practicality"
    / "w5_policy_by_strategy.csv"
)

OUT_ROOT = REPO_ROOT / "output" / "paper" / "icse_pack"
DERIVED_DIR = OUT_ROOT / "derived" / "RQ4"
TABLE_DIR = OUT_ROOT / "tables"
FIG_DIR = OUT_ROOT / "figures" / "main"

SCENARIO_LABELS = {
    "baseline_e5": "Clear cases",
    "near_boundary_w5": "Boundary cases",
}
SCENARIO_COLORS = {
    "Clear cases": "#4d4d4d",
    "Boundary cases": "#9a4f4f",
}
STRATEGY_LABELS = {
    "full_factorial": "Full factorial",
    "random_k_32": "Random-k (32)",
    "random_k_64": "Random-k (64)",
    "adaptive_ci": "Adaptive CI",
    "adaptive_ci_tuned": "Adaptive CI tuned",
}
STRATEGY_ORDER = [
    "full_factorial",
    "random_k_32",
    "random_k_64",
    "adaptive_ci",
    "adaptive_ci_tuned",
]


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
    e5 = pd.read_csv(E5_SUMMARY)
    w5 = pd.read_csv(W5_SUMMARY)

    baseline_rows = w5[w5["pack"] == "baseline_e5"].copy()
    boundary_rows = w5[w5["pack"] == "near_boundary_w5"].copy()

    baseline_rows["scenario"] = "Clear cases"
    boundary_rows["scenario"] = "Boundary cases"
    combined = pd.concat([baseline_rows, boundary_rows], ignore_index=True)

    e5_lookup = e5.set_index("strategy")
    rows: list[dict[str, Any]] = []
    for record in combined.to_dict(orient="records"):
        strategy = str(record["strategy"])
        k_used = float(record["k_used"])
        space_size = float(record["perturbation_space_size"])
        fraction = k_used / space_size if space_size else 0.0
        e5_meta = e5_lookup.loc[strategy] if strategy in e5_lookup.index else None
        rows.append(
            {
                "scenario": str(record["scenario"]),
                "source_pack": str(record["pack"]),
                "strategy": strategy,
                "strategy_label": STRATEGY_LABELS[strategy],
                "strategy_group": str(record["strategy_group"]),
                "k_used": k_used,
                "perturbation_space_size": space_size,
                "configuration_fraction": fraction,
                "configuration_fraction_pct": fraction * 100.0,
                "agreement_rate": float(record["agreement_rate"]),
                "clear_case_target_ci_width": (
                    float(e5_meta["adaptive_target_ci_width"])
                    if e5_meta is not None and pd.notna(e5_meta.get("adaptive_target_ci_width"))
                    else None
                ),
                "clear_case_stop_reason": (
                    str(e5_meta["adaptive_stop_reason"])
                    if e5_meta is not None and pd.notna(e5_meta.get("adaptive_stop_reason"))
                    else ""
                ),
            }
        )
    return pd.DataFrame(rows)


def _make_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy in STRATEGY_ORDER:
        clear = df[(df["strategy"] == strategy) & (df["scenario"] == "Clear cases")].iloc[0]
        boundary = df[(df["strategy"] == strategy) & (df["scenario"] == "Boundary cases")].iloc[0]
        clear_fraction = float(clear["configuration_fraction"])
        boundary_fraction = float(boundary["configuration_fraction"])
        rows.append(
            {
                "strategy": strategy,
                "strategy_label": STRATEGY_LABELS[strategy],
                "clear_case_k_used": int(clear["k_used"]),
                "clear_case_fraction_pct": round(clear_fraction * 100.0, 1),
                "clear_case_agreement_rate": float(clear["agreement_rate"]),
                "boundary_case_k_used": int(boundary["k_used"]),
                "boundary_case_fraction_pct": round(boundary_fraction * 100.0, 1),
                "boundary_case_agreement_rate": float(boundary["agreement_rate"]),
                "boundary_over_clear_ratio": round(
                    (boundary_fraction / clear_fraction) if clear_fraction else 0.0, 2
                ),
            }
        )
    return rows


def _plot_tradeoff(df: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    _set_style()
    fig, ax = plt.subplots(figsize=(8.6, 3.8), constrained_layout=False)
    fig.subplots_adjust(left=0.24, right=0.97, top=0.84, bottom=0.20)

    y = list(range(len(STRATEGY_ORDER)))
    bar_h = 0.34
    for offset, scenario in [(-bar_h / 2, "Clear cases"), (bar_h / 2, "Boundary cases")]:
        scenario_df = (
            df[df["scenario"] == scenario]
            .set_index("strategy")
            .reindex(STRATEGY_ORDER)
            .reset_index()
        )
        values = scenario_df["configuration_fraction"].astype(float).tolist()
        ax.barh(
            [v + offset for v in y],
            values,
            height=bar_h,
            color=SCENARIO_COLORS[scenario],
            edgecolor="white",
            linewidth=0.8,
            label=scenario,
            zorder=3,
        )
        for idx, row in scenario_df.iterrows():
            label = f'{int(row["k_used"])} ({row["configuration_fraction_pct"]:.1f}%)'
            ax.text(
                float(row["configuration_fraction"]) + 0.015,
                y[idx] + offset,
                label,
                va="center",
                ha="left",
                fontsize=9,
                color="#222222",
            )

    ax.set_yticks(y, [STRATEGY_LABELS[key] for key in STRATEGY_ORDER])
    ax.invert_yaxis()
    ax.set_xlabel("Evaluated configurations (% of full admissible space)")
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlim(0.0, 1.12)
    ax.grid(axis="x", color="#dddddd", linewidth=0.6)
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Boundary Claims Require Larger Evaluation Budgets", pad=10)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def _write_note(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    tuned = next(row for row in summary_rows if row["strategy"] == "adaptive_ci_tuned")
    adaptive = next(row for row in summary_rows if row["strategy"] == "adaptive_ci")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# RQ4 Interpretation: Practicality and Cost",
                "",
                "The current RQ4 evidence asks whether conservative claim-level validation is operationally usable, not whether it is always cheap.",
                "",
                "Key pattern:",
                f"- all current policy packs preserve full-factorial decisions (`agreement_rate = 1.0` throughout)",
                f"- adaptive CI tuned uses {tuned['clear_case_k_used']} configurations ({tuned['clear_case_fraction_pct']:.1f}%) on clear cases but {tuned['boundary_case_k_used']} ({tuned['boundary_case_fraction_pct']:.1f}%) on boundary cases",
                f"- adaptive CI uses {adaptive['clear_case_k_used']} configurations ({adaptive['clear_case_fraction_pct']:.1f}%) on clear cases but {adaptive['boundary_case_k_used']} ({adaptive['boundary_case_fraction_pct']:.1f}%) on boundary cases",
                "",
                "Safe paper-facing takeaway:",
                "Claim-level validation is practical for many clear cases, but difficult boundary cases consume substantially more of the admissible configuration budget. This is expected behavior for a conservative validation method.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    df = _load_dataset()
    dataset_rows = df.to_dict(orient="records")
    summary_rows = _make_summary(df)

    _write_csv(DERIVED_DIR / "practicality_tradeoff_dataset.csv", dataset_rows)
    _write_json(DERIVED_DIR / "practicality_tradeoff_dataset.json", dataset_rows)
    _write_csv(TABLE_DIR / "tab4_rq4_practicality_summary.csv", summary_rows)
    _plot_tradeoff(
        df,
        FIG_DIR / "fig4_cost_configuration_tradeoff.png",
        FIG_DIR / "fig4_cost_configuration_tradeoff.pdf",
    )
    _write_note(DERIVED_DIR / "practicality_interpretation.md", summary_rows)

    summary = {
        "schema_version": "rq4_practicality_icse_v1",
        "source_files": {
            "e5_policy_summary": str(E5_SUMMARY),
            "w5_policy_by_strategy": str(W5_SUMMARY),
        },
        "rows": {
            "dataset": len(dataset_rows),
            "summary": len(summary_rows),
        },
    }
    _write_json(DERIVED_DIR / "practicality_summary.json", summary)
    print("Wrote RQ4 ICSE outputs to", DERIVED_DIR)


if __name__ == "__main__":
    main()
