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
from matplotlib.patches import Rectangle
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
RQ1_SOURCE = REPO_ROOT / "output" / "paper" / "evaluation_v4" / "derived_paper_evaluation" / "RQ1_necessity" / "cross_family_metric_baselines.csv"
E1_REFERENCE = REPO_ROOT / "output" / "paper" / "evaluation_v3" / "derived_paper_evaluation" / "RQ1_necessity" / "e1_metric_matched_scope_table.csv"

SCOPE_LABELS = {
    "compilation_only_exact": "Compilation",
    "sampling_only_exact": "Sampling",
    "combined_light_exact": "Combined",
}
SCOPE_ORDER = ["compilation_only_exact", "sampling_only_exact", "combined_light_exact"]
CLAIM_OUTCOME_ORDER = ["validated", "refuted", "unstable", "inconclusive"]
METRIC_VERDICT_ORDER = ["positive", "negative"]

FAMILY_METADATA = {
    "MaxCut QAOA": {
        "task_family": "combinatorial_optimization",
        "algorithm_family": "MaxCut QAOA",
        "source_table_bundle": "evaluation_v4",
        "source_experiment_bundle": "evaluation_v2",
    },
    "Max-2-SAT QAOA": {
        "task_family": "combinatorial_optimization",
        "algorithm_family": "Max-2-SAT QAOA",
        "source_table_bundle": "evaluation_v4",
        "source_experiment_bundle": "evaluation_v3",
    },
    "VQE/H2": {
        "task_family": "quantum_chemistry",
        "algorithm_family": "VQE/H2",
        "source_table_bundle": "evaluation_v4",
        "source_experiment_bundle": "evaluation_v3",
    },
}


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


def _safe_rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    return bool(value)


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
    claim_supportive = claim_validation_outcome == "validated"
    metric_supportive = metric_verdict == "positive"
    return claim_supportive == metric_supportive


def _claim_id(algorithm_family: str, claim_pair: str, scope: str, delta: float) -> str:
    return f"{algorithm_family}|{claim_pair}|{scope}|delta={delta:.2f}"


def _normalize_dataset(source_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in source_df.to_dict(orient="records"):
        family = str(record["family"])
        if family not in FAMILY_METADATA:
            raise KeyError(f"Missing family metadata for {family}")
        meta = FAMILY_METADATA[family]
        scope = str(record["space_preset"])
        delta = float(record["delta"])
        metric_verdict = _metric_verdict(record["metric_supportive"])
        claim_stability_verdict = str(record["claimstab_decision"])
        claim_validation_outcome = str(record["claim_validation_outcome"])
        false_kind = _false_reassurance_type(metric_verdict, claim_validation_outcome)
        rows.append(
            {
                "claim_id": _claim_id(str(meta["algorithm_family"]), str(record["claim_pair"]), scope, delta),
                "source_table_bundle": str(meta["source_table_bundle"]),
                "source_experiment_bundle": str(meta["source_experiment_bundle"]),
                "source_path": str(RQ1_SOURCE.resolve()),
                "task_family": str(meta["task_family"]),
                "algorithm_family": str(meta["algorithm_family"]),
                "claim_family": "ranking",
                "run_id": str(record["run_id"]),
                "claim_pair": str(record["claim_pair"]),
                "scope": scope,
                "scope_label": SCOPE_LABELS.get(scope, scope),
                "delta": delta,
                "higher_is_better": bool(record["higher_is_better"]),
                "metric_value": float(record["metric_mean_diff"]),
                "metric_verdict": metric_verdict,
                "metric_ci_lower": float(record["metric_ci_low"]),
                "metric_ci_upper": float(record["metric_ci_high"]),
                "baseline_claim_holds": _as_optional_bool(record.get("baseline_claim_holds")),
                "baseline_claim_holds_rate": float(record["baseline_claim_holds_rate"]) if not pd.isna(record["baseline_claim_holds_rate"]) else math.nan,
                "claim_holds_rate_mean": float(record["claim_holds_rate_mean"]) if not pd.isna(record["claim_holds_rate_mean"]) else math.nan,
                "claim_stability_verdict": claim_stability_verdict,
                "claim_validation_outcome": claim_validation_outcome,
                "s_hat": float(record["stability_hat"]),
                "claim_ci_lower": float(record["stability_ci_low"]),
                "claim_ci_upper": float(record["stability_ci_high"]),
                "false_reassurance_type": false_kind,
                "support_alignment": _support_alignment(metric_verdict, claim_validation_outcome),
            }
        )
    dataset = pd.DataFrame(rows)
    dataset = dataset.sort_values(
        by=["algorithm_family", "scope", "claim_pair", "delta"],
        key=lambda series: series.map({name: idx for idx, name in enumerate(SCOPE_ORDER)}) if series.name == "scope" else series,
    ).reset_index(drop=True)
    return dataset


def _make_summary_row(group_kind: str, group: str, df: pd.DataFrame) -> dict[str, Any]:
    n_total = int(len(df))
    metric_positive = int((df["metric_verdict"] == "positive").sum())
    claim_validated = int((df["claim_validation_outcome"] == "validated").sum())
    claim_refuted = int((df["claim_validation_outcome"] == "refuted").sum())
    claim_unstable = int((df["claim_validation_outcome"] == "unstable").sum())
    claim_inconclusive = int((df["claim_validation_outcome"] == "inconclusive").sum())
    pos_refuted = int((df["false_reassurance_type"] == "metric_positive_claim_refuted").sum())
    pos_unstable = int((df["false_reassurance_type"] == "metric_positive_claim_unstable").sum())
    pos_inconclusive = int((df["false_reassurance_type"] == "metric_positive_claim_inconclusive").sum())
    return {
        "group_kind": group_kind,
        "group": group,
        "n_total": n_total,
        "metric_positive": metric_positive,
        "claim_validated": claim_validated,
        "claim_refuted": claim_refuted,
        "claim_unstable": claim_unstable,
        "claim_inconclusive": claim_inconclusive,
        "metric_positive_claim_validated": int(((df["metric_verdict"] == "positive") & (df["claim_validation_outcome"] == "validated")).sum()),
        "metric_positive_claim_refuted": pos_refuted,
        "metric_positive_claim_unstable": pos_unstable,
        "metric_positive_claim_inconclusive": pos_inconclusive,
        "metric_negative_claim_validated": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "validated")).sum()),
        "metric_negative_claim_refuted": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "refuted")).sum()),
        "metric_negative_claim_unstable": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "unstable")).sum()),
        "metric_negative_claim_inconclusive": int(((df["metric_verdict"] == "negative") & (df["claim_validation_outcome"] == "inconclusive")).sum()),
        "conditional_false_reassurance_rate": _safe_rate(pos_refuted + pos_unstable + pos_inconclusive, metric_positive),
        "support_alignment_rate": _safe_rate(int(df["support_alignment"].sum()), n_total),
        "inconclusive_rate": _safe_rate(claim_inconclusive, n_total),
    }


def _build_summary_tables(dataset: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    summary_rows.append(_make_summary_row("overall", "all", dataset))
    for family in sorted(dataset["algorithm_family"].unique()):
        summary_rows.append(_make_summary_row("algorithm_family", family, dataset[dataset["algorithm_family"] == family]))
    for scope in SCOPE_ORDER:
        scope_df = dataset[dataset["scope"] == scope]
        if scope_df.empty:
            continue
        summary_rows.append(_make_summary_row("scope", scope, scope_df))

    breakdown_rows: list[dict[str, Any]] = []
    grouped = dataset.groupby(["algorithm_family", "scope", "delta"], dropna=False)
    for (family, scope, delta), group_df in grouped:
        breakdown_rows.append(
            {
                "algorithm_family": family,
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
                    int((group_df["false_reassurance_type"] == "metric_positive_claim_refuted").sum())
                    + int((group_df["false_reassurance_type"] == "metric_positive_claim_unstable").sum())
                    + int((group_df["false_reassurance_type"] == "metric_positive_claim_inconclusive").sum()),
                    int((group_df["metric_verdict"] == "positive").sum()),
                ),
            }
        )
    breakdown_rows.sort(key=lambda row: (str(row["algorithm_family"]), SCOPE_ORDER.index(str(row["scope"])), float(row["delta"])))
    return summary_rows, breakdown_rows


def _curate_family_breakdown(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in sorted(dataset["algorithm_family"].unique()):
        group_df = dataset[dataset["algorithm_family"] == family]
        summary = _make_summary_row("algorithm_family", family, group_df)
        rows.append(
            {
                "algorithm_family": family,
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": (
                    summary["metric_positive_claim_refuted"]
                    + summary["metric_positive_claim_unstable"]
                    + summary["metric_positive_claim_inconclusive"]
                ),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
                "support_alignment_rate": summary["support_alignment_rate"],
            }
        )
    return rows


def _curate_scope_breakdown(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope in SCOPE_ORDER:
        group_df = dataset[dataset["scope"] == scope]
        if group_df.empty:
            continue
        summary = _make_summary_row("scope", scope, group_df)
        rows.append(
            {
                "scope": scope,
                "scope_label": SCOPE_LABELS.get(scope, scope),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": (
                    summary["metric_positive_claim_refuted"]
                    + summary["metric_positive_claim_unstable"]
                    + summary["metric_positive_claim_inconclusive"]
                ),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
                "support_alignment_rate": summary["support_alignment_rate"],
            }
        )
    return rows


def _curate_delta_breakdown(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for delta in sorted(dataset["delta"].unique()):
        group_df = dataset[dataset["delta"] == delta]
        summary = _make_summary_row("delta", f"{delta:.2f}", group_df)
        rows.append(
            {
                "delta": float(delta),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": (
                    summary["metric_positive_claim_refuted"]
                    + summary["metric_positive_claim_unstable"]
                    + summary["metric_positive_claim_inconclusive"]
                ),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
                "support_alignment_rate": summary["support_alignment_rate"],
            }
        )
    return rows


def _curate_primary_family_sensitivity(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    slices = [
        ("all_families", "All families", dataset),
        ("primary_family_only", "MaxCut primary family only", dataset[dataset["algorithm_family"] == "MaxCut QAOA"]),
    ]
    rows: list[dict[str, Any]] = []
    for slice_key, slice_label, group_df in slices:
        summary = _make_summary_row("sensitivity", slice_key, group_df)
        rows.append(
            {
                "analysis_slice": slice_key,
                "label": slice_label,
                "included_families": ", ".join(sorted(group_df["algorithm_family"].unique())),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": (
                    summary["metric_positive_claim_refuted"]
                    + summary["metric_positive_claim_unstable"]
                    + summary["metric_positive_claim_inconclusive"]
                ),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
            }
        )
    return rows


def _curate_leave_one_family_out(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in sorted(dataset["algorithm_family"].unique()):
        group_df = dataset[dataset["algorithm_family"] != family]
        summary = _make_summary_row("leave_one_out", family, group_df)
        rows.append(
            {
                "excluded_family": family,
                "included_families": ", ".join(sorted(group_df["algorithm_family"].unique())),
                "n_total": summary["n_total"],
                "metric_positive": summary["metric_positive"],
                "claim_validated": summary["claim_validated"],
                "claim_refuted": summary["claim_refuted"],
                "claim_unstable": summary["claim_unstable"],
                "claim_inconclusive": summary["claim_inconclusive"],
                "metric_positive_non_validated": (
                    summary["metric_positive_claim_refuted"]
                    + summary["metric_positive_claim_unstable"]
                    + summary["metric_positive_claim_inconclusive"]
                ),
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
            }
        )
    return rows


def _build_main_paper_structural_table(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add_row(dimension: str, slice_label: str, group_df: pd.DataFrame) -> None:
        summary = _make_summary_row(dimension.lower(), slice_label, group_df)
        metric_positive = int(summary["metric_positive"])
        false_reassurance = int(
            summary["metric_positive_claim_refuted"]
            + summary["metric_positive_claim_unstable"]
            + summary["metric_positive_claim_inconclusive"]
        )
        rows.append(
            {
                "dimension": dimension,
                "slice": slice_label,
                "metric_positive": metric_positive,
                "false_reassurance": false_reassurance,
                "conditional_false_reassurance_rate": summary["conditional_false_reassurance_rate"],
            }
        )

    add_row("Overall", "All variants", dataset)
    for family in ["MaxCut QAOA", "Max-2-SAT QAOA", "VQE/H2"]:
        add_row("Family", family, dataset[dataset["algorithm_family"] == family])
    for scope in SCOPE_ORDER:
        add_row("Scope", scope, dataset[dataset["scope"] == scope])
    for delta in sorted(dataset["delta"].unique()):
        add_row("Delta", f"{float(delta):.2f}", dataset[dataset["delta"] == delta])
    return rows


def _render_metric_positive_headline_figure(dataset: pd.DataFrame, out_png: Path, out_pdf: Path) -> dict[str, Any]:
    metric_positive_df = dataset[dataset["metric_verdict"] == "positive"].copy()
    total = int(len(metric_positive_df))
    segments = [
        ("validated", int((metric_positive_df["claim_validation_outcome"] == "validated").sum()), "#2ca02c"),
        ("unstable", int((metric_positive_df["claim_validation_outcome"] == "unstable").sum()), "#d62728"),
        ("inconclusive", int((metric_positive_df["claim_validation_outcome"] == "inconclusive").sum()), "#7f7f7f"),
        ("refuted", int((metric_positive_df["claim_validation_outcome"] == "refuted").sum()), "#9467bd"),
    ]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, ax = plt.subplots(figsize=(8.0, 2.7))
    left = 0
    for label, count, color in segments:
        if count <= 0:
            continue
        ax.barh(["metric-positive variants"], [count], left=left, color=color, edgecolor="white", height=0.6)
        share = 100.0 * count / total if total else 0.0
        ax.text(left + count / 2, 0, f"{label}\n{count} ({share:.1f}%)", ha="center", va="center", fontsize=10, color="white" if color != "#7f7f7f" else "black", fontweight="bold")
        left += count

    false_reassurance = total - int((metric_positive_df["claim_validation_outcome"] == "validated").sum())
    false_rate = 100.0 * false_reassurance / total if total else 0.0
    ax.set_xlim(0, total if total else 1)
    ax.set_xlabel("count among metric-positive variants")
    ax.set_title("Metric-Positive Outcomes Do Not Reliably Imply Claim Validation")
    ax.grid(False)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=3, color="#666666")
    fig.text(
        0.5,
        0.93,
        f"Headline result: {false_reassurance}/{total} metric-positive variants are not claim-validated ({false_rate:.1f}%).",
        ha="center",
        va="center",
        fontsize=10,
        color="#444444",
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.88))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=240)
    fig.savefig(out_pdf)
    plt.close(fig)
    return {
        "figure_png": str(out_png.resolve()),
        "figure_pdf": str(out_pdf.resolve()),
        "metric_positive_total": total,
        "false_reassurance_count": false_reassurance,
        "false_reassurance_rate": false_rate / 100.0 if total else None,
    }


def _render_discrepancy_matrix(dataset: pd.DataFrame, out_png: Path, out_pdf: Path) -> dict[str, Any]:
    matrix = []
    total = len(dataset)
    counts_by_cell: dict[tuple[str, str], int] = {}
    for metric in METRIC_VERDICT_ORDER:
        row = []
        for claim in CLAIM_OUTCOME_ORDER:
            count = int(((dataset["metric_verdict"] == metric) & (dataset["claim_validation_outcome"] == claim)).sum())
            counts_by_cell[(metric, claim)] = count
            row.append(count)
        matrix.append(row)

    values = [[count / total if total else 0.0 for count in row] for row in matrix]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    image = ax.imshow(values, cmap="Blues", vmin=0.0, vmax=max(max(row) for row in values) if total else 1.0)

    for row_idx, metric in enumerate(METRIC_VERDICT_ORDER):
        for col_idx, claim in enumerate(CLAIM_OUTCOME_ORDER):
            count = counts_by_cell[(metric, claim)]
            share = (100.0 * count / total) if total else 0.0
            ax.text(
                col_idx,
                row_idx,
                f"n={count}\n{share:.1f}%",
                ha="center",
                va="center",
                fontsize=10,
                color="black",
                fontweight="bold" if metric == "positive" and claim != "validated" else "normal",
            )

    # Highlight false-reassurance cells.
    for col_idx, claim in enumerate(CLAIM_OUTCOME_ORDER):
        if claim == "validated":
            continue
        ax.add_patch(
            Rectangle(
                (col_idx - 0.5, 0 - 0.5),
                1.0,
                1.0,
                fill=False,
                linewidth=2.6,
                edgecolor="#d62728",
            )
        )

    ax.set_xticks(range(len(CLAIM_OUTCOME_ORDER)))
    ax.set_xticklabels(["claim\nvalidated", "claim\nrefuted", "claim\nunstable", "claim\ninconclusive"])
    ax.set_yticks(range(len(METRIC_VERDICT_ORDER)))
    ax.set_yticklabels(["metric positive", "metric negative"])
    ax.set_title("Metric vs Claim Discrepancy Matrix")
    ax.set_xlabel("claim validation outcome")
    ax.set_ylabel("metric-level verdict")

    false_rows = dataset[dataset["false_reassurance_type"] != "none"]
    metric_positive = int((dataset["metric_verdict"] == "positive").sum())
    false_rate = _safe_rate(int(len(false_rows)), metric_positive)
    fig.text(
        0.5,
        0.95,
        (
            f"False reassurance among metric-positive variants: "
            f"{len(false_rows)}/{metric_positive} = {100.0 * false_rate:.1f}%"
            if false_rate is not None
            else "False reassurance among metric-positive variants: n/a"
        ),
        ha="center",
        va="center",
        fontsize=10,
        color="#444444",
    )

    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("share of all claim variants")

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.9))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=240)
    fig.savefig(out_pdf)
    plt.close(fig)

    return {
        "matrix_counts": {
            metric: {claim: counts_by_cell[(metric, claim)] for claim in CLAIM_OUTCOME_ORDER}
            for metric in METRIC_VERDICT_ORDER
        },
        "figure_png": str(out_png.resolve()),
        "figure_pdf": str(out_pdf.resolve()),
    }


def _write_interpretation_note(path: Path, dataset: pd.DataFrame, summary_rows: list[dict[str, Any]]) -> None:
    overall = next(row for row in summary_rows if row["group_kind"] == "overall")
    family_rows = [row for row in summary_rows if row["group_kind"] == "algorithm_family"]
    best_scope = max(
        [row for row in summary_rows if row["group_kind"] == "scope"],
        key=lambda row: (row["conditional_false_reassurance_rate"] or -1.0),
    )
    delta_rows = [_make_summary_row("delta", f"{delta:.2f}", dataset[dataset["delta"] == delta]) for delta in sorted(dataset["delta"].unique())]
    maxcut_only = _make_summary_row("sensitivity", "primary_family_only", dataset[dataset["algorithm_family"] == "MaxCut QAOA"])
    refuted_false = int((dataset["false_reassurance_type"] == "metric_positive_claim_refuted").sum())
    unstable_false = int((dataset["false_reassurance_type"] == "metric_positive_claim_unstable").sum())
    inconclusive_false = int((dataset["false_reassurance_type"] == "metric_positive_claim_inconclusive").sum())

    lines = [
        "# RQ1 Metric vs Claim Interpretation",
        "",
        (
            f"Across {overall['n_total']} comparative claim variants in the main-paper ranking population, "
            f"{overall['metric_positive']} are supported by the metric baseline."
        ),
        (
            f"Among these metric-positive variants, {overall['metric_positive_claim_refuted']} are claim-refuted, "
            f"{overall['metric_positive_claim_unstable']} are claim-unstable, and "
            f"{overall['metric_positive_claim_inconclusive']} are claim-inconclusive, yielding a conditional "
            f"false-reassurance rate of {100.0 * float(overall['conditional_false_reassurance_rate']):.1f}%."
        ),
        (
            f"The mismatch is distributed across refuted ({refuted_false}), unstable ({unstable_false}), "
            f"and inconclusive ({inconclusive_false}) claim-validation outcomes."
        ),
        "",
        "## By Algorithm Family",
        "",
    ]
    for row in family_rows:
        rate = row["conditional_false_reassurance_rate"]
        rate_text = "n/a" if rate is None else f"{100.0 * float(rate):.1f}%"
        lines.append(
            f"- {row['group']}: {row['metric_positive_claim_refuted'] + row['metric_positive_claim_unstable'] + row['metric_positive_claim_inconclusive']}/"
            f"{row['metric_positive']} metric-positive variants are non-validated ({rate_text})."
        )
    lines.extend(
        [
            "",
            "## Scope Signal",
            "",
            (
                f"The highest conditional false-reassurance rate appears in the `{best_scope['group']}` scope "
                f"({100.0 * float(best_scope['conditional_false_reassurance_rate']):.1f}%), reinforcing that mismatch "
                f"is structured by admissible perturbation scope rather than by one isolated claim."
            ),
            "",
            "## Delta Signal",
            "",
        ]
    )
    for row in delta_rows:
        lines.append(
            f"- delta = {float(row['group']):.2f}: "
            f"{row['metric_positive_claim_refuted'] + row['metric_positive_claim_unstable'] + row['metric_positive_claim_inconclusive']}/"
            f"{row['metric_positive']} metric-positive variants are non-validated "
            f"({100.0 * float(row['conditional_false_reassurance_rate']):.1f}%)."
        )
    lines.extend(
        [
            "",
            "## Sensitivity",
            "",
            (
                f"The primary MaxCut family alone remains sufficient to recover the core mismatch: "
                f"{maxcut_only['metric_positive_claim_refuted'] + maxcut_only['metric_positive_claim_unstable'] + maxcut_only['metric_positive_claim_inconclusive']}/"
                f"{maxcut_only['metric_positive']} metric-positive variants are non-validated "
                f"({100.0 * float(maxcut_only['conditional_false_reassurance_rate']):.1f}%)."
            ),
            "",
            "These exports support the RQ1 main-text argument that metric-centric evaluation can statistically support outcomes while failing to validate conclusions.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate_against_existing_sources(dataset: pd.DataFrame) -> None:
    source_df = pd.read_csv(RQ1_SOURCE)
    if len(dataset) != len(source_df):
        raise ValueError(f"Unified dataset row count {len(dataset)} does not match source rows {len(source_df)}")

    e1_reference = pd.read_csv(E1_REFERENCE)
    e1_subset = dataset[dataset["algorithm_family"] == "MaxCut QAOA"].copy()
    if len(e1_subset) != len(e1_reference):
        raise ValueError(f"E1 subset row count {len(e1_subset)} does not match reference rows {len(e1_reference)}")

    merged = e1_subset.merge(
        e1_reference,
        left_on=["claim_pair", "scope", "delta"],
        right_on=["claim_pair", "space_preset", "delta"],
        how="outer",
        indicator=True,
    )
    if not (merged["_merge"] == "both").all():
        raise ValueError("E1 subset keys do not match the matched-scope reference table")

    if not (merged["claim_stability_verdict"] == merged["claimstab_decision"]).all():
        raise ValueError("E1 stability verdicts do not match the matched-scope reference table")

    if not all(math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(merged["s_hat"], merged["stability_hat"])):
        raise ValueError("E1 stability estimates do not match the matched-scope reference table")

    e1_stable = merged[merged["claim_stability_verdict"] == "stable"]
    if e1_stable.empty:
        raise ValueError("Expected at least one stable E1 row for sanity checking")
    if bool(e1_stable["baseline_claim_holds"].fillna(False).any()):
        raise ValueError("E1 stable rows are expected to be baseline-refuted under the current artifact")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ICSE RQ1 metric-vs-claim comparison pack.")
    parser.add_argument(
        "--out-root",
        type=Path,
        default=REPO_ROOT / "output" / "paper" / "icse_pack",
        help="Output root for the ICSE pack.",
    )
    args = parser.parse_args()

    out_root = args.out_root
    derived_dir = out_root / "derived" / "RQ1"
    tables_dir = out_root / "tables"
    figures_dir = out_root / "figures" / "main"

    source_df = pd.read_csv(RQ1_SOURCE)
    dataset = _normalize_dataset(source_df)
    _validate_against_existing_sources(dataset)

    dataset_csv = derived_dir / "metric_claim_comparison_dataset.csv"
    dataset_json = derived_dir / "metric_claim_comparison_dataset.json"
    dataset_csv.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(dataset_csv, index=False)
    _write_json(
        dataset_json,
        {
            "meta": {
                "source_tables": [
                    str(RQ1_SOURCE.resolve()),
                    str(E1_REFERENCE.resolve()),
                ],
                "n_rows": int(len(dataset)),
                "scope": "comparative/ranking claim variants only",
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
    headline_figure_meta = _render_metric_positive_headline_figure(
        dataset,
        figures_dir / "fig1_metric_positive_validation_bar.png",
        figures_dir / "fig1_metric_positive_validation_bar.pdf",
    )

    _write_interpretation_note(derived_dir / "metric_claim_interpretation.md", dataset, summary_rows)
    _write_json(
        derived_dir / "metric_claim_comparison_summary.json",
        {
            "dataset_csv": str(dataset_csv.resolve()),
            "dataset_json": str(dataset_json.resolve()),
            "summary_table": str((tables_dir / "tab_mismatch_summary.csv").resolve()),
            "breakdown_table": str((tables_dir / "tab_false_reassurance_breakdown.csv").resolve()),
            "family_breakdown_table": str((tables_dir / "tab_rq1_family_breakdown.csv").resolve()),
            "scope_breakdown_table": str((tables_dir / "tab_rq1_scope_breakdown.csv").resolve()),
            "delta_breakdown_table": str((tables_dir / "tab_rq1_delta_breakdown.csv").resolve()),
            "primary_family_sensitivity_table": str((tables_dir / "tab_rq1_primary_family_sensitivity.csv").resolve()),
            "leave_one_family_out_table": str((tables_dir / "tab_rq1_leave_one_family_out_sensitivity.csv").resolve()),
            "main_paper_table": str((tables_dir / "tab1_rq1_structural_breakdown.csv").resolve()),
            "overall": next(row for row in summary_rows if row["group_kind"] == "overall"),
            "figure": figure_meta,
            "headline_figure": headline_figure_meta,
        },
    )


if __name__ == "__main__":
    main()
