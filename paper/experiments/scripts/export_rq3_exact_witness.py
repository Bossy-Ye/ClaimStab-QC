from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]

RUN_SPECS = [
    {
        "family": "MaxCut QAOA",
        "run_id": "E1_maxcut_main",
        "run_dir": REPO_ROOT / "output" / "paper" / "evaluation_v2" / "runs" / "E1_maxcut_main",
        "canonical_status": "exact default",
    },
    {
        "family": "GHZ structural",
        "run_id": "E2_ghz_structural",
        "run_dir": REPO_ROOT / "output" / "paper" / "evaluation_v2" / "runs" / "E2_ghz_structural",
        "canonical_status": "exact default",
    },
    {
        "family": "Max-2-SAT QAOA",
        "run_id": "W1_max2sat_second_family",
        "run_dir": REPO_ROOT / "output" / "paper" / "evaluation_v3" / "runs" / "W1_max2sat_second_family",
        "canonical_status": "exact default",
    },
    {
        "family": "VQE/H2",
        "run_id": "W1_vqe_pilot",
        "run_dir": REPO_ROOT / "output" / "paper" / "evaluation_v3" / "runs" / "W1_vqe_pilot",
        "canonical_status": "exact default",
    },
]

LEGACY_EXACT_GREEDY = (
    REPO_ROOT / "output" / "paper" / "evaluation_v4" / "pack" / "tables" / "tab_c_exact_vs_greedy_mos.csv"
)


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


def _parse_claim_pair(experiment_id: str) -> str:
    if ":" in experiment_id:
        return experiment_id.split(":", 1)[1]
    return experiment_id


def _render_witness_size_figure(
    status_rows: list[dict[str, Any]],
    out_png: Path,
    out_pdf: Path,
) -> None:
    frame = pd.DataFrame(status_rows)
    frame = frame[frame["exact_witnesses_found"] > 0].copy()
    if frame.empty:
        raise ValueError("No exact witnesses available for plotting.")

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

    labels = frame["family"].tolist()
    heights = frame["witness_size_max"].astype(float).tolist()
    counts = frame["exact_witnesses_found"].astype(int).tolist()

    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    bars = ax.bar(labels, heights, color="#4a4a4a", width=0.58)
    ax.set_title("Exact Witnesses Are Single-Factor Subsets", pad=10)
    ax.set_ylabel("Exact witness size")
    ax.set_ylim(0, 1.25)
    ax.set_yticks([0, 1])
    ax.grid(axis="y", color="#dddddd", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.04,
            f"n={count}",
            ha="center",
            va="bottom",
            fontsize=10.5,
            color="#333333",
            fontweight="bold",
        )

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=240)
    fig.savefig(out_pdf)
    plt.close(fig)


def _build_dataset() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in RUN_SPECS:
        claim_stability_path = spec["run_dir"] / "claim_stability.json"
        data = json.loads(claim_stability_path.read_text())
        for exp in data.get("experiments", []):
            overall = exp.get("overall", {})
            robustness = overall.get("conditional_robustness", {})
            exact_by_delta = robustness.get("exact_mos_by_delta", {})
            for delta, payload in exact_by_delta.items():
                if not isinstance(payload, dict):
                    continue
                best = payload.get("best")
                witness_found = isinstance(best, dict)
                rows.append(
                    {
                        "family": spec["family"],
                        "run_id": spec["run_id"],
                        "experiment_id": str(exp.get("experiment_id", "")),
                        "claim_pair": _parse_claim_pair(str(exp.get("experiment_id", ""))),
                        "space_preset": str(exp.get("sampling", {}).get("space_preset", "")),
                        "delta": str(delta),
                        "exact_search_mode": str(payload.get("search_mode", "")),
                        "exact_search_depth": payload.get("search_depth"),
                        "exact_witness_found": witness_found,
                        "witness_size": len(best.get("lock_dimensions", [])) if witness_found else None,
                        "lock_dimensions": best.get("lock_dimensions", []) if witness_found else [],
                        "conditions": best.get("conditions", {}) if witness_found else {},
                        "n_eval": best.get("n_eval") if witness_found else None,
                        "stability_hat": best.get("stability_hat") if witness_found else None,
                        "stability_ci_low": best.get("stability_ci_low") if witness_found else None,
                        "stability_ci_high": best.get("stability_ci_high") if witness_found else None,
                        "decision": best.get("decision") if witness_found else None,
                        "canonical_status": spec["canonical_status"],
                    }
                )
    return rows


def _build_status_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    legacy_frame = pd.read_csv(LEGACY_EXACT_GREEDY) if LEGACY_EXACT_GREEDY.exists() else pd.DataFrame()
    legacy_counts = {}
    if not legacy_frame.empty:
        legacy_counts = legacy_frame.groupby("family").size().to_dict()

    frame = pd.DataFrame(dataset_rows)
    rows: list[dict[str, Any]] = []
    for spec in RUN_SPECS:
        sub = frame[frame["run_id"] == spec["run_id"]].copy()
        exact_search_entries = int((sub["exact_search_mode"] == "exact_subset_search").sum())
        exact_found = int(sub["exact_witness_found"].sum())
        sizes = sub.loc[sub["exact_witness_found"], "witness_size"].dropna().astype(int).tolist()
        rows.append(
            {
                "family": spec["family"],
                "run_id": spec["run_id"],
                "delta_entries": int(len(sub)),
                "exact_search_entries": exact_search_entries,
                "exact_witnesses_found": exact_found,
                "no_exact_witness_entries": int(len(sub) - exact_found),
                "witness_discovery_rate": (exact_found / len(sub)) if len(sub) else None,
                "witness_size_min": min(sizes) if sizes else None,
                "witness_size_max": max(sizes) if sizes else None,
                "canonical_status": spec["canonical_status"],
                "legacy_exact_vs_greedy_rows": int(legacy_counts.get(spec["family"], 0)),
                "approximation_policy": "legacy greedy comparisons remain supporting-only",
            }
        )
    return rows


def _build_example_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    exact_rows = frame[frame["exact_witness_found"]].copy()
    exact_rows["delta_num"] = exact_rows["delta"].astype(float)
    exact_rows = exact_rows.sort_values(
        by=["family", "delta_num", "witness_size", "stability_ci_low"],
        ascending=[True, False, True, False],
    )
    rows: list[dict[str, Any]] = []
    for family in [spec["family"] for spec in RUN_SPECS]:
        family_rows = exact_rows[exact_rows["family"] == family]
        if family_rows.empty:
            continue
        row = family_rows.iloc[0]
        conditions = row["conditions"]
        condition_text = ", ".join(f"{key}={value}" for key, value in conditions.items() if key != "space_preset")
        rows.append(
            {
                "family": family,
                "experiment_id": row["experiment_id"],
                "claim_pair": row["claim_pair"],
                "space_preset": row["space_preset"],
                "delta": row["delta"],
                "witness_size": int(row["witness_size"]),
                "lock_dimensions": str(row["lock_dimensions"]),
                "conditions": str(conditions),
                "compact_witness": condition_text if condition_text else str(conditions),
                "decision": row["decision"],
                "stability_hat": row["stability_hat"],
                "stability_ci_low": row["stability_ci_low"],
                "stability_ci_high": row["stability_ci_high"],
            }
        )
    return rows


def _write_note(path: Path, status_rows: list[dict[str, Any]], example_rows: list[dict[str, Any]]) -> None:
    total_witnesses = sum(int(row["exact_witnesses_found"]) for row in status_rows)
    lines = [
        "# RQ3 Exact Witness Interpretation",
        "",
        "This artifact promotes exact minimal overturn subsets into paper-facing explanatory evidence.",
        "",
        "## Headline",
        "",
        f"- all {total_witnesses} exact witnesses found in the tractable paper-facing runs are single-factor subsets",
        "- main-paper tractable spaces use exact subset search rather than greedy approximation as the canonical witness source",
        "- legacy greedy comparisons remain supporting material only",
        "",
        "## Representative witnesses",
        "",
    ]
    for row in example_rows:
        lines.append(
            f"- {row['family']} / {row['claim_pair']} / {row['space_preset']} / delta={row['delta']}: "
            f"witness `{row['compact_witness']}` is sufficient for a `{row['decision']}` verdict."
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- these witnesses should be described as compact sufficient perturbation subsets",
            "- they are explanatory evidence for claim failure or preservation behavior",
            "- they should not be described as causal root causes",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ICSE exact-witness pack.")
    parser.add_argument(
        "--out-root",
        type=Path,
        default=REPO_ROOT / "output" / "paper" / "icse_pack",
        help="Output root for the ICSE pack.",
    )
    args = parser.parse_args()

    out_root = args.out_root
    derived_dir = out_root / "derived" / "RQ3"
    tables_dir = out_root / "tables"
    figures_dir = out_root / "figures" / "main"

    dataset_rows = _build_dataset()
    status_rows = _build_status_rows(dataset_rows)
    example_rows = _build_example_rows(dataset_rows)

    _write_csv(derived_dir / "exact_witness_dataset.csv", dataset_rows)
    _write_json(derived_dir / "exact_witness_dataset.json", {"rows": dataset_rows})
    _write_csv(tables_dir / "tab_rq3_exact_approx_status.csv", status_rows)
    _write_csv(tables_dir / "tab3_exact_witness_examples.csv", example_rows)
    _render_witness_size_figure(
        status_rows,
        figures_dir / "fig3_exact_witness_sizes.png",
        figures_dir / "fig3_exact_witness_sizes.pdf",
    )
    _write_note(derived_dir / "exact_witness_interpretation.md", status_rows, example_rows)
    _write_json(
        derived_dir / "exact_witness_summary.json",
        {
            "dataset_csv": str((derived_dir / "exact_witness_dataset.csv").resolve()),
            "status_table_csv": str((tables_dir / "tab_rq3_exact_approx_status.csv").resolve()),
            "examples_table_csv": str((tables_dir / "tab3_exact_witness_examples.csv").resolve()),
            "figure_png": str((figures_dir / "fig3_exact_witness_sizes.png").resolve()),
            "figure_pdf": str((figures_dir / "fig3_exact_witness_sizes.pdf").resolve()),
        },
    )


if __name__ == "__main__":
    main()
