from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_CSV = (
    REPO_ROOT
    / "output"
    / "paper"
    / "evaluation_v4"
    / "derived_paper_evaluation"
    / "RQ2_semantics"
    / "scope_robustness.csv"
)

SCOPE_ORDER = ["Compilation", "Sampling", "Combined"]
VERDICT_TO_VALUE = {
    "inconclusive": 0,
    "unstable": 1,
    "stable": 2,
}
VALUE_TO_LABEL = {
    -1: "",
    0: "inconclusive",
    1: "unstable",
    2: "stable",
}
TRANSPORT_LABELS = {
    "stable_transport": "robustly stable",
    "unstable_transport": "robustly unstable",
    "scope_flip": "boundary-sensitive",
    "abstention_under_scope_change": "abstention-sensitive",
}

CLAIM_PAIR_DISPLAY = {
    "GHZ_Linear>GHZ_Star": "GHZ Linear > GHZ Star",
    "QAOA_p2>QAOA_p1": "QAOA p2 > QAOA p1",
    "VQE_HEA>VQE_HF": "VQE HEA > VQE HF",
}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _display_claim_pair(claim_pair: str) -> str:
    return CLAIM_PAIR_DISPLAY.get(claim_pair, claim_pair.replace("_", " "))


def _write_note(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# RQ3 Scope Robustness Interpretation",
        "",
        "This artifact reuses the existing three-case scope-robustness audit and presents it as a transport-oriented summary.",
        "",
        "## Headline",
        "",
        "- explicit admissible scope matters, but the effect is structured rather than arbitrary",
        "- clear stable claims can transport as stable across nearby scope variants",
        "- clear unstable claims can remain unstable across nearby scope variants",
        "- near-boundary claims can flip when the declared scope broadens",
        "",
        "## Case summary",
        "",
    ]
    for row in summary_rows:
        lines.append(
            f"- {row['label']}: {row['transport_class_label']} across {row['scope_variants_tested']} tested scope variants "
            f"({row['decisions_sequence']})."
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- ClaimStab-QC does not hide admissibility choices; it makes scope dependence explicit and inspectable",
            "- transport classes distinguish robust cases from boundary-sensitive ones",
            "- scope sensitivity should be reported as methodological evidence, not treated as an implementation nuisance",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered_cases = frame["case_id"].drop_duplicates().tolist()
    for case_id in ordered_cases:
        case = frame[frame["case_id"] == case_id].copy()
        transport = str(case["scope_transport"].iloc[0])
        scope_values: dict[str, dict[str, Any]] = {}
        for scope_label in SCOPE_ORDER:
            scope_case = case[case["scope_label"] == scope_label]
            if scope_case.empty:
                scope_values[scope_label] = {"decision": "", "stability_hat": None}
            else:
                scope_values[scope_label] = {
                    "decision": str(scope_case["decision"].iloc[0]),
                    "stability_hat": float(scope_case["stability_hat"].iloc[0]),
                }
        rows.append(
            {
                "case_id": case_id,
                "label": str(case["label"].iloc[0]),
                "source_run": str(case["source_run"].iloc[0]),
                "claim_pair": str(case["claim_pair"].iloc[0]),
                "delta": float(case["delta"].iloc[0]),
                "scope_variants_tested": int(len(case)),
                "tested_scopes": " | ".join(case["scope_label"].tolist()),
                "decisions_sequence": " | ".join(case["decision"].tolist()),
                "transport_class": transport,
                "transport_class_label": TRANSPORT_LABELS[transport],
                "paper_role": {
                    "stable_transport": "robust stable case",
                    "unstable_transport": "robust unstable case",
                    "scope_flip": "boundary-sensitive case",
                    "abstention_under_scope_change": "abstention-sensitive case",
                }[transport],
                "compilation_decision": scope_values["Compilation"]["decision"],
                "compilation_stability_hat": scope_values["Compilation"]["stability_hat"],
                "sampling_decision": scope_values["Sampling"]["decision"],
                "sampling_stability_hat": scope_values["Sampling"]["stability_hat"],
                "combined_decision": scope_values["Combined"]["decision"],
                "combined_stability_hat": scope_values["Combined"]["stability_hat"],
            }
        )
    return rows


def _render_transport_map(frame: pd.DataFrame, summary_rows: list[dict[str, Any]], out_png: Path, out_pdf: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )

    case_title_map = {
        "clear_stable": "Robust stable",
        "clear_unstable": "Robust unstable",
        "near_boundary": "Boundary-sensitive",
    }
    decision_colors = {
        "stable": "#365c4a",
        "unstable": "#9f3d2f",
        "inconclusive": "#8a7d68",
    }

    plot_rows: list[dict[str, Any]] = []
    group_midpoints: list[tuple[float, str, str]] = []
    sampling_note_y: float | None = None
    y_cursor = 8.0
    for row in summary_rows:
        case_id = str(row["case_id"])
        case = frame[frame["case_id"] == case_id].copy()
        case["scope_order"] = case["scope_label"].map({scope: idx for idx, scope in enumerate(SCOPE_ORDER)})
        case = case.sort_values("scope_order")
        group_y_positions: list[float] = []
        for _, case_row in case.iterrows():
            plot_rows.append(
                {
                    "y": y_cursor,
                    "case_id": case_id,
                    "scope_label": str(case_row["scope_label"]),
                    "stability_hat": float(case_row["stability_hat"]),
                    "stability_ci_low": float(case_row["stability_ci_low"]),
                    "stability_ci_high": float(case_row["stability_ci_high"]),
                    "decision": str(case_row["decision"]),
                }
            )
            if case_id == "clear_unstable" and str(case_row["scope_label"]) == "Sampling":
                sampling_note_y = y_cursor
            group_y_positions.append(y_cursor)
            y_cursor -= 1.0
        group_midpoints.append(
            (
                float(np.mean(group_y_positions)),
                case_title_map[case_id],
                _display_claim_pair(str(row["claim_pair"])),
            )
        )
        y_cursor -= 0.7

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    tau = 0.95
    ax.axvline(tau, color="#444444", linestyle="--", linewidth=1.1)
    ax.text(tau, 8.7, "τ = .95", ha="center", va="bottom", fontsize=9.5, color="#444444")

    for record in plot_rows:
        lower_err = record["stability_hat"] - record["stability_ci_low"]
        upper_err = record["stability_ci_high"] - record["stability_hat"]
        color = decision_colors[record["decision"]]
        ax.errorbar(
            record["stability_hat"],
            record["y"],
            xerr=[[lower_err], [upper_err]],
            fmt="o",
            color=color,
            ecolor="#333333",
            elinewidth=1.2,
            capsize=3.0,
            markersize=5.8,
            zorder=3,
        )
        label_x = min(record["stability_hat"] + 0.02, 1.01)
        ax.text(
            label_x,
            record["y"],
            f"ŝ={record['stability_hat']:.2f}",
            ha="left",
            va="center",
            fontsize=9.0,
            color=color,
        )

    ax.set_xlim(0.50, 1.04)
    ax.set_ylim(0.2, 8.9)
    ax.set_xlabel("Preservation rate")
    y_tick_labels: list[str] = []
    for row in plot_rows:
        label = row["scope_label"]
        if row["case_id"] == "clear_unstable" and label == "Sampling":
            label = "Sampling†"
        y_tick_labels.append(label)
    ax.set_yticks([row["y"] for row in plot_rows], labels=y_tick_labels)
    ax.grid(axis="x", color="#dddddd", linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    for midpoint, case_title, claim_pair in group_midpoints:
        ax.text(
            0.505,
            midpoint + 0.28,
            case_title,
            ha="left",
            va="center",
            fontsize=11.5,
            fontweight="bold",
            color="#222222",
        )
        ax.text(
            0.505,
            midpoint - 0.18,
            claim_pair.replace(">", " > "),
            ha="left",
            va="center",
            fontsize=9.2,
            color="#555555",
        )

    if sampling_note_y is not None:
        ax.text(
            0.505,
            sampling_note_y - 0.42,
            "† only representative case with a sampling-only preset",
            ha="left",
            va="center",
            fontsize=8.6,
            color="#555555",
        )
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ICSE scope-robustness pack.")
    parser.add_argument(
        "--out-root",
        type=Path,
        default=REPO_ROOT / "output" / "paper" / "icse_pack",
        help="Output root for the ICSE pack.",
    )
    args = parser.parse_args()

    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Expected scope-robustness source at {SOURCE_CSV}")

    out_root = args.out_root
    derived_dir = out_root / "derived" / "RQ3"
    tables_dir = out_root / "tables"
    figures_dir = out_root / "figures" / "main"

    frame = pd.read_csv(SOURCE_CSV)
    summary_rows = _summary_rows(frame)

    _write_csv(derived_dir / "scope_transport_dataset.csv", frame.to_dict(orient="records"))
    _write_json(
        derived_dir / "scope_transport_dataset.json",
        {"source_csv": str(SOURCE_CSV.resolve()), "rows": frame.to_dict(orient="records")},
    )
    _write_csv(tables_dir / "tab_rq3_scope_transport_summary.csv", summary_rows)
    _render_transport_map(
        frame,
        summary_rows,
        figures_dir / "fig4_scope_transport_map.png",
        figures_dir / "fig4_scope_transport_map.pdf",
    )
    _write_note(derived_dir / "scope_transport_interpretation.md", summary_rows)
    _write_json(
        derived_dir / "scope_transport_summary.json",
        {
            "dataset_csv": str((derived_dir / "scope_transport_dataset.csv").resolve()),
            "summary_table_csv": str((tables_dir / "tab_rq3_scope_transport_summary.csv").resolve()),
            "figure_png": str((figures_dir / "fig4_scope_transport_map.png").resolve()),
            "figure_pdf": str((figures_dir / "fig4_scope_transport_map.pdf").resolve()),
        },
    )


if __name__ == "__main__":
    main()
