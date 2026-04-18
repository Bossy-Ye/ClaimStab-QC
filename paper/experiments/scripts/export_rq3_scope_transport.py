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
from matplotlib.colors import ListedColormap


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
    short_case_labels = {
        "clear_stable": "Clear stable",
        "clear_unstable": "Clear unstable",
        "near_boundary": "Near-boundary",
    }
    case_labels = [short_case_labels.get(str(row["case_id"]), str(row["label"])) for row in summary_rows]
    matrix = np.full((len(case_labels), len(SCOPE_ORDER)), -1, dtype=int)
    for i, row in enumerate(summary_rows):
        case = frame[frame["case_id"] == row["case_id"]]
        for _, case_row in case.iterrows():
            scope = str(case_row["scope_label"])
            if scope not in SCOPE_ORDER:
                continue
            j = SCOPE_ORDER.index(scope)
            decision = str(case_row["decision"])
            matrix[i, j] = VERDICT_TO_VALUE[decision]

    cmap = ListedColormap(["#7f7f7f", "#b7b7b7", "#4a4a4a", "#ededed"])
    display_matrix = matrix.copy()
    display_matrix = np.where(display_matrix == -1, 3, display_matrix)

    plt.rcParams.update(
        {
            "font.family": ["Times New Roman", "Times", "serif"],
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 12,
            "axes.titlesize": 16,
            "axes.labelsize": 12,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
        }
    )

    fig, ax = plt.subplots(figsize=(8.8, 3.4))
    ax.imshow(display_matrix, cmap=cmap, aspect="auto", vmin=0, vmax=3)
    ax.set_xticks(range(len(SCOPE_ORDER)), labels=["Compilation", "Sampling", "Combined"])
    ax.set_yticks(range(len(case_labels)), labels=["Stable claim", "Unstable claim", "Boundary claim"])
    ax.set_title("Scope Transport")
    ax.set_ylabel("Representative claim")

    ax.set_xticks(np.arange(-0.5, len(SCOPE_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(case_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)

    fig.text(
        0.5,
        0.96,
        "Claim stability across admissible perturbation scopes",
        ha="center",
        va="center",
        fontsize=11,
        color="#555555",
    )
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color="#4a4a4a"),
        plt.Rectangle((0, 0), 1, 1, color="#b7b7b7"),
        plt.Rectangle((0, 0), 1, 1, color="#7f7f7f"),
        plt.Rectangle((0, 0), 1, 1, color="#ededed"),
    ]
    ax.legend(
        legend_handles,
        ["Stable", "Unstable", "Inconclusive", "Not tested"],
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        ncol=1,
        frameon=False,
        fontsize=9.0,
    )
    fig.tight_layout(rect=(0.0, 0.0, 0.84, 0.9))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=240)
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
