from __future__ import annotations

from collections import defaultdict
from typing import Any


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _decision_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"stable": 0, "unstable": 0, "inconclusive": 0}
    for row in rows:
        decision = str(row.get("decision", "inconclusive"))
        if decision in out:
            out[decision] += 1
    return out


def _build_rq2_drivers(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    # NOTE:
    # Summing flips/total across each dimension partition leads to identical rates
    # across dimensions (a partition identity). Instead we score dimensions by how
    # much the flip rate changes across their values (contrast) and by achievable
    # improvement from locking to the best value.
    accum: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "contrast_weighted_sum": 0.0,
            "improvement_weighted_sum": 0.0,
            "global_flip_weighted_sum": 0.0,
            "weight_sum": 0.0,
            "observations": 0.0,
        }
    )

    for exp in experiments:
        diagnostics = exp.get("overall", {}).get("diagnostics", {})
        by_delta_dim = diagnostics.get("by_delta_dimension", {})
        if not isinstance(by_delta_dim, dict):
            continue
        for _, dims in by_delta_dim.items():
            if not isinstance(dims, dict):
                continue
            for dim_name, values in dims.items():
                if not isinstance(values, dict) or not values:
                    continue
                rates: list[float] = []
                flips_total = 0.0
                eval_total = 0.0
                for _, stats in values.items():
                    if not isinstance(stats, dict):
                        continue
                    flips = _as_float(stats.get("flips"), 0.0)
                    total = _as_float(stats.get("total"), 0.0)
                    if total <= 0:
                        continue
                    rates.append(flips / total)
                    flips_total += flips
                    eval_total += total
                if not rates or eval_total <= 0:
                    continue
                min_rate = min(rates)
                max_rate = max(rates)
                global_rate = flips_total / eval_total
                contrast = max_rate - min_rate
                improvement = max(0.0, global_rate - min_rate)
                weight = eval_total

                slot = accum[dim_name]
                slot["contrast_weighted_sum"] += contrast * weight
                slot["improvement_weighted_sum"] += improvement * weight
                slot["global_flip_weighted_sum"] += global_rate * weight
                slot["weight_sum"] += weight
                slot["observations"] += 1.0

    ranked_dims: list[dict[str, Any]] = []
    for dim_name, stats in accum.items():
        w = stats["weight_sum"]
        if w <= 0:
            continue
        avg_contrast = stats["contrast_weighted_sum"] / w
        avg_improvement = stats["improvement_weighted_sum"] / w
        mean_global_flip = stats["global_flip_weighted_sum"] / w
        ranked_dims.append(
            {
                "dimension": dim_name,
                "driver_score": avg_improvement,
                "avg_contrast": avg_contrast,
                "avg_improvement_from_best_value": avg_improvement,
                "flip_rate": mean_global_flip,
                "observations": int(stats["observations"]),
            }
        )

    ranked_dims.sort(
        key=lambda row: (
            float(row.get("driver_score", 0.0)),
            float(row.get("avg_contrast", 0.0)),
            -float(row.get("flip_rate", 0.0)),
        ),
        reverse=True,
    )
    return {"top_dimensions": ranked_dims[:3], "all_dimensions": ranked_dims}


def build_rq_summary(payload: dict[str, Any]) -> dict[str, Any]:
    experiments = payload.get("experiments", [])
    comparative_rows = payload.get("comparative", {}).get("space_claim_delta", [])
    task_name = str(payload.get("meta", {}).get("task", "unknown"))

    rq1_by_space_and_claim: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"stable": 0, "unstable": 0, "inconclusive": 0, "total": 0})
    )
    for row in comparative_rows:
        space = str(row.get("space_preset", "unknown"))
        claim_type = str(row.get("claim_type", "ranking"))
        decision = str(row.get("decision", "inconclusive"))
        bucket = rq1_by_space_and_claim[space][claim_type]
        if decision in {"stable", "unstable", "inconclusive"}:
            bucket[decision] += 1
        bucket["total"] += 1

    rq1 = {
        "task": task_name,
        "by_space_and_claim_type": rq1_by_space_and_claim,
    }

    rq2 = _build_rq2_drivers(experiments)

    cost_rows: list[dict[str, Any]] = []
    for exp in experiments:
        claim = exp.get("claim", {})
        exp_id = str(exp.get("experiment_id"))
        svs = exp.get("overall", {}).get("stability_vs_cost", {})
        by_delta = svs.get("by_delta", {})
        mins = svs.get("minimum_shots_for_stable", {})
        if not isinstance(by_delta, dict):
            continue
        for delta, rows in by_delta.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                cost_rows.append(
                    {
                        "experiment_id": exp_id,
                        "claim_type": claim.get("type", "ranking"),
                        "delta": delta,
                        "shots": row.get("shots"),
                        "n_eval": row.get("n_eval"),
                        "stability_hat": row.get("stability_hat"),
                        "stability_ci_low": row.get("stability_ci_low"),
                        "stability_ci_high": row.get("stability_ci_high"),
                        "decision": row.get("decision"),
                        "minimum_shots_for_stable": mins.get(delta),
                    }
                )
    rq3 = {"stability_vs_cost_rows": cost_rows}

    adaptive_rows: list[dict[str, Any]] = []
    for exp in experiments:
        sampling = exp.get("sampling", {})
        if not isinstance(sampling, dict):
            continue
        adaptive = sampling.get("adaptive_stopping")
        if not isinstance(adaptive, dict) or not adaptive.get("enabled"):
            continue
        adaptive_rows.append(
            {
                "experiment_id": exp.get("experiment_id"),
                "target_ci_width": adaptive.get("target_ci_width"),
                "achieved_ci_width": adaptive.get("achieved_ci_width"),
                "selected_configurations_with_baseline": adaptive.get("selected_configurations_with_baseline"),
                "evaluated_configurations_without_baseline": adaptive.get("evaluated_configurations_without_baseline"),
                "stop_reason": adaptive.get("stop_reason"),
            }
        )
    rq4 = {
        "adaptive_sampling": adaptive_rows,
        "decision_agreement_rate_vs_full_factorial": None,
    }

    naive_counts = {"naive_overclaim": 0, "naive_underclaim": 0, "agree": 0, "naive_uninformative": 0}
    for row in comparative_rows:
        naive = row.get("naive_baseline")
        if isinstance(naive, dict):
            label = str(naive.get("comparison", "naive_uninformative"))
            if label in naive_counts:
                naive_counts[label] += 1
    baseline_compare = {"counts": naive_counts}

    return {
        "rq1_prevalence": rq1,
        "rq2_drivers": rq2,
        "rq3_cost_tradeoff": rq3,
        "rq4_adaptive_sampling": rq4,
        "naive_baseline_comparison": baseline_compare,
        "decision_counts_overall": _decision_counts(comparative_rows),
    }
