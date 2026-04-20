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

FAMILY_SOURCES = [
    {
        "algorithm_family": "MaxCut QAOA",
        "run_root": REPO_ROOT / "output" / "paper" / "evaluation_v2" / "runs" / "E1_maxcut_main",
    },
    {
        "algorithm_family": "Max-2-SAT QAOA",
        "run_root": REPO_ROOT / "output" / "paper" / "evaluation_v3" / "runs" / "W1_max2sat_second_family",
    },
    {
        "algorithm_family": "VQE/H2",
        "run_root": REPO_ROOT / "output" / "paper" / "evaluation_v3" / "runs" / "W1_vqe_pilot",
    },
]

LAYOUT_PREFERENCE = ["trivial", "sabre", "dense"]
BASELINE_ORDER = [
    "metric_mean_ci_verdict",
    "local_sensitivity_verdict",
    "majority_support_ratio_verdict",
    "single_baseline_realistic_verdict",
    "claimstab_reference_verdict",
]
BASELINE_LABELS = {
    "metric_mean_ci_verdict": "Metric mean + CI",
    "local_sensitivity_verdict": "Local sensitivity check",
    "majority_support_ratio_verdict": "Majority support ratio",
    "single_baseline_realistic_verdict": "Single baseline (realistic)",
    "claimstab_reference_verdict": "ClaimStab-QC",
}
BASELINE_COLORS = {
    "metric_mean_ci_verdict": "#b0413e",
    "local_sensitivity_verdict": "#c65d34",
    "majority_support_ratio_verdict": "#a36f1d",
    "single_baseline_realistic_verdict": "#7d7f2a",
    "claimstab_reference_verdict": "#2d7f5e",
}
BASELINE_EXPORT_PREFIX = {
    "single_baseline_realistic_verdict": "single_baseline_realistic",
    "metric_mean_ci_verdict": "metric_mean_ci",
    "majority_support_ratio_verdict": "majority_support_ratio",
    "local_sensitivity_verdict": "local_sensitivity_check",
    "claimstab_reference_verdict": "claimstab_qc",
}
BASELINE_README_NAME = "baseline_comparison_README.md"
NORMALIZED_OUTCOME_ORDER = ["validated", "refuted", "unstable", "inconclusive", "non_supportive"]


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


def _parse_claim_pair(claim_pair: str) -> tuple[str, str]:
    left, right = claim_pair.split(">", 1)
    return left, right


def _claim_holds(score_a: float, score_b: float, *, delta: float, higher_is_better: bool) -> bool:
    if higher_is_better:
        return score_a >= score_b + delta
    return score_a <= score_b - delta


def _scope_anchor_config(scoped_scores: pd.DataFrame) -> dict[str, Any]:
    anchor: dict[str, Any] = {}
    for column in CONFIG_COLUMNS:
        values = sorted(scoped_scores[column].drop_duplicates().tolist())
        preferred = NAIVE_BASELINE_CONFIG[column]
        if preferred in values:
            anchor[column] = preferred
            continue
        if column == "layout_method":
            fallback = next((value for value in LAYOUT_PREFERENCE if value in values), values[0])
            anchor[column] = fallback
            continue
        if len(values) == 1:
            anchor[column] = values[0]
            continue
        if all(isinstance(value, (int, float)) for value in values):
            anchor[column] = sorted(values, key=lambda value: (abs(value - preferred), value))[0]
            continue
        anchor[column] = values[0]
    return anchor


def _derive_local_sensitivity_map() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for source in FAMILY_SOURCES:
        family = str(source["algorithm_family"])
        run_root = Path(source["run_root"])
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
        payload = json.loads((run_root / "claim_stability.json").read_text(encoding="utf-8"))
        comparative_rows = payload.get("comparative", {}).get("space_claim_delta", [])
        for row in comparative_rows:
            scope = str(row["space_preset"])
            claim_pair = str(row["claim_pair"])
            delta = float(row["delta"])
            higher_is_better = bool(row.get("higher_is_better", True))
            method_a, method_b = _parse_claim_pair(claim_pair)

            scoped_scores = pivot[pivot["space_preset"] == scope].copy()
            anchor = _scope_anchor_config(scoped_scores)
            active_dimensions = [
                column for column in CONFIG_COLUMNS if scoped_scores[column].nunique(dropna=False) > 1
            ]

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

            verdict = SUPPORTIVE if supportive_by_config and all(supportive_by_config) else NON_SUPPORTIVE
            claim_id = f"{family}|{claim_pair}|{scope}|delta={delta:.2f}"
            result[claim_id] = {
                "local_sensitivity_verdict": verdict,
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
                "algorithm_family": str(record["algorithm_family"]),
                "scope": str(record["scope"]),
                "delta": float(record["delta"]),
                "claim_pair": str(record["claim_pair"]),
                "claim_validation_outcome": str(record["claim_validation_outcome"]),
                "claimstab_decision": str(record["claim_stability_verdict"]),
                "single_baseline_realistic_verdict": SUPPORTIVE if bool(record["baseline_claim_holds"]) else NON_SUPPORTIVE,
                "metric_mean_ci_verdict": SUPPORTIVE if str(record["metric_verdict"]) == "positive" else NON_SUPPORTIVE,
                "majority_support_ratio_verdict": (
                    SUPPORTIVE if float(record["claim_holds_rate_mean"]) > SUPPORT_RATIO_THRESHOLD else NON_SUPPORTIVE
                ),
                "local_sensitivity_verdict": str(local["local_sensitivity_verdict"]),
                "claimstab_reference_verdict": (
                    SUPPORTIVE if str(record["claim_validation_outcome"]) == "validated" else NON_SUPPORTIVE
                ),
                "baseline_claim_holds_rate": float(record["baseline_claim_holds_rate"]),
                "claim_holds_rate_mean": float(record["claim_holds_rate_mean"]),
                "metric_value": float(record["metric_value"]),
                "local_anchor_config": str(local["local_anchor_config"]),
                "local_configurations_evaluated": int(local["local_configurations_evaluated"]),
                "local_supportive_configurations": int(local["local_supportive_configurations"]),
                "local_worst_margin": local["local_worst_margin"],
            }
        )
    return rows


def _capability_rows() -> list[dict[str, Any]]:
    return [
        {
            "baseline": "Single baseline (realistic)",
            "verdict_key": "single_baseline_realistic_verdict",
            "support_rule": "supportive iff the realistic default baseline configuration satisfies the claim",
            "scope_coverage": "single baseline configuration only",
            "claim_level_validation": "no",
            "conservative_abstention": "no",
            "explanatory_evidence": "no",
            "same_claim_units_as_rq1": "yes",
        },
        {
            "baseline": "Metric mean + CI",
            "verdict_key": "metric_mean_ci_verdict",
            "support_rule": "supportive iff the configuration-averaged metric margin is positive and CI low > 0",
            "scope_coverage": "global aggregate over the declared scope",
            "claim_level_validation": "no",
            "conservative_abstention": "no",
            "explanatory_evidence": "no",
            "same_claim_units_as_rq1": "yes",
        },
        {
            "baseline": "Majority support ratio",
            "verdict_key": "majority_support_ratio_verdict",
            "support_rule": "supportive iff the claim holds in more than 50% of admissible configuration cells",
            "scope_coverage": "global frequency over the declared scope",
            "claim_level_validation": "no",
            "conservative_abstention": "no",
            "explanatory_evidence": "no",
            "same_claim_units_as_rq1": "yes",
        },
        {
            "baseline": "Local sensitivity check",
            "verdict_key": "local_sensitivity_verdict",
            "support_rule": "supportive iff all one-factor-local anchor-neighborhood margin checks preserve the claim",
            "scope_coverage": "local neighborhood around a scope-aware anchor",
            "claim_level_validation": "no",
            "conservative_abstention": "no",
            "explanatory_evidence": "limited",
            "same_claim_units_as_rq1": "yes",
        },
        {
            "baseline": "ClaimStab-QC",
            "verdict_key": "claimstab_reference_verdict",
            "support_rule": "supportive iff claim-level validation returns validated",
            "scope_coverage": "full declared admissible scope",
            "claim_level_validation": "yes",
            "conservative_abstention": "yes",
            "explanatory_evidence": "yes",
            "same_claim_units_as_rq1": "yes",
        },
    ]


def _audit_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    claimstab_supportive = frame["claimstab_reference_verdict"] == SUPPORTIVE
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        supportive_mask = frame[verdict_key] == SUPPORTIVE
        non_supportive_mask = ~supportive_mask
        supportive = frame[supportive_mask]
        rows.append(
            {
                "baseline": str(capability["baseline"]),
                "verdict_key": verdict_key,
                "n_total": int(len(frame)),
                "supportive_variants": int(supportive_mask.sum()),
                "non_supportive_variants": int(non_supportive_mask.sum()),
                "supportive_validated": int((supportive["claim_validation_outcome"] == "validated").sum()),
                "supportive_refuted": int((supportive["claim_validation_outcome"] == "refuted").sum()),
                "supportive_unstable": int((supportive["claim_validation_outcome"] == "unstable").sum()),
                "supportive_inconclusive": int((supportive["claim_validation_outcome"] == "inconclusive").sum()),
                "mismatch_vs_claimstab_count": int((supportive_mask != claimstab_supportive).sum()),
                "mismatch_vs_claimstab_rate": float((supportive_mask != claimstab_supportive).mean()),
                "false_confidence_count": int((supportive_mask & (frame["claim_validation_outcome"] != "validated")).sum()),
                "false_confidence_rate_given_supportive": (
                    float((supportive["claim_validation_outcome"] != "validated").mean()) if len(supportive) else None
                ),
                "hidden_robustness_count": int((non_supportive_mask & (frame["claim_validation_outcome"] == "validated")).sum()),
                "hidden_robustness_rate_given_non_supportive": (
                    float((frame.loc[non_supportive_mask, "claim_validation_outcome"] == "validated").mean())
                    if int(non_supportive_mask.sum())
                    else None
                ),
                "same_claim_surface_as_rq1": True,
            }
        )
    return rows


def _normalized_case_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        supportive_mask = frame[verdict_key] == SUPPORTIVE
        for record in frame.to_dict(orient="records"):
            supportive = bool(record[verdict_key] == SUPPORTIVE)
            claim_outcome = str(record["claim_validation_outcome"])
            normalized_outcome = claim_outcome if supportive else NON_SUPPORTIVE
            rows.append(
                {
                    "baseline": str(capability["baseline"]),
                    "verdict_key": verdict_key,
                    "claim_id": str(record["claim_id"]),
                    "algorithm_family": str(record["algorithm_family"]),
                    "scope": str(record["scope"]),
                    "delta": float(record["delta"]),
                    "supportive": supportive,
                    "normalized_outcome": normalized_outcome,
                    "claim_validation_outcome": claim_outcome,
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
        row = {
            "baseline": str(capability["baseline"]),
            "verdict_key": verdict_key,
            "n_total": int(len(sub)),
        }
        for outcome in NORMALIZED_OUTCOME_ORDER:
            row[f"normalized_{outcome}"] = int((sub["normalized_outcome"] == outcome).sum())
        rows.append(row)
    return rows


def _baseline_confusion_rows(normalized_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(normalized_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        sub = frame[frame["verdict_key"] == verdict_key].copy()
        supportive_mask = sub["supportive"] == True
        agree = int(
            (
                (supportive_mask & (sub["claim_validation_outcome"] == "validated"))
                | ((~supportive_mask) & (sub["claim_validation_outcome"] != "validated"))
            ).sum()
        )
        rows.append(
            {
                "method": str(capability["baseline"]),
                "verdict_key": verdict_key,
                "agree": agree,
                "false_confidence": int(sub["false_confidence"].sum()),
                "abstain_mismatch": int(sub["hidden_robustness"].sum()),
                "direction_mismatch": int(
                    (supportive_mask & (sub["claim_validation_outcome"] == "refuted")).sum()
                ),
            }
        )
    return rows


def _leave_one_family_out_rows(
    base_dataset: pd.DataFrame,
    normalized_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = pd.DataFrame(normalized_rows)
    rows: list[dict[str, Any]] = []
    for family in sorted(base_dataset["algorithm_family"].unique()):
        kept = base_dataset[base_dataset["algorithm_family"] != family].copy()
        metric_positive = int((kept["metric_verdict"] == "positive").sum())
        false_reassurance = int(
            ((kept["metric_verdict"] == "positive") & (kept["claim_validation_outcome"] != "validated")).sum()
        )
        row: dict[str, Any] = {
            "removed_family": family,
            "included_families": ", ".join(sorted(kept["algorithm_family"].unique())),
            "total_variants": int(len(kept)),
            "metric_positive": metric_positive,
            "validated": int((kept["claim_validation_outcome"] == "validated").sum()),
            "refuted": int((kept["claim_validation_outcome"] == "refuted").sum()),
            "unstable": int((kept["claim_validation_outcome"] == "unstable").sum()),
            "inconclusive": int((kept["claim_validation_outcome"] == "inconclusive").sum()),
            "false_reassurance": false_reassurance,
            "false_reassurance_rate": (float(false_reassurance / metric_positive) if metric_positive else None),
        }
        for capability in _capability_rows():
            verdict_key = str(capability["verdict_key"])
            prefix = BASELINE_EXPORT_PREFIX[verdict_key]
            sub = normalized[
                (normalized["verdict_key"] == verdict_key) & (normalized["algorithm_family"] != family)
            ].copy()
            row[f"{prefix}_false_confidence_count"] = int(sub["false_confidence"].sum())
            row[f"{prefix}_mismatch_count"] = int(sub["mismatch_vs_claimstab"].sum())
        rows.append(row)
    return rows


def _representative_case_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        candidates = frame.copy()
        candidates["supportive"] = candidates[verdict_key] == SUPPORTIVE
        candidates["false_confidence"] = candidates["supportive"] & (candidates["claim_validation_outcome"] != "validated")
        candidates["hidden_robustness"] = (~candidates["supportive"]) & (candidates["claim_validation_outcome"] == "validated")
        picks = [
            ("false_confidence", candidates[candidates["false_confidence"]].sort_values(["algorithm_family", "scope", "delta", "claim_pair"]).head(2)),
            ("hidden_robustness", candidates[candidates["hidden_robustness"]].sort_values(["algorithm_family", "scope", "delta", "claim_pair"]).head(2)),
        ]
        for pattern_name, picked in picks:
            for record in picked.to_dict(orient="records"):
                rows.append(
                    {
                        "baseline": str(capability["baseline"]),
                        "verdict_key": verdict_key,
                        "pattern_type": pattern_name,
                        "claim_id": str(record["claim_id"]),
                        "algorithm_family": str(record["algorithm_family"]),
                        "scope": str(record["scope"]),
                        "delta": float(record["delta"]),
                        "claim_pair": str(record["claim_pair"]),
                        "claim_validation_outcome": str(record["claim_validation_outcome"]),
                        "metric_value": float(record["metric_value"]),
                        "baseline_claim_holds_rate": float(record["baseline_claim_holds_rate"]),
                        "claim_holds_rate_mean": float(record["claim_holds_rate_mean"]),
                    }
                )
    return rows


def _disagreement_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(dataset_rows)
    rows: list[dict[str, Any]] = []
    for capability in _capability_rows():
        verdict_key = str(capability["verdict_key"])
        supportive = frame[frame[verdict_key] == SUPPORTIVE]
        validated_supportive = int((supportive["claim_validation_outcome"] == "validated").sum())
        refuted_supportive = int((supportive["claim_validation_outcome"] == "refuted").sum())
        unstable_supportive = int((supportive["claim_validation_outcome"] == "unstable").sum())
        inconclusive_supportive = int((supportive["claim_validation_outcome"] == "inconclusive").sum())
        false_reassurance_count = refuted_supportive + unstable_supportive + inconclusive_supportive
        validated_total = int((frame["claim_validation_outcome"] == "validated").sum())
        rows.append(
            {
                "baseline": str(capability["baseline"]),
                "verdict_key": verdict_key,
                "n_total": int(len(frame)),
                "supportive_variants": int(len(supportive)),
                "validated_supportive": validated_supportive,
                "refuted_supportive": refuted_supportive,
                "unstable_supportive": unstable_supportive,
                "inconclusive_supportive": inconclusive_supportive,
                "false_reassurance_count": false_reassurance_count,
                "conditional_false_reassurance_rate": (
                    float(false_reassurance_count / len(supportive)) if len(supportive) else None
                ),
                "validated_capture_rate": (
                    float(validated_supportive / validated_total) if validated_total else None
                ),
            }
        )
    return rows


def _render_baseline_disagreement_figure(summary_rows: list[dict[str, Any]], out_png: Path, out_pdf: Path) -> None:
    ordered = sorted(summary_rows, key=lambda row: BASELINE_ORDER.index(str(row["verdict_key"])))
    labels = [BASELINE_LABELS[str(row["verdict_key"])] for row in ordered]
    total_variants = max(int(row["n_total"]) for row in ordered)
    validated_counts = [int(row["validated_supportive"]) for row in ordered]
    refuted_counts = [int(row["refuted_supportive"]) for row in ordered]
    unstable_counts = [int(row["unstable_supportive"]) for row in ordered]
    inconclusive_counts = [int(row["inconclusive_supportive"]) for row in ordered]
    supportive_counts = [int(row["supportive_variants"]) for row in ordered]
    non_supportive_counts = [total_variants - supportive for supportive in supportive_counts]
    y_positions = list(range(len(labels)))

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
        }
    )
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    segment_specs = [
        ("Validated", validated_counts, "#365c4a"),
        ("Refuted", refuted_counts, "#34435e"),
        ("Unstable", unstable_counts, "#9f3d2f"),
        ("Inconclusive", inconclusive_counts, "#ead7d2"),
        ("Non-supportive", non_supportive_counts, "#ececec"),
    ]
    lefts = [0] * len(labels)
    for segment_label, values, color in segment_specs:
        ax.barh(
            y_positions,
            values,
            left=lefts,
            color=color,
            edgecolor="white",
            linewidth=0.8,
            height=0.64,
            label=segment_label,
        )
        for idx, value in enumerate(values):
            if value < 4:
                lefts[idx] += value
                continue
            text_color = "white" if segment_label in {"Validated", "Refuted", "Unstable"} else "#444444"
            ax.text(
                lefts[idx] + value / 2.0,
                idx,
                f"{value}",
                ha="center",
                va="center",
                fontsize=8.8,
                color=text_color,
                fontweight="bold",
            )
            lefts[idx] += value

    ax.set_yticks(y_positions, labels=labels)
    ax.invert_yaxis()
    ax.set_xlim(0, total_variants + 8)
    ax.set_xlabel("Claim variants (n = 63)")
    ax.grid(axis="x", color="#dddddd", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.20),
        frameon=False,
        ncol=5,
        fontsize=9.2,
        columnspacing=1.2,
    )
    ax.tick_params(axis="x", bottom=True, labelbottom=True, top=False, labeltop=False)
    ax.set_xticks([0, 13, 27, 45, 63])

    for y, supportive, unstable, inconclusive, refuted in zip(
        y_positions,
        supportive_counts,
        unstable_counts,
        inconclusive_counts,
        refuted_counts,
    ):
        supportive_pct = 100.0 * supportive / total_variants
        ax.text(
            total_variants + 0.6,
            y,
            f"{supportive} supportive ({supportive_pct:.0f}%)",
            ha="left",
            va="center",
            fontsize=8.5,
            color="#333333",
        )
    fig.tight_layout(rect=(0.0, 0.08, 0.96, 1.0))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def _write_interpretation_note(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    by_key = {str(row["verdict_key"]): row for row in summary_rows}

    def describe(verdict_key: str) -> str:
        row = by_key[verdict_key]
        supportive = int(row["supportive_variants"])
        false = int(row["false_reassurance_count"])
        rate = row["conditional_false_reassurance_rate"]
        if rate is None:
            return f"- {BASELINE_LABELS[verdict_key]}: no supportive variants."
        return (
            f"- {BASELINE_LABELS[verdict_key]}: {false}/{supportive} supportive variants are non-validated "
            f"({100.0 * float(rate):.1f}%)."
        )

    lines = [
        "# RQ1 Baseline Comparison Interpretation",
        "",
        "This comparison uses the same 63 comparative claim variants as `RQ1` and evaluates each baseline on the same claim units.",
        "",
        "## Headline",
        "",
        describe("metric_mean_ci_verdict"),
        describe("local_sensitivity_verdict"),
        describe("majority_support_ratio_verdict"),
        describe("single_baseline_realistic_verdict"),
        describe("claimstab_reference_verdict"),
        "",
        "Interpretation:",
        "- several non-ClaimStab baselines still produce substantial false reassurance on the same claim population",
        "- lower false-reassurance baselines are not claim-level validators; they simply use narrower or more local heuristics",
        "- ClaimStab-QC is the only method in this comparison that validates claims directly and supports conservative abstention",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_leave_one_family_out_note(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# RQ1 Leave-One-Family-Out Interpretation",
        "",
        "This sensitivity check reuses the canonical 63-variant comparative surface and removes one workload family at a time.",
        "",
        "Headline rows:",
    ]
    for row in rows:
        rate = row["false_reassurance_rate"]
        rate_str = "n/a" if rate is None else f"{100.0 * float(rate):.1f}%"
        lines.append(
            f"- remove `{row['removed_family']}` -> false reassurance `{row['false_reassurance']}/{row['metric_positive']}` "
            f"({rate_str}), validated `{row['validated']}`, unstable `{row['unstable']}`, refuted `{row['refuted']}`."
        )

    max_rate = max(float(row["false_reassurance_rate"]) for row in rows if row["false_reassurance_rate"] is not None)
    min_rate = min(float(row["false_reassurance_rate"]) for row in rows if row["false_reassurance_rate"] is not None)
    lines.extend(
        [
            "",
            "Interpretation:",
            "- the main RQ1 gap persists in every leave-one-family-out slice; no single family removal collapses false reassurance to zero.",
            f"- across the three leave-one-family-out slices, the false-reassurance rate ranges from `{100.0 * min_rate:.1f}%` to `{100.0 * max_rate:.1f}%`.",
            "- this strengthens the claim that the metric-vs-claim gap is structural rather than being carried by one family alone.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_readme(
    path: Path,
    *,
    dataset_path: Path,
    audit_table_path: Path,
    disagreement_table_path: Path,
    normalized_table_path: Path,
    representative_cases_path: Path,
    confusion_table_path: Path,
    leave_one_out_table_path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# RQ1 Baseline Comparison Generation",
                "",
                "This artifact family is generated from the canonical 63 comparative claim variants already frozen in:",
                f"- `{dataset_path}`",
                "",
                "Compared methods:",
                "- `single_baseline_realistic`",
                "- `metric_mean_ci`",
                "- `majority_support_ratio`",
                "- `local_sensitivity_check`",
                "- `ClaimStab-QC`",
                "",
                "Normalization rule:",
                "- all methods are keyed by the same `claim_id` values from the canonical RQ1 dataset",
                "- conventional methods emit `supportive` / `non_supportive`",
                "- the normalized summary projects each supportive case onto the corresponding ClaimStab outcome bucket",
                "- non-supportive cases are retained as `non_supportive` rather than relabeled as paper outcomes",
                "",
                "Generated outputs:",
                f"- audit table: `{audit_table_path}`",
                f"- disagreement table: `{disagreement_table_path}`",
                f"- normalized summary table: `{normalized_table_path}`",
                f"- baseline confusion table: `{confusion_table_path}`",
                f"- leave-one-family-out table: `{leave_one_out_table_path}`",
                f"- representative cases: `{representative_cases_path}`",
                "",
                "Implementation note:",
                "- `local_sensitivity_check` is derived from the same run bundles used by the canonical comparative surface and remains aligned on the same claim variants.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ICSE baseline-comparison pack for RQ1.")
    parser.add_argument(
        "--out-root",
        type=Path,
        default=REPO_ROOT / "output" / "paper" / "icse_pack",
        help="Output root for the ICSE pack.",
    )
    args = parser.parse_args()

    if not RQ1_DATASET.exists():
        raise FileNotFoundError(f"Expected RQ1 dataset at {RQ1_DATASET}")

    out_root = args.out_root
    derived_dir = out_root / "derived" / "RQ1"
    tables_dir = out_root / "tables"
    figures_dir = out_root / "figures" / "main"

    base_dataset = pd.read_csv(RQ1_DATASET)
    local_map = _derive_local_sensitivity_map()
    dataset_rows = _baseline_dataset_rows(base_dataset, local_map)
    capability_rows = _capability_rows()
    disagreement_rows = _disagreement_rows(dataset_rows)
    audit_rows = _audit_rows(dataset_rows)
    normalized_rows = _normalized_case_rows(dataset_rows)
    normalized_summary_rows = _normalized_summary_rows(normalized_rows)
    confusion_rows = _baseline_confusion_rows(normalized_rows)
    leave_one_out_rows = _leave_one_family_out_rows(base_dataset, normalized_rows)
    representative_rows = _representative_case_rows(dataset_rows)

    _write_csv(derived_dir / "baseline_comparison_dataset.csv", dataset_rows)
    _write_json(
        derived_dir / "baseline_comparison_dataset.json",
        {
            "source_rq1_dataset": str(RQ1_DATASET.resolve()),
            "support_ratio_threshold": SUPPORT_RATIO_THRESHOLD,
            "rows": dataset_rows,
        },
    )
    _write_csv(tables_dir / "tab2_baseline_capability_matrix.csv", capability_rows)
    _write_csv(tables_dir / "tab_baseline_disagreement_summary.csv", disagreement_rows)
    _write_csv(tables_dir / "tab_rq1_baseline_audit_summary.csv", audit_rows)
    _write_csv(tables_dir / "tab_rq1_baseline_normalized_outcomes.csv", normalized_summary_rows)
    _write_csv(tables_dir / "tab_rq1_baseline_confusion.csv", confusion_rows)
    _write_csv(tables_dir / "tab_rq1_leave_one_family_out.csv", leave_one_out_rows)
    _write_csv(derived_dir / "baseline_comparison_case_normalization.csv", normalized_rows)
    _write_csv(derived_dir / "baseline_comparison_representative_cases.csv", representative_rows)
    _render_baseline_disagreement_figure(
        disagreement_rows,
        figures_dir / "fig2_validated_vs_false_reassurance.png",
        figures_dir / "fig2_validated_vs_false_reassurance.pdf",
    )
    _write_interpretation_note(derived_dir / "baseline_comparison_interpretation.md", disagreement_rows)
    _write_leave_one_family_out_note(derived_dir / "rq1_leave_one_family_out_interpretation.md", leave_one_out_rows)
    _write_readme(
        derived_dir / BASELINE_README_NAME,
        dataset_path=RQ1_DATASET,
        audit_table_path=tables_dir / "tab_rq1_baseline_audit_summary.csv",
        disagreement_table_path=tables_dir / "tab_baseline_disagreement_summary.csv",
        normalized_table_path=tables_dir / "tab_rq1_baseline_normalized_outcomes.csv",
        representative_cases_path=derived_dir / "baseline_comparison_representative_cases.csv",
        confusion_table_path=tables_dir / "tab_rq1_baseline_confusion.csv",
        leave_one_out_table_path=tables_dir / "tab_rq1_leave_one_family_out.csv",
    )
    _write_json(
        derived_dir / "baseline_comparison_summary.json",
        {
            "dataset_csv": str((derived_dir / "baseline_comparison_dataset.csv").resolve()),
            "capability_matrix_csv": str((tables_dir / "tab2_baseline_capability_matrix.csv").resolve()),
            "disagreement_summary_csv": str((tables_dir / "tab_baseline_disagreement_summary.csv").resolve()),
            "audit_summary_csv": str((tables_dir / "tab_rq1_baseline_audit_summary.csv").resolve()),
            "normalized_outcomes_csv": str((tables_dir / "tab_rq1_baseline_normalized_outcomes.csv").resolve()),
            "baseline_confusion_csv": str((tables_dir / "tab_rq1_baseline_confusion.csv").resolve()),
            "leave_one_family_out_csv": str((tables_dir / "tab_rq1_leave_one_family_out.csv").resolve()),
            "case_normalization_csv": str((derived_dir / "baseline_comparison_case_normalization.csv").resolve()),
            "representative_cases_csv": str((derived_dir / "baseline_comparison_representative_cases.csv").resolve()),
            "leave_one_family_out_note_md": str((derived_dir / "rq1_leave_one_family_out_interpretation.md").resolve()),
            "readme_md": str((derived_dir / BASELINE_README_NAME).resolve()),
            "figure_png": str((figures_dir / "fig2_validated_vs_false_reassurance.png").resolve()),
            "figure_pdf": str((figures_dir / "fig2_validated_vs_false_reassurance.pdf").resolve()),
        },
    )


if __name__ == "__main__":
    main()
