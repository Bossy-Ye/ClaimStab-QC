from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from claimstab.inference.status_remap import remap_status


REPO_ROOT = Path(__file__).resolve().parents[3]
ICSE_OUT_ROOT = REPO_ROOT / "output" / "paper" / "icse_pack"
V2_SOURCE = REPO_ROOT / "output" / "paper" / "internal_surface_v2" / "derived_paper_evaluation" / "RQ1_necessity" / "cross_family_metric_baselines_v2.csv"
LEGACY_SOURCE = REPO_ROOT / "output" / "paper" / "evaluation_v4" / "derived_paper_evaluation" / "RQ1_necessity" / "cross_family_metric_baselines.csv"

SCOPE_LABELS = {
    "compilation_only_exact": "Compilation",
    "sampling_only_exact": "Sampling",
    "combined_light_exact": "Combined",
}
SCOPE_ORDER = ["compilation_only_exact", "sampling_only_exact", "combined_light_exact"]
CLAIM_OUTCOME_ORDER = ["validated", "refuted", "unstable", "inconclusive"]
METRIC_VERDICT_ORDER = ["positive", "negative"]

LEGACY_METADATA = {
    "MaxCut QAOA": {
        "task_family": "combinatorial_optimization",
        "benchmark_family": "maxcut",
        "slice_class": "optimization",
        "role": "main",
        "metric": "objective",
        "source_table_bundle": "evaluation_v4",
        "source_experiment_bundle": "evaluation_v2",
    },
    "Max-2-SAT QAOA": {
        "task_family": "combinatorial_optimization",
        "benchmark_family": "max2sat",
        "slice_class": "optimization",
        "role": "main",
        "metric": "objective",
        "source_table_bundle": "evaluation_v4",
        "source_experiment_bundle": "evaluation_v3",
    },
    "VQE/H2": {
        "task_family": "quantum_chemistry",
        "benchmark_family": "h2_vqe_pilot",
        "slice_class": "chemistry",
        "role": "supporting",
        "metric": "energy_error",
        "source_table_bundle": "evaluation_v4",
        "source_experiment_bundle": "evaluation_v3",
    },
}


def _linkage_ids(claim_id: str | None = None) -> dict[str, str]:
    if claim_id is None:
        return {"cro_id": "__aggregate__", "drr_id": "__aggregate__", "oap_id": "__aggregate__"}
    return {"cro_id": claim_id, "drr_id": f"{claim_id}__drr", "oap_id": f"{claim_id}__oap"}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def _metric_verdict(flag: Any) -> str:
    return "positive" if bool(flag) else "negative"


def _false_reassurance_type(metric_verdict: str, claim_validation_outcome: str) -> str:
    if metric_verdict != "positive":
        return "none"
    if claim_validation_outcome == "refuted":
        return "metric_positive_claim_refuted"
    if claim_validation_outcome == "unstable":
        return "metric_positive_claim_unstable"
    if claim_validation_outcome == "inconclusive":
        return "metric_positive_claim_inconclusive"
    return "none"


def _support_alignment(metric_verdict: str, claim_validation_outcome: str) -> bool:
    return (metric_verdict == "positive") == (claim_validation_outcome == "validated")


def _claim_id(algorithm_family: str, claim_pair: str, scope: str, delta: float) -> str:
    return f"{algorithm_family}|{claim_pair}|{scope}|delta={delta:.2f}"


def _source_path() -> Path:
    return V2_SOURCE if V2_SOURCE.exists() else LEGACY_SOURCE


def _normalize_dataset(source_df: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in source_df.to_dict(orient="records"):
        family = str(record.get("family") or record.get("algorithm_family"))
        meta = LEGACY_METADATA.get(family, {})
        task_family = str(record.get("task_family") or meta.get("task_family") or "")
        benchmark_family = str(record.get("benchmark_family") or meta.get("benchmark_family") or family.lower().replace(" ", "_"))
        slice_class = str(record.get("slice_class") or meta.get("slice_class") or "main")
        role = str(record.get("role") or meta.get("role") or "main")
        metric = str(record.get("metric") or meta.get("metric") or "metric_value")
        source_table_bundle = str(record.get("source_table_bundle") or meta.get("source_table_bundle") or "internal_surface_v2")
        source_experiment_bundle = str(record.get("source_experiment_bundle") or meta.get("source_experiment_bundle") or "internal_surface_v2")
        scope = str(record["space_preset"])
        delta = float(record["delta"])
        claim_pair = str(record["claim_pair"])
        claim_id = _claim_id(family, claim_pair, scope, delta)
        metric_verdict = _metric_verdict(record["metric_supportive"])
        claim_validation_outcome = str(record["claim_validation_outcome"])
        claim_stability_verdict = str(record["claimstab_decision"])
        rows.append(
            {
                "claim_id": claim_id,
                **_linkage_ids(claim_id),
                "source_table_bundle": source_table_bundle,
                "source_experiment_bundle": source_experiment_bundle,
                "source_path": str(record.get("source_path") or source_path.resolve()),
                "source_run_root": str(record.get("source_run_root") or ""),
                "config_path": str(record.get("config_path") or ""),
                "task_family": task_family,
                "benchmark_family": benchmark_family,
                "slice_class": slice_class,
                "role": role,
                "algorithm_family": family,
                "claim_family": str(record.get("claim_family") or "ranking"),
                "run_id": str(record["run_id"]),
                "claim_pair": claim_pair,
                "scope": scope,
                "scope_label": SCOPE_LABELS.get(scope, scope),
                "delta": delta,
                "higher_is_better": bool(record["higher_is_better"]),
                "metric": metric,
                "metric_value": float(record["metric_mean_diff"]),
                "metric_verdict": metric_verdict,
                "metric_ci_lower": float(record["metric_ci_low"]),
                "metric_ci_upper": float(record["metric_ci_high"]),
                "baseline_claim_holds": bool(record["baseline_claim_holds"]) if not pd.isna(record["baseline_claim_holds"]) else None,
                "baseline_claim_holds_rate": float(record["baseline_claim_holds_rate"]) if not pd.isna(record["baseline_claim_holds_rate"]) else math.nan,
                "claim_holds_rate_mean": float(record["claim_holds_rate_mean"]) if not pd.isna(record["claim_holds_rate_mean"]) else math.nan,
                "claim_stability_verdict": claim_stability_verdict,
                "claim_validation_outcome": claim_validation_outcome,
                "reporting_status": remap_status(
                    raw_stability=claim_stability_verdict,
                    anchor_support=bool(record["baseline_claim_holds"]) if not pd.isna(record["baseline_claim_holds"]) else False,
                    has_stable_reverse=claim_validation_outcome == "refuted",
                    has_subregion_candidate=False,
                    subregion_valid=False,
                ),
                "s_hat": float(record["stability_hat"]),
                "claim_ci_lower": float(record["stability_ci_low"]),
                "claim_ci_upper": float(record["stability_ci_high"]),
                "false_reassurance_type": _false_reassurance_type(metric_verdict, claim_validation_outcome),
                "support_alignment": _support_alignment(metric_verdict, claim_validation_outcome),
            }
        )
    dataset = pd.DataFrame(rows)
    dataset = dataset.sort_values(
        by=["role", "slice_class", "algorithm_family", "scope", "claim_pair", "delta"],
        key=lambda series: series.map({name: idx for idx, name in enumerate(SCOPE_ORDER)}) if series.name == "scope" else series,
    ).reset_index(drop=True)
    return dataset


def _safe_rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _make_summary_row(group_kind: str, group: str, df: pd.DataFrame) -> dict[str, Any]:
    metric_positive = int((df["metric_verdict"] == "positive").sum())
    return {
        "group_kind": group_kind,
        "group": group,
        **_linkage_ids(),
        "n_total": int(len(df)),
        "metric_positive": metric_positive,
        "claim_validated": int((df["claim_validation_outcome"] == "validated").sum()),
        "claim_refuted": int((df["claim_validation_outcome"] == "refuted").sum()),
        "claim_unstable": int((df["claim_validation_outcome"] == "unstable").sum()),
        "claim_inconclusive": int((df["claim_validation_outcome"] == "inconclusive").sum()),
        "metric_positive_claim_validated": int(((df["metric_verdict"] == "positive") & (df["claim_validation_outcome"] == "validated")).sum()),
        "metric_positive_claim_refuted": int((df["false_reassurance_type"] == "metric_positive_claim_refuted").sum()),
        "metric_positive_claim_unstable": int((df["false_reassurance_type"] == "metric_positive_claim_unstable").sum()),
        "metric_positive_claim_inconclusive": int((df["false_reassurance_type"] == "metric_positive_claim_inconclusive").sum()),
        "metric_negative_claim_validated": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "validated")).sum()),
        "metric_negative_claim_refuted": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "refuted")).sum()),
        "metric_negative_claim_unstable": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "unstable")).sum()),
        "metric_negative_claim_inconclusive": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "inconclusive")).sum()),
        "conditional_false_reassurance_rate": _safe_rate(
            int((df["false_reassurance_type"] != "none").sum()),
            metric_positive,
        ),
        "support_alignment_rate": _safe_rate(int(df["support_alignment"].sum()), int(len(df))),
        "inconclusive_rate": _safe_rate(int((df["claim_validation_outcome"] == "inconclusive").sum()), int(len(df))),
    }


def _build_summary_tables(dataset: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows = [_make_summary_row("overall", "all", dataset)]
    for slice_class in sorted(dataset["slice_class"].astype(str).unique()):
        summary_rows.append(_make_summary_row("slice_class", slice_class, dataset[dataset["slice_class"] == slice_class]))
    for family in sorted(dataset["algorithm_family"].astype(str).unique()):
        summary_rows.append(_make_summary_row("algorithm_family", family, dataset[dataset["algorithm_family"] == family]))
    for scope in sorted(dataset["scope"].astype(str).unique(), key=lambda item: SCOPE_ORDER.index(item) if item in SCOPE_ORDER else 99):
        scope_df = dataset[dataset["scope"] == scope]
        if not scope_df.empty:
            summary_rows.append(_make_summary_row("scope", scope, scope_df))

    breakdown_rows: list[dict[str, Any]] = []
    for (family, scope, delta), group_df in dataset.groupby(["algorithm_family", "scope", "delta"], dropna=False):
        breakdown_rows.append(
            {
                "algorithm_family": family,
                **_linkage_ids(),
                "scope": scope,
                "scope_label": SCOPE_LABELS.get(scope, scope),
                "delta": float(delta),
                "n_total": int(len(group_df)),
                "metric_positive": int((group_df["metric_verdict"] == "positive").sum()),
                "claim_validated": int((group_df["claim_validation_outcome"] == "validated").sum()),
                "claim_refuted": int((group_df["claim_validation_outcome"] == "refuted").sum()),
                "claim_unstable": int((group_df["claim_validation_outcome"] == "unstable").sum()),
                "claim_inconclusive": int((group_df["claim_validation_outcome"] == "inconclusive").sum()),
                "metric_positive_claim_refuted": int((group_df["false_reassurance_type"] == "metric_positive_claim_refuted").sum()),
                "metric_positive_claim_unstable": int((group_df["false_reassurance_type"] == "metric_positive_claim_unstable").sum()),
                "metric_positive_claim_inconclusive": int((group_df["false_reassurance_type"] == "metric_positive_claim_inconclusive").sum()),
                "conditional_false_reassurance_rate": _safe_rate(
                    int((group_df["false_reassurance_type"] != "none").sum()),
                    int((group_df["metric_verdict"] == "positive").sum()),
                ),
            }
        )
    breakdown_rows.sort(key=lambda row: (str(row["algorithm_family"]), SCOPE_ORDER.index(str(row["scope"])) if str(row["scope"]) in SCOPE_ORDER else 99, float(row["delta"])))
    return summary_rows, breakdown_rows


def _curate_family_breakdown(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in sorted(dataset["algorithm_family"].astype(str).unique()):
        group_df = dataset[dataset["algorithm_family"] == family]
        summary = _make_summary_row("algorithm_family", family, group_df)
        rows.append(
            {
                "algorithm_family": family,
                "slice_class": str(group_df["slice_class"].iloc[0]),
                "benchmark_family": str(group_df["benchmark_family"].iloc[0]),
                **_linkage_ids(),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": int((group_df["false_reassurance_type"] != "none").sum()),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
                "support_alignment_rate": summary["support_alignment_rate"],
            }
        )
    return rows


def _curate_scope_breakdown(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope in sorted(dataset["scope"].astype(str).unique(), key=lambda item: SCOPE_ORDER.index(item) if item in SCOPE_ORDER else 99):
        group_df = dataset[dataset["scope"] == scope]
        summary = _make_summary_row("scope", scope, group_df)
        rows.append(
            {
                "scope": scope,
                **_linkage_ids(),
                "scope_label": SCOPE_LABELS.get(scope, scope),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": int((group_df["false_reassurance_type"] != "none").sum()),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
                "support_alignment_rate": summary["support_alignment_rate"],
            }
        )
    return rows


def _curate_delta_breakdown(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for delta in sorted(dataset["delta"].astype(float).unique()):
        group_df = dataset[dataset["delta"] == delta]
        summary = _make_summary_row("delta", f"{delta:.2f}", group_df)
        rows.append(
            {
                "delta": float(delta),
                **_linkage_ids(),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": int((group_df["false_reassurance_type"] != "none").sum()),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
                "support_alignment_rate": summary["support_alignment_rate"],
            }
        )
    return rows


def _curate_primary_family_sensitivity(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    slices = [
        ("all_main_families", "All main families", dataset),
        ("optimization_only", "Optimization only", dataset[dataset["slice_class"] == "optimization"]),
        ("software_stack_only", "Software stack only", dataset[dataset["slice_class"] == "software_stack"]),
    ]
    rows: list[dict[str, Any]] = []
    for slice_key, label, group_df in slices:
        summary = _make_summary_row("sensitivity", slice_key, group_df)
        rows.append(
            {
                "analysis_slice": slice_key,
                **_linkage_ids(),
                "label": label,
                "included_families": ", ".join(sorted(group_df["algorithm_family"].astype(str).unique().tolist())),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": int((group_df["false_reassurance_type"] != "none").sum()),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
            }
        )
    return rows


def _curate_leave_one_family_out(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    families = sorted(dataset["algorithm_family"].astype(str).unique().tolist())
    for family in families:
        group_df = dataset[dataset["algorithm_family"] != family]
        summary = _make_summary_row("leave_one_out", family, group_df)
        rows.append(
            {
                "excluded_family": family,
                **_linkage_ids(),
                "included_families": ", ".join(sorted(group_df["algorithm_family"].astype(str).unique().tolist())),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": int((group_df["false_reassurance_type"] != "none").sum()),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
            }
        )
    return rows


def _build_main_paper_structural_table(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add_row(dimension: str, slice_label: str, frame: pd.DataFrame) -> None:
        summary = _make_summary_row(dimension.lower(), slice_label, frame)
        rows.append(
            {
                "dimension": dimension,
                "slice": slice_label,
                **_linkage_ids(),
                "metric_positive": int(summary["metric_positive"]),
                "false_reassurance": int((frame["false_reassurance_type"] != "none").sum()),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
            }
        )

    add_row("Overall", "All main variants", dataset)
    for slice_class in sorted(dataset["slice_class"].astype(str).unique()):
        add_row("Slice", slice_class, dataset[dataset["slice_class"] == slice_class])
    for family in sorted(dataset["algorithm_family"].astype(str).unique()):
        add_row("Family", family, dataset[dataset["algorithm_family"] == family])
    for scope in sorted(dataset["scope"].astype(str).unique(), key=lambda item: SCOPE_ORDER.index(item) if item in SCOPE_ORDER else 99):
        add_row("Scope", scope, dataset[dataset["scope"] == scope])
    for delta in sorted(dataset["delta"].astype(float).unique()):
        add_row("Delta", f"{float(delta):.2f}", dataset[dataset["delta"] == delta])
    return rows


def _render_discrepancy_matrix(dataset: pd.DataFrame, out_png: Path, out_pdf: Path) -> dict[str, Any]:
    total = len(dataset)
    matrix_counts: dict[tuple[str, str], int] = {}
    values: list[list[float]] = []
    for metric in METRIC_VERDICT_ORDER:
        row_values: list[float] = []
        for claim in CLAIM_OUTCOME_ORDER:
            count = int(((dataset["metric_verdict"] == metric) & (dataset["claim_validation_outcome"] == claim)).sum())
            matrix_counts[(metric, claim)] = count
            row_values.append(float(count / total) if total else 0.0)
        values.append(row_values)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 11,
        }
    )
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    vmax = max((max(row) for row in values), default=1.0)
    ax.imshow(values, cmap="Greys", vmin=0.0, vmax=vmax or 1.0, aspect="auto")
    for row_idx, metric in enumerate(METRIC_VERDICT_ORDER):
        for col_idx, claim in enumerate(CLAIM_OUTCOME_ORDER):
            count = matrix_counts[(metric, claim)]
            share = 100.0 * count / total if total else 0.0
            cell_value = values[row_idx][col_idx]
            ax.text(
                col_idx,
                row_idx,
                f"{count}\n({share:.1f}%)",
                ha="center",
                va="center",
                fontsize=10,
                color="white" if cell_value >= 0.22 else "#111111",
            )
    ax.set_xticks(range(len(CLAIM_OUTCOME_ORDER)))
    ax.set_xticklabels(["Validated", "Refuted", "Unstable", "Inconclusive"])
    ax.set_yticks(range(len(METRIC_VERDICT_ORDER)))
    ax.set_yticklabels(["Metric positive", "Metric negative"])
    ax.set_xlabel("Claim validation outcome")
    ax.set_ylabel("Metric verdict")
    ax.set_xticks([x - 0.5 for x in range(1, len(CLAIM_OUTCOME_ORDER))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(METRIC_VERDICT_ORDER))], minor=True)
    ax.grid(which="minor", color="white", linewidth=2.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    return {
        "matrix_counts": {
            metric: {claim: matrix_counts[(metric, claim)] for claim in CLAIM_OUTCOME_ORDER}
            for metric in METRIC_VERDICT_ORDER
        },
        "figure_png": str(out_png.resolve()),
        "figure_pdf": str(out_pdf.resolve()),
    }


def _write_interpretation_note(path: Path, dataset: pd.DataFrame, summary_rows: list[dict[str, Any]]) -> None:
    overall = next(row for row in summary_rows if row["group_kind"] == "overall")
    slice_rows = [row for row in summary_rows if row["group_kind"] == "slice_class"]
    lines = [
        "# RQ1 Metric vs Claim Interpretation",
        "",
        f"Across {overall['n_total']} strengthened internal main-surface variants, {overall['metric_positive']} are metric-positive.",
        (
            f"Among metric-positive variants, {overall['metric_positive_claim_refuted']} are refuted, "
            f"{overall['metric_positive_claim_unstable']} are unstable, and "
            f"{overall['metric_positive_claim_inconclusive']} are inconclusive."
        ),
        "",
        "## Slice breakdown",
        "",
    ]
    for row in slice_rows:
        rate = row["conditional_false_reassurance_rate"]
        rate_text = "n/a" if rate is None else f"{100.0 * float(rate):.1f}%"
        lines.append(
            f"- {row['group']}: n={row['n_total']} | metric_positive={row['metric_positive']} | "
            f"non_validated_metric_positive={row['metric_positive_claim_refuted'] + row['metric_positive_claim_unstable'] + row['metric_positive_claim_inconclusive']} | "
            f"conditional_false_reassurance={rate_text}"
        )
    lines.extend(
        [
            "",
            f"Primary strengthened source: `{_source_path()}`",
            "- chemistry is retained separately as supporting and is not part of this denominator.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export RQ1 metric-vs-claim artifacts for the strengthened internal surface.")
    parser.add_argument("--out-root", type=Path, default=ICSE_OUT_ROOT)
    args = parser.parse_args()

    source_path = _source_path()
    source_df = pd.read_csv(source_path)
    dataset = _normalize_dataset(source_df, source_path)

    derived_dir = args.out_root / "derived" / "RQ1"
    tables_dir = args.out_root / "tables"
    figures_dir = args.out_root / "figures" / "main"

    dataset_csv = derived_dir / "metric_claim_comparison_dataset.csv"
    dataset.to_csv(dataset_csv, index=False)
    _write_json(
        derived_dir / "metric_claim_comparison_dataset.json",
        {
            "meta": {
                "source_table": str(source_path.resolve()),
                "n_rows": int(len(dataset)),
                "roles": sorted(dataset["role"].astype(str).unique().tolist()),
                "slice_classes": sorted(dataset["slice_class"].astype(str).unique().tolist()),
            },
            "rows": dataset.to_dict(orient="records"),
        },
    )

    summary_rows, breakdown_rows = _build_summary_tables(dataset)
    _write_csv(tables_dir / "tab_mismatch_summary.csv", summary_rows)
    _write_csv(tables_dir / "tab_false_reassurance_breakdown.csv", breakdown_rows)
    _write_csv(tables_dir / "tab_rq1_family_breakdown.csv", _curate_family_breakdown(dataset))
    _write_csv(tables_dir / "tab_rq1_scope_breakdown.csv", _curate_scope_breakdown(dataset))
    _write_csv(tables_dir / "tab_rq1_delta_breakdown.csv", _curate_delta_breakdown(dataset))
    _write_csv(tables_dir / "tab_rq1_primary_family_sensitivity.csv", _curate_primary_family_sensitivity(dataset))
    _write_csv(tables_dir / "tab_rq1_leave_one_family_out_sensitivity.csv", _curate_leave_one_family_out(dataset))
    _write_csv(tables_dir / "tab1_rq1_structural_breakdown.csv", _build_main_paper_structural_table(dataset))

    figure_meta = _render_discrepancy_matrix(
        dataset,
        figures_dir / "fig1_metric_claim_discrepancy_matrix.png",
        figures_dir / "fig1_metric_claim_discrepancy_matrix.pdf",
    )
    _write_interpretation_note(derived_dir / "metric_claim_interpretation.md", dataset, summary_rows)
    _write_json(
        derived_dir / "metric_claim_comparison_summary.json",
        {
            "dataset_csv": str(dataset_csv.resolve()),
            "source_table": str(source_path.resolve()),
            "overall": next(row for row in summary_rows if row["group_kind"] == "overall"),
            "figure": figure_meta,
        },
    )

    print(f"dataset_rows = {len(dataset)}")
    print(f"slice_classes = {sorted(dataset['slice_class'].astype(str).unique().tolist())}")


if __name__ == "__main__":
    main()
