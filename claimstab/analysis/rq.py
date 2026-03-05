from __future__ import annotations

import math
import sys
from collections import defaultdict
from typing import Any, TextIO


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


def _build_rq5_conditional_robustness(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    robust_core_rows: list[dict[str, Any]] = []
    failure_frontier_rows: list[dict[str, Any]] = []
    minimal_lockdown_rows: list[dict[str, Any]] = []
    experiments_with_map = 0

    for exp in experiments:
        overall = exp.get("overall", {})
        robustness = overall.get("conditional_robustness")
        if not isinstance(robustness, dict):
            continue
        experiments_with_map += 1
        exp_id = str(exp.get("experiment_id"))
        claim = exp.get("claim", {})
        claim_type = str(claim.get("type", "ranking"))

        for delta, rows in robustness.get("robust_core_by_delta", {}).items():
            if not isinstance(rows, list):
                continue
            for row in rows[:3]:
                if not isinstance(row, dict):
                    continue
                robust_core_rows.append(
                    {
                        "experiment_id": exp_id,
                        "claim_type": claim_type,
                        "delta": str(delta),
                        "conditions": row.get("conditions", {}),
                        "n_eval": _as_int(row.get("n_eval"), 0),
                        "stability_hat": _as_float(row.get("stability_hat"), 0.0),
                        "stability_ci_low": _as_float(row.get("stability_ci_low"), 0.0),
                        "stability_ci_high": _as_float(row.get("stability_ci_high"), 0.0),
                        "decision": str(row.get("decision", "inconclusive")),
                    }
                )

        for delta, rows in robustness.get("failure_frontier_by_delta", {}).items():
            if not isinstance(rows, list):
                continue
            for row in rows[:3]:
                if not isinstance(row, dict):
                    continue
                failure_frontier_rows.append(
                    {
                        "experiment_id": exp_id,
                        "claim_type": claim_type,
                        "delta": str(delta),
                        "changed_dimension": row.get("changed_dimension"),
                        "stable_conditions": row.get("stable_conditions", {}),
                        "unstable_conditions": row.get("unstable_conditions", {}),
                        "stable_n_eval": _as_int(row.get("stable_n_eval"), 0),
                        "unstable_n_eval": _as_int(row.get("unstable_n_eval"), 0),
                    }
                )

        for delta, payload in robustness.get("minimal_lockdown_set_by_delta", {}).items():
            if not isinstance(payload, dict):
                continue
            best = payload.get("best")
            if not isinstance(best, dict):
                continue
            minimal_lockdown_rows.append(
                {
                    "experiment_id": exp_id,
                    "claim_type": claim_type,
                    "delta": str(delta),
                    "lock_dimensions": best.get("lock_dimensions", []),
                    "conditions": best.get("conditions", {}),
                    "n_eval": _as_int(best.get("n_eval"), 0),
                    "stability_hat": _as_float(best.get("stability_hat"), 0.0),
                    "stability_ci_low": _as_float(best.get("stability_ci_low"), 0.0),
                    "stability_ci_high": _as_float(best.get("stability_ci_high"), 0.0),
                    "decision": str(best.get("decision", "inconclusive")),
                }
            )

    robust_core_rows.sort(
        key=lambda row: (
            row.get("decision") == "stable",
            _as_int(row.get("n_eval"), 0),
            _as_float(row.get("stability_ci_low"), 0.0),
        ),
        reverse=True,
    )
    minimal_lockdown_rows.sort(
        key=lambda row: (
            len(row.get("lock_dimensions", [])),
            -_as_int(row.get("n_eval"), 0),
            -_as_float(row.get("stability_ci_low"), 0.0),
        ),
    )
    failure_frontier_rows.sort(
        key=lambda row: min(_as_int(row.get("stable_n_eval"), 0), _as_int(row.get("unstable_n_eval"), 0)),
        reverse=True,
    )

    return {
        "experiments_with_map": experiments_with_map,
        "robust_core_examples": robust_core_rows[:20],
        "failure_frontier_examples": failure_frontier_rows[:20],
        "minimal_lockdown_examples": minimal_lockdown_rows[:20],
    }


def _build_rq6_stratified_stability(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    experiments_with_strata = 0
    all_dimensions: set[str] = set()
    stable_rows: list[dict[str, Any]] = []
    unstable_rows: list[dict[str, Any]] = []
    inconclusive_rows: list[dict[str, Any]] = []

    for exp in experiments:
        overall = exp.get("overall", {})
        stratified = overall.get("stratified_stability")
        if not isinstance(stratified, dict):
            continue
        by_delta = stratified.get("by_delta")
        if not isinstance(by_delta, dict):
            continue
        experiments_with_strata += 1
        for name in stratified.get("strata_dimensions", []):
            all_dimensions.add(str(name))
        exp_id = str(exp.get("experiment_id"))
        claim = exp.get("claim", {})
        claim_type = str(claim.get("type", "ranking"))

        for delta, rows in by_delta.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                out_row = {
                    "experiment_id": exp_id,
                    "claim_type": claim_type,
                    "delta": str(delta),
                    "conditions": row.get("conditions", {}),
                    "n_instances": _as_int(row.get("n_instances"), 0),
                    "n_eval": _as_int(row.get("n_eval"), 0),
                    "flip_rate": _as_float(row.get("flip_rate"), 0.0),
                    "stability_hat": _as_float(row.get("stability_hat"), 0.0),
                    "stability_ci_low": _as_float(row.get("stability_ci_low"), 0.0),
                    "stability_ci_high": _as_float(row.get("stability_ci_high"), 0.0),
                    "decision": str(row.get("decision", "inconclusive")),
                }
                decision = str(out_row["decision"])
                if decision == "stable":
                    stable_rows.append(out_row)
                elif decision == "unstable":
                    unstable_rows.append(out_row)
                else:
                    inconclusive_rows.append(out_row)

    stable_rows.sort(
        key=lambda row: (
            _as_float(row.get("stability_ci_low"), 0.0),
            _as_int(row.get("n_eval"), 0),
            _as_int(row.get("n_instances"), 0),
        ),
        reverse=True,
    )
    unstable_rows.sort(
        key=lambda row: (
            _as_float(row.get("flip_rate"), 0.0),
            -_as_float(row.get("stability_ci_high"), 0.0),
            _as_int(row.get("n_eval"), 0),
        ),
        reverse=True,
    )
    inconclusive_rows.sort(
        key=lambda row: (
            _as_int(row.get("n_eval"), 0),
            _as_float(row.get("stability_ci_low"), 0.0),
        ),
        reverse=True,
    )

    decision_counts = {
        "stable": len(stable_rows),
        "unstable": len(unstable_rows),
        "inconclusive": len(inconclusive_rows),
    }
    return {
        "experiments_with_strata": experiments_with_strata,
        "strata_dimensions": sorted(all_dimensions),
        "decision_counts": decision_counts,
        "stable_examples": stable_rows[:20],
        "unstable_examples": unstable_rows[:20],
        "inconclusive_examples": inconclusive_rows[:20],
    }


def _build_rq7_effect_diagnostics(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    experiments_with_effects = 0
    dimensions_union: set[str] = set()
    main_effect_rows: list[dict[str, Any]] = []
    interaction_rows: list[dict[str, Any]] = []

    for exp in experiments:
        overall = exp.get("overall", {})
        effects = overall.get("effect_diagnostics")
        if not isinstance(effects, dict):
            continue
        by_delta = effects.get("by_delta")
        if not isinstance(by_delta, dict):
            continue
        experiments_with_effects += 1
        for dim_name in effects.get("dimensions", []):
            dimensions_union.add(str(dim_name))
        context_conditions = effects.get("context_conditions", {})
        exp_id = str(exp.get("experiment_id"))
        claim = exp.get("claim", {})
        claim_type = str(claim.get("type", "ranking"))

        for delta, payload in by_delta.items():
            if not isinstance(payload, dict):
                continue
            for row in payload.get("main_effects", []):
                if not isinstance(row, dict):
                    continue
                main_effect_rows.append(
                    {
                        "experiment_id": exp_id,
                        "claim_type": claim_type,
                        "delta": str(delta),
                        "context_conditions": context_conditions,
                        "dimension": str(row.get("dimension", "")),
                        "effect_score": _as_float(row.get("effect_score"), 0.0),
                        "n_levels": _as_int(row.get("n_levels"), 0),
                        "n_eval": _as_int(row.get("n_eval"), 0),
                        "by_value": row.get("by_value", []),
                    }
                )
            for row in payload.get("interaction_effects", []):
                if not isinstance(row, dict):
                    continue
                dims = row.get("dimensions", [])
                interaction_rows.append(
                    {
                        "experiment_id": exp_id,
                        "claim_type": claim_type,
                        "delta": str(delta),
                        "context_conditions": context_conditions,
                        "dimensions": [str(x) for x in dims] if isinstance(dims, list) else [],
                        "interaction_score": _as_float(row.get("interaction_score"), 0.0),
                        "joint_spread": _as_float(row.get("joint_spread"), 0.0),
                        "reference_main_effect": _as_float(row.get("reference_main_effect"), 0.0),
                        "n_cells": _as_int(row.get("n_cells"), 0),
                        "n_eval": _as_int(row.get("n_eval"), 0),
                    }
                )

    main_effect_rows.sort(
        key=lambda row: (
            _as_float(row.get("effect_score"), 0.0),
            _as_int(row.get("n_eval"), 0),
            _as_int(row.get("n_levels"), 0),
        ),
        reverse=True,
    )
    interaction_rows.sort(
        key=lambda row: (
            _as_float(row.get("interaction_score"), 0.0),
            _as_float(row.get("joint_spread"), 0.0),
            _as_int(row.get("n_eval"), 0),
        ),
        reverse=True,
    )

    return {
        "experiments_with_effect_diagnostics": experiments_with_effects,
        "dimensions": sorted(dimensions_union),
        "top_main_effects": main_effect_rows[:20],
        "top_interactions": interaction_rows[:20],
    }


def _weighted_std(values: list[float], weights: list[float]) -> float:
    if not values or not weights:
        return 0.0
    denom = sum(weights)
    if denom <= 0.0:
        return 0.0
    mean = sum(v * w for v, w in zip(values, weights)) / denom
    variance = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / denom
    return math.sqrt(max(0.0, variance))


def _emit_rq2_debug(accum: dict[str, dict[str, float]], ranked_dims: list[dict[str, Any]], stream: TextIO) -> None:
    print("[RQ2 attribution debug] Driver metric: weighted std of per-value flip rates.", file=stream)
    print(
        "[RQ2 attribution debug] driver_score = sqrt(sum_v w_v*(r_v-r_bar)^2 / sum_v w_v), "
        "r_v=flips_v/total_v, w_v=total_v",
        file=stream,
    )
    print(
        "[RQ2 attribution debug] flip contribution rate field in output = total_flips / total_configs_considered.",
        file=stream,
    )
    print("[RQ2 attribution debug] per-dimension normalization to sum=1: False", file=stream)
    print(
        "[RQ2 attribution debug] averaged after per-instance normalization: False "
        "(weighted by total evaluations per observation).",
        file=stream,
    )

    for dim_name in sorted(accum.keys()):
        stats = accum[dim_name]
        total_evals = stats["total_evals"]
        total_flips = stats["total_flips"]
        flip_contribution_rate = 0.0 if total_evals <= 0 else total_flips / total_evals
        observations = int(stats["observations"])
        value_groups = int(stats["value_groups"])
        mean_unweighted_gap = 0.0 if observations == 0 else stats["unweighted_gap_sum"] / float(observations)
        mean_weighted_gap = 0.0 if observations == 0 else stats["weighted_gap_sum"] / float(observations)
        print(
            "[RQ2 attribution debug] "
            f"dimension={dim_name} "
            f"total_configs_considered={int(round(total_evals))} "
            f"total_flips_counted={int(round(total_flips))} "
            f"value_groups={value_groups} "
            f"observations={observations} "
            f"flip_contribution_rate={flip_contribution_rate:.6f} "
            f"(= {total_flips:.0f}/{total_evals:.0f}) "
            f"mean_unweighted_gap_to_global={mean_unweighted_gap:.6f} "
            f"mean_weighted_gap_to_global={mean_weighted_gap:.6f}",
            file=stream,
        )

    flip_rates = [float(row.get("flip_rate", 0.0)) for row in ranked_dims]
    driver_scores = [float(row.get("driver_score", 0.0)) for row in ranked_dims]
    eval_totals = [float(stats["total_evals"]) for stats in accum.values() if stats["total_evals"] > 0]
    unweighted_gaps = [
        (stats["unweighted_gap_sum"] / stats["observations"]) if stats["observations"] > 0 else 0.0
        for stats in accum.values()
    ]

    pattern_a = bool(unweighted_gaps) and max(unweighted_gaps) <= 1e-6
    pattern_b = False
    pattern_c = (
        len(eval_totals) > 1
        and (max(eval_totals) - min(eval_totals)) <= 1e-9
        and len(flip_rates) > 1
        and (max(flip_rates) - min(flip_rates)) <= 1e-12
    )
    pattern_d = len(driver_scores) > 1 and (max(driver_scores) - min(driver_scores)) <= 1e-12

    print(f"[RQ2 attribution debug] Pattern A (mean(rate_by_value) ~= global_rate): {pattern_a}", file=stream)
    print(f"[RQ2 attribution debug] Pattern B (within-dimension normalization): {pattern_b}", file=stream)
    print(
        "[RQ2 attribution debug] Pattern C (flip contribution collapses to global rate): "
        f"{pattern_c}",
        file=stream,
    )
    print(f"[RQ2 attribution debug] Pattern D (same scalar reused for all dimensions): {pattern_d}", file=stream)


def _build_rq2_drivers(
    experiments: list[dict[str, Any]],
    *,
    debug_attribution: bool = False,
    debug_stream: TextIO | None = None,
) -> dict[str, Any]:
    # NOTE:
    # Summing flips/total across each dimension partition leads to identical rates
    # across dimensions (a partition identity). We therefore score dimensions by
    # how much value-level flip rates spread within each dimension.
    accum: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "std_weighted_sum": 0.0,
            "contrast_weighted_sum": 0.0,
            "improvement_weighted_sum": 0.0,
            "global_flip_weighted_sum": 0.0,
            "weight_sum": 0.0,
            "observations": 0.0,
            "value_groups": 0.0,
            "total_flips": 0.0,
            "total_evals": 0.0,
            "unweighted_gap_sum": 0.0,
            "weighted_gap_sum": 0.0,
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
                weights: list[float] = []
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
                    weights.append(total)
                    flips_total += flips
                    eval_total += total
                if not rates or eval_total <= 0:
                    continue
                min_rate = min(rates)
                max_rate = max(rates)
                global_rate = flips_total / eval_total
                weighted_mean_by_value = sum(r * w for r, w in zip(rates, weights)) / eval_total
                unweighted_mean_by_value = sum(rates) / float(len(rates))
                spread_std = _weighted_std(rates, weights)
                contrast = max_rate - min_rate
                improvement = max(0.0, global_rate - min_rate)
                weight = eval_total

                slot = accum[dim_name]
                slot["std_weighted_sum"] += spread_std * weight
                slot["contrast_weighted_sum"] += contrast * weight
                slot["improvement_weighted_sum"] += improvement * weight
                slot["global_flip_weighted_sum"] += global_rate * weight
                slot["weight_sum"] += weight
                slot["observations"] += 1.0
                slot["value_groups"] += float(len(rates))
                slot["total_flips"] += flips_total
                slot["total_evals"] += eval_total
                slot["unweighted_gap_sum"] += abs(unweighted_mean_by_value - global_rate)
                slot["weighted_gap_sum"] += abs(weighted_mean_by_value - global_rate)

    ranked_dims: list[dict[str, Any]] = []
    for dim_name, stats in accum.items():
        w = stats["weight_sum"]
        if w <= 0:
            continue
        avg_std = stats["std_weighted_sum"] / w
        avg_contrast = stats["contrast_weighted_sum"] / w
        avg_improvement = stats["improvement_weighted_sum"] / w
        mean_global_flip = stats["global_flip_weighted_sum"] / w
        ranked_dims.append(
            {
                "dimension": dim_name,
                "driver_score": avg_std,
                "avg_contrast": avg_contrast,
                "avg_improvement_from_best_value": avg_improvement,
                "flip_rate": mean_global_flip,
                "observations": int(stats["observations"]),
                "value_groups": int(stats["value_groups"]),
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
    if debug_attribution:
        _emit_rq2_debug(accum, ranked_dims, debug_stream or sys.stdout)
    return {
        "metric_name": "std_flip_rate_across_values",
        "metric_label": "driver score (std of flip rate across knob values)",
        "metric_formula": "driver_score = sqrt(sum_v w_v*(r_v-r_bar)^2 / sum_v w_v), r_v=flips_v/total_v, w_v=total_v",
        "metric_note": "Higher score means changing this knob shifts flip-rate behavior more across its values.",
        "top_dimensions": ranked_dims[:3],
        "all_dimensions": ranked_dims,
    }


def build_rq_summary(
    payload: dict[str, Any],
    *,
    debug_attribution: bool = False,
    debug_stream: TextIO | None = None,
) -> dict[str, Any]:
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

    rq2 = _build_rq2_drivers(experiments, debug_attribution=debug_attribution, debug_stream=debug_stream)

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
    rq5 = _build_rq5_conditional_robustness(experiments)
    rq6 = _build_rq6_stratified_stability(experiments)
    rq7 = _build_rq7_effect_diagnostics(experiments)

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
        "rq5_conditional_robustness": rq5,
        "rq6_stratified_stability": rq6,
        "rq7_effect_diagnostics": rq7,
        "naive_baseline_comparison": baseline_compare,
        "decision_counts_overall": _decision_counts(comparative_rows),
    }
