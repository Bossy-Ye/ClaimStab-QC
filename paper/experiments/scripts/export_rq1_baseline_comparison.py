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

from claimstab.baselines.naive import NAIVE_BASELINE_CONFIG


REPO_ROOT = Path(__file__).resolve().parents[3]
RQ1_DATASET = REPO_ROOT / "output" / "paper" / "icse_pack" / "derived" / "RQ1" / "metric_claim_comparison_dataset.csv"

CONFIG_COLUMNS = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]
SUPPORT_RATIO_THRESHOLD = 0.50
NON_SUPPORTIVE = "non_supportive"
SUPPORTIVE = "supportive"
BASELINE_README_NAME = "baseline_comparison_README.md"
BASELINE_ORDER = [
    "single_baseline_realistic_verdict",
    "metric_mean_ci_verdict",
    "majority_support_ratio_verdict",
    "local_sensitivity_verdict",
    "claimstab_reference_verdict",
]
BASELINE_LABELS = {
    "single_baseline_realistic_verdict": "Single baseline (realistic)",
    "metric_mean_ci_verdict": "Metric mean + CI",
    "majority_support_ratio_verdict": "Majority support ratio",
    "local_sensitivity_verdict": "Local sensitivity check",
    "claimstab_reference_verdict": "ClaimStab-QC",
}
LAYOUT_PREFERENCE = ["trivial", "sabre", "dense"]
NORMALIZED_OUTCOME_ORDER = ["validated", "refuted", "unstable", "inconclusive", "non_supportive"]


def _linkage_ids(claim_id: str | None = None) -> dict[str, str]:
    if claim_id is None:
        return {"cro_id": "__aggregate__", "drr_id": "__aggregate__", "oap_id": "__aggregate__"}
    return {"cro_id": claim_id, "drr_id": f"{claim_id}__drr", "oap_id": f"{claim_id}__oap"}


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


def _capability_rows() -> list[dict[str, Any]]:
    return [
        {
            "baseline": "Single baseline (realistic)",
            "verdict_key": "single_baseline_realistic_verdict",
            "support_rule": "supportive iff the realistic default baseline configuration satisfies the claim",
        },
        {
            "baseline": "Metric mean + CI",
            "verdict_key": "metric_mean_ci_verdict",
            "support_rule": "supportive iff the configuration-averaged metric margin is positive and CI low > 0",
        },
        {
            "baseline": "Majority support ratio",
            "verdict_key": "majority_support_ratio_verdict",
            "support_rule": "supportive iff the claim holds in more than 50% of admissible configuration cells",
        },
        {
            "baseline": "Local sensitivity check",
            "verdict_key": "local_sensitivity_verdict",
            "support_rule": "supportive iff all one-factor-local anchor-neighborhood checks preserve the claim",
        },
        {
            "baseline": "ClaimStab-QC",
            "verdict_key": "claimstab_reference_verdict",
            "support_rule": "supportive iff claim-level validation returns validated",
        },
    ]


def _scope_anchor_config(scoped_scores: pd.DataFrame) -> dict[str, Any]:
    anchor: dict[str, Any] = {}
    for column in CONFIG_COLUMNS:
        values = sorted(scoped_scores[column].drop_duplicates().tolist())
        preferred = NAIVE_BASELINE_CONFIG[column]
        if preferred in values:
            anchor[column] = preferred
            continue
        if column == "layout_method":
            anchor[column] = next((value for value in LAYOUT_PREFERENCE if value in values), values[0])
            continue
        if len(values) == 1:
            anchor[column] = values[0]
            continue
        if all(isinstance(value, (int, float)) for value in values):
            anchor[column] = sorted(values, key=lambda value: (abs(value - preferred), value))[0]
            continue
        anchor[column] = values[0]
    return anchor


def _claim_holds(score_a: float, score_b: float, *, delta: float, higher_is_better: bool) -> bool:
    if higher_is_better:
        return score_a >= score_b + delta
    return score_a <= score_b - delta


def _parse_claim_pair(claim_pair: str) -> tuple[str, str]:
    left, right = claim_pair.split(">", 1)
    return left, right


def _family_run_roots(base_dataset: pd.DataFrame) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for family, group in base_dataset.groupby("algorithm_family", dropna=False):
        run_roots = sorted({str(x) for x in group["source_run_root"].fillna("").tolist() if str(x).strip()})
        if len(run_roots) != 1:
            raise ValueError(f"Expected exactly one run root for {family}, got {run_roots}")
        roots[str(family)] = Path(run_roots[0])
    return roots


def _derive_local_sensitivity_map(base_dataset: pd.DataFrame) -> dict[str, dict[str, Any]]:
    run_roots = _family_run_roots(base_dataset)
    result: dict[str, dict[str, Any]] = {}
    for family, run_root in run_roots.items():
        scores = pd.read_csv(run_root / "scores.csv")
        pivot = (
            scores.pivot_table(
                index=["instance_id", "space_preset", *CONFIG_COLUMNS],
                columns="method",
                values="score",
                aggfunc="first",
            )
            .reset_index()
            .copy()
        )
        family_rows = base_dataset[base_dataset["algorithm_family"] == family]
        for record in family_rows.to_dict(orient="records"):
            claim_id = str(record["claim_id"])
            scope = str(record["scope"])
            claim_pair = str(record["claim_pair"])
            delta = float(record["delta"])
            higher_is_better = bool(record["higher_is_better"])
            method_a, method_b = _parse_claim_pair(claim_pair)

            scoped_scores = pivot[pivot["space_preset"] == scope].copy()
            anchor = _scope_anchor_config(scoped_scores)
            active_dimensions = [column for column in CONFIG_COLUMNS if scoped_scores[column].nunique(dropna=False) > 1]

            local_mask = []
            for _, config_row in scoped_scores.iterrows():
                differing_active = 0
                valid = True
                for column in CONFIG_COLUMNS:
                    if config_row[column] != anchor[column]:
                        if column in active_dimensions:
                            differing_active += 1
                        else:
                            valid = False
                            break
                local_mask.append(valid and differing_active <= 1)

            local_scores = scoped_scores[pd.Series(local_mask, index=scoped_scores.index)].copy()
            supportive_by_config: list[bool] = []
            worst_margin: float | None = None
            for _, config_group in local_scores.groupby(CONFIG_COLUMNS, dropna=False):
                if higher_is_better:
                    margin = float((config_group[method_a] - config_group[method_b]).mean())
                else:
                    margin = float((config_group[method_b] - config_group[method_a]).mean())
                worst_margin = margin if worst_margin is None else min(worst_margin, margin)
                supportive_by_config.append(margin > delta)

            result[claim_id] = {
                "local_sensitivity_verdict": SUPPORTIVE if supportive_by_config and all(supportive_by_config) else NON_SUPPORTIVE,
                "local_anchor_config": json.dumps(anchor, sort_keys=True),
                "local_configurations_evaluated": int(len(supportive_by_config)),
                "local_supportive_configurations": int(sum(1 for flag in supportive_by_config if flag)),
                "local_worst_margin": worst_margin,
            }
    return result


def _baseline_dataset_rows(base_dataset: pd.DataFrame, local_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in base_dataset.to_dict(orient="records"):
        claim_id = str(record["claim_id"])
        local = local_map[claim_id]
        rows.append(
            {
                "claim_id": claim_id,
                **_linkage_ids(claim_id),
                "algorithm_family": str(record["algorithm_family"]),
                "task_family": str(record["task_family"]),
                "benchmark_family": str(record["benchmark_family"]),
                "slice_class": str(record["slice_class"]),
                "scope": str(record["scope"]),
                "delta": float(record["delta"]),
                "claim_pair": str(record["claim_pair"]),
                "claim_validation_outcome": str(record["claim_validation_outcome"]),
                "claimstab_decision": str(record["claim_stability_verdict"]),
                "reporting_status": str(record["reporting_status"]),
                "single_baseline_realistic_verdict": SUPPORTIVE if bool(record["baseline_claim_holds"]) else NON_SUPPORTIVE,
                "metric_mean_ci_verdict": SUPPORTIVE if str(record["metric_verdict"]) == "positive" else NON_SUPPORTIVE,
                "majority_support_ratio_verdict": SUPPORTIVE if float(record["claim_holds_rate_mean"]) > SUPPORT_RATIO_THRESHOLD else NON_SUPPORTIVE,
                "local_sensitivity_verdict": str(local["local_sensitivity_verdict"]),
                "claimstab_reference_verdict": SUPPORTIVE if str(record["claim_validation_outcome"]) == "validated" else NON_SUPPORTIVE,
                "baseline_claim_holds_rate": float(record["baseline_claim_holds_rate"]),
                "claim_holds_rate_mean": float(record["claim_holds_rate_mean"]),
                "metric_value": float(record["metric_value"]),
                "metric": str(record["metric"]),
                "local_anchor_config": str(local["local_anchor_config"]),
                "local_configurations_evaluated": int(local["local_configurations_evaluated"]),
                "local_supportive_configurations": int(local["local_supportive_configurations"]),
                "local_worst_margin": local["local_worst_margin"],
            }
        )
    return rows


def _normalized_case_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        for record in frame.to_dict(orient="records"):
            supportive = bool(record[verdict_key] == SUPPORTIVE)
            claim_outcome = str(record["claim_validation_outcome"])
            rows.append(
                {
                    "baseline": str(capability["baseline"]),
                    "verdict_key": verdict_key,
                    "claim_id": str(record["claim_id"]),
                    **_linkage_ids(str(record["claim_id"])),
                    "algorithm_family": str(record["algorithm_family"]),
                    "slice_class": str(record["slice_class"]),
                    "scope": str(record["scope"]),
                    "delta": float(record["delta"]),
                    "supportive": supportive,
                    "normalized_outcome": claim_outcome if supportive else NON_SUPPORTIVE,
                    "claim_validation_outcome": claim_outcome,
                    "reporting_status": str(record["reporting_status"]),
                    "mismatch_vs_claimstab": supportive != bool(record["claimstab_reference_verdict"] == SUPPORTIVE),
                    "false_confidence": supportive and claim_outcome != "validated",
                    "hidden_robustness": (not supportive) and claim_outcome == "validated",
                }
            )
    return rows


def _normalized_summary_rows(normalized_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(normalized_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        sub = frame[frame["verdict_key"] == verdict_key]
        row = {"baseline": str(capability["baseline"]), "verdict_key": verdict_key, **_linkage_ids(), "n_total": int(len(sub))}
        for outcome in NORMALIZED_OUTCOME_ORDER:
            row[f"normalized_{outcome}"] = int((sub["normalized_outcome"] == outcome).sum())
        rows.append(row)
    return rows


def _disagreement_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        supportive = frame[frame[verdict_key] == SUPPORTIVE]
        false_reassurance_count = int((supportive["claim_validation_outcome"] != "validated").sum())
        validated_total = int((frame["claim_validation_outcome"] == "validated").sum())
        rows.append(
            {
                "baseline": str(capability["baseline"]),
                "verdict_key": verdict_key,
                **_linkage_ids(),
                "n_total": int(len(frame)),
                "supportive_variants": int(len(supportive)),
                "validated_supportive": int((supportive["claim_validation_outcome"] == "validated").sum()),
                "refuted_supportive": int((supportive["claim_validation_outcome"] == "refuted").sum()),
                "unstable_supportive": int((supportive["claim_validation_outcome"] == "unstable").sum()),
                "inconclusive_supportive": int((supportive["claim_validation_outcome"] == "inconclusive").sum()),
                "false_reassurance_count": false_reassurance_count,
                "conditional_false_reassurance_rate": (float(false_reassurance_count / len(supportive)) if len(supportive) else None),
                "validated_capture_rate": (float(int((supportive["claim_validation_outcome"] == "validated").sum()) / validated_total) if validated_total else None),
            }
        )
    return rows


def _audit_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    claimstab_supportive = frame["claimstab_reference_verdict"] == SUPPORTIVE
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        supportive_mask = frame[verdict_key] == SUPPORTIVE
        supportive = frame[supportive_mask]
        false_confidence_count = int((supportive["claim_validation_outcome"] != "validated").sum())
        rows.append(
            {
                "baseline": str(capability["baseline"]),
                "verdict_key": verdict_key,
                **_linkage_ids(),
                "n_total": int(len(frame)),
                "supportive_variants": int(supportive_mask.sum()),
                "validated_supportive": int((supportive["claim_validation_outcome"] == "validated").sum()),
                "refuted_supportive": int((supportive["claim_validation_outcome"] == "refuted").sum()),
                "unstable_supportive": int((supportive["claim_validation_outcome"] == "unstable").sum()),
                "inconclusive_supportive": int((supportive["claim_validation_outcome"] == "inconclusive").sum()),
                "false_confidence_count": false_confidence_count,
                "false_confidence_rate_given_supportive": (float(false_confidence_count / len(supportive)) if len(supportive) else None),
                "hidden_robustness_count": int(((~supportive_mask) & (frame["claim_validation_outcome"] == "validated")).sum()),
                "mismatch_vs_claimstab_count": int((supportive_mask != claimstab_supportive).sum()),
                "conditional_false_reassurance_rate": (float(false_confidence_count / len(supportive)) if len(supportive) else None),
                "same_claim_surface_as_rq1": True,
            }
        )
    return rows


def _render_baseline_disagreement_figure(summary_rows: list[dict[str, Any]], out_png: Path, out_pdf: Path, total_variants: int) -> None:
    ordered = sorted(summary_rows, key=lambda row: BASELINE_ORDER.index(str(row["verdict_key"])))
    labels = [BASELINE_LABELS[str(row["verdict_key"])] for row in ordered]
    validated = [int(row["validated_supportive"]) for row in ordered]
    refuted = [int(row["refuted_supportive"]) for row in ordered]
    unstable = [int(row["unstable_supportive"]) for row in ordered]
    inconclusive = [int(row["inconclusive_supportive"]) for row in ordered]
    non_supportive = [total_variants - int(row["supportive_variants"]) for row in ordered]
    y_positions = list(range(len(labels)))

    plt.rcParams.update({"font.family": "serif", "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"], "mathtext.fontset": "cm"})
    fig, ax = plt.subplots(figsize=(9.8, 4.8))
    segments = [
        ("Validated", validated, "#365c4a"),
        ("Refuted", refuted, "#34435e"),
        ("Unstable", unstable, "#9f3d2f"),
        ("Inconclusive", inconclusive, "#ead7d2"),
        ("Non-supportive", non_supportive, "#ececec"),
    ]
    lefts = [0] * len(labels)
    for label, values, color in segments:
        ax.barh(y_positions, values, left=lefts, color=color, edgecolor="white", height=0.64, label=label)
        for idx, value in enumerate(values):
            if value >= 4:
                ax.text(lefts[idx] + value / 2, idx, str(value), ha="center", va="center", fontsize=8.5, color="white" if label in {"Validated", "Refuted", "Unstable"} else "#444")
            lefts[idx] += value
    ax.set_yticks(y_positions, labels=labels)
    ax.invert_yaxis()
    ax.set_xlim(0, total_variants + 6)
    ax.set_xlabel(f"Claim variants (n = {total_variants})")
    ax.grid(axis="x", color="#dddddd", linewidth=0.8)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.2), frameon=False, ncol=5, fontsize=9)
    fig.tight_layout(rect=(0.0, 0.08, 1.0, 1.0))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def _write_note(path: Path, summary_rows: list[dict[str, Any]], total_variants: int) -> None:
    lines = [
        "# RQ1 Baseline Comparison Interpretation",
        "",
        f"This comparison reuses the strengthened internal main surface (n={total_variants}).",
        "",
    ]
    for row in sorted(summary_rows, key=lambda item: BASELINE_ORDER.index(str(item["verdict_key"]))):
        rate = row["conditional_false_reassurance_rate"]
        lines.append(
            f"- {BASELINE_LABELS[str(row['verdict_key'])]}: supportive={row['supportive_variants']} | "
            f"false_reassurance={row['false_reassurance_count']} | "
            f"conditional_false_reassurance={('n/a' if rate is None else f'{100.0 * float(rate):.1f}%')}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_readme(path: Path, dataset_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# RQ1 Baseline Comparison Generation",
                "",
                f"Source surface: `{dataset_path}`",
                "- all baselines are evaluated over the same strengthened claim units",
                "- local sensitivity is derived from the same run roots referenced by the RQ1 dataset",
                "- chemistry/supporting slices are excluded because they are not in the strengthened denominator",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export RQ1 baseline-comparison artifacts for the strengthened internal surface.")
    parser.add_argument("--out-root", type=Path, default=REPO_ROOT / "output" / "paper" / "icse_pack")
    args = parser.parse_args()

    base_dataset = pd.read_csv(RQ1_DATASET)
    local_map = _derive_local_sensitivity_map(base_dataset)
    dataset_rows = _baseline_dataset_rows(base_dataset, local_map)
    disagreement_rows = _disagreement_rows(dataset_rows)
    audit_rows = _audit_rows(dataset_rows)
    normalized_rows = _normalized_case_rows(dataset_rows)
    normalized_summary_rows = _normalized_summary_rows(normalized_rows)
    total_variants = len(dataset_rows)

    derived_dir = args.out_root / "derived" / "RQ1"
    tables_dir = args.out_root / "tables"
    figures_dir = args.out_root / "figures" / "main"

    _write_csv(derived_dir / "baseline_comparison_dataset.csv", dataset_rows)
    _write_json(
        derived_dir / "baseline_comparison_dataset.json",
        {"source_rq1_dataset": str(RQ1_DATASET.resolve()), "support_ratio_threshold": SUPPORT_RATIO_THRESHOLD, "rows": dataset_rows},
    )
    _write_csv(tables_dir / "tab2_baseline_capability_matrix.csv", _capability_rows())
    _write_csv(tables_dir / "tab_baseline_disagreement_summary.csv", disagreement_rows)
    _write_csv(tables_dir / "tab_rq1_baseline_audit_summary.csv", audit_rows)
    _write_csv(tables_dir / "tab_rq1_baseline_normalized_outcomes.csv", normalized_summary_rows)
    _write_csv(derived_dir / "baseline_comparison_case_normalization.csv", normalized_rows)
    _render_baseline_disagreement_figure(
        disagreement_rows,
        figures_dir / "fig2_validated_vs_false_reassurance.png",
        figures_dir / "fig2_validated_vs_false_reassurance.pdf",
        total_variants=total_variants,
    )
    _write_note(derived_dir / "baseline_comparison_interpretation.md", disagreement_rows, total_variants)
    _write_readme(derived_dir / BASELINE_README_NAME, RQ1_DATASET)
    _write_json(
        derived_dir / "baseline_comparison_summary.json",
        {
            "dataset_csv": str((derived_dir / "baseline_comparison_dataset.csv").resolve()),
            "disagreement_summary_csv": str((tables_dir / "tab_baseline_disagreement_summary.csv").resolve()),
            "audit_summary_csv": str((tables_dir / "tab_rq1_baseline_audit_summary.csv").resolve()),
            "normalized_outcomes_csv": str((tables_dir / "tab_rq1_baseline_normalized_outcomes.csv").resolve()),
            "figure_png": str((figures_dir / "fig2_validated_vs_false_reassurance.png").resolve()),
        },
    )

    print(f"baseline_dataset_rows = {total_variants}")


if __name__ == "__main__":
    main()
