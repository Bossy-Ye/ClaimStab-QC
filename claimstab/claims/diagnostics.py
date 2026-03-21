from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any, Dict, Mapping, Sequence

from claimstab.claims.evaluation import PerturbationKey, ScorePair, collect_paired_scores
from claimstab.claims.ranking import HigherIsBetter, RankingClaim, Relation
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.runners.matrix_runner import ScoreRow

CORE_DIMENSION_NAMES = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]
HYBRID_DIMENSION_NAMES = [
    "init_strategy",
    "init_seed",
]
DIMENSION_NAMES = CORE_DIMENSION_NAMES + HYBRID_DIMENSION_NAMES
DIMENSION_INDEX = {name: idx for idx, name in enumerate(DIMENSION_NAMES)}


def _analysis_dimensions(paired_scores: Mapping[PerturbationKey, ScorePair]) -> list[str]:
    dims = list(CORE_DIMENSION_NAMES)
    keys = list(paired_scores.keys())
    if any(len(k) > 5 and k[5] is not None for k in keys):
        dims.append("init_strategy")
    if any(len(k) > 6 and k[6] is not None for k in keys):
        dims.append("init_seed")
    return dims


def _parse_ranking_claim(claim_spec: RankingClaim | Mapping[str, Any]) -> RankingClaim:
    if isinstance(claim_spec, RankingClaim):
        return claim_spec
    if not isinstance(claim_spec, Mapping):
        raise TypeError("claim_spec must be RankingClaim or mapping")

    method_a = str(claim_spec.get("method_a", "")).strip()
    method_b = str(claim_spec.get("method_b", "")).strip()
    if not method_a or not method_b:
        raise ValueError("claim_spec must include non-empty method_a and method_b")

    delta = float(claim_spec.get("delta", 0.0))
    direction = claim_spec.get("direction")
    higher_is_better = claim_spec.get("higher_is_better")
    if isinstance(direction, HigherIsBetter):
        dir_enum = direction
    elif isinstance(direction, str):
        if direction.strip().lower() == "lower_is_better":
            dir_enum = HigherIsBetter.NO
        else:
            dir_enum = HigherIsBetter.YES
    elif higher_is_better is False:
        dir_enum = HigherIsBetter.NO
    else:
        dir_enum = HigherIsBetter.YES

    return RankingClaim(
        method_a=method_a,
        method_b=method_b,
        delta=delta,
        direction=dir_enum,
    )


def _parse_baseline_key(
    baseline_config: PerturbationKey | Mapping[str, int | str | None] | None,
) -> PerturbationKey | None:
    if baseline_config is None:
        return None
    if isinstance(baseline_config, tuple):
        if len(baseline_config) == 7:
            return baseline_config
        if len(baseline_config) == 5:
            return (
                int(baseline_config[0]),
                int(baseline_config[1]),
                None if baseline_config[2] is None else str(baseline_config[2]),
                int(baseline_config[3]),
                None if baseline_config[4] is None else int(baseline_config[4]),
                None,
                None,
            )
    if isinstance(baseline_config, Mapping):
        core_dims = ["seed_transpiler", "optimization_level", "layout_method", "shots", "seed_simulator"]
        if not all(dim in baseline_config for dim in core_dims):
            return None
        return (
            int(baseline_config["seed_transpiler"]),
            int(baseline_config["optimization_level"]),
            str(baseline_config["layout_method"]) if baseline_config["layout_method"] is not None else None,
            int(baseline_config["shots"]),
            int(baseline_config["seed_simulator"]) if baseline_config["seed_simulator"] is not None else None,
            str(baseline_config["init_strategy"]) if baseline_config.get("init_strategy") is not None else None,
            int(baseline_config["init_seed"]) if baseline_config.get("init_seed") is not None else None,
        )
    raise TypeError("baseline_config must be None, PerturbationKey tuple, or mapping")


def _key_to_config(key: PerturbationKey) -> dict[str, int | str | None]:
    out: dict[str, int | str | None] = {
        "seed_transpiler": key[0],
        "optimization_level": key[1],
        "layout_method": key[2],
        "shots": key[3],
        "seed_simulator": key[4],
    }
    if key[5] is not None:
        out["init_strategy"] = key[5]
    if key[6] is not None:
        out["init_seed"] = key[6]
    return out


def _claim_margin(claim: RankingClaim, score_a: float, score_b: float) -> float:
    if claim.direction.value == "higher_is_better":
        return score_a - score_b
    return score_b - score_a


def _matches_constraints(
    key: PerturbationKey,
    constraints: Mapping[str, int | str | None],
) -> bool:
    for dim_name, expected in constraints.items():
        if dim_name not in DIMENSION_INDEX:
            raise ValueError(f"Unknown perturbation dimension '{dim_name}'")
        if key[DIMENSION_INDEX[dim_name]] != expected:
            return False
    return True


def conditional_rank_flip_summary(
    claim: RankingClaim,
    *,
    paired_scores: Mapping[PerturbationKey, ScorePair],
    baseline_key: PerturbationKey,
    constraints: Mapping[str, int | str | None],
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, Any] | None:
    subset_keys = [k for k in paired_scores if _matches_constraints(k, constraints)]
    if len(subset_keys) < 2:
        return None

    if baseline_key in subset_keys:
        chosen_baseline = baseline_key
    else:
        chosen_baseline = sorted(subset_keys)[0]

    baseline_scores = paired_scores[chosen_baseline]
    baseline_relation = claim.relation(*baseline_scores)
    baseline_margin = _claim_margin(claim, *baseline_scores)

    flips = 0
    for key in subset_keys:
        if key == chosen_baseline:
            continue
        if claim.relation(*paired_scores[key]) != baseline_relation:
            flips += 1

    total = len(subset_keys) - 1
    stability_successes = total - flips
    estimate = estimate_binomial_rate(
        successes=stability_successes,
        total=total,
        confidence=confidence_level,
    )
    decision = conservative_stability_decision(
        estimate=estimate,
        stability_threshold=stability_threshold,
    ).value
    return {
        "constraints": dict(constraints),
        "subset_size": len(subset_keys),
        "baseline_key_used": _key_to_config(chosen_baseline),
        "baseline_margin": baseline_margin,
        "baseline_relation": baseline_relation.value,
        "total": total,
        "flips": flips,
        "flip_rate": 0.0 if total == 0 else flips / total,
        "stability_hat": estimate.rate,
        "stability_ci_low": estimate.ci_low,
        "stability_ci_high": estimate.ci_high,
        "decision": decision,
    }


def single_knob_lockdown_recommendation(
    claim: RankingClaim,
    *,
    paired_scores: Mapping[PerturbationKey, ScorePair],
    baseline_key: PerturbationKey,
    global_flip_rate: float,
    stability_threshold: float,
    confidence_level: float,
    top_k: int = 2,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for dim_name in _analysis_dimensions(paired_scores):
        dim_idx = DIMENSION_INDEX[dim_name]
        values = sorted({k[dim_idx] for k in paired_scores})
        for value in values:
            summary = conditional_rank_flip_summary(
                claim,
                paired_scores=paired_scores,
                baseline_key=baseline_key,
                constraints={dim_name: value},
                stability_threshold=stability_threshold,
                confidence_level=confidence_level,
            )
            if summary is None:
                continue
            improvement = global_flip_rate - float(summary["flip_rate"])
            candidates.append(
                {
                    "dimension": dim_name,
                    "value": value,
                    "flip_rate_improvement": improvement,
                    **summary,
                }
            )

    ranked = sorted(
        candidates,
        key=lambda row: (
            float(row["flip_rate_improvement"]),
            float(row["stability_hat"]),
            -float(row["flip_rate"]),
        ),
        reverse=True,
    )
    return {
        "global_flip_rate": global_flip_rate,
        "top_recommendations": ranked[:max(0, top_k)],
        "candidate_count": len(ranked),
    }


def aggregate_lockdown_recommendations(
    recommendations: Sequence[dict[str, Any]],
    *,
    top_k: int = 2,
) -> list[dict[str, Any]]:
    if not recommendations:
        return []

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in recommendations:
        for item in rec.get("top_recommendations", []):
            key = (str(item["dimension"]), str(item["value"]))
            if key not in grouped:
                grouped[key] = {
                    "dimension": item["dimension"],
                    "value": item["value"],
                    "avg_flip_rate_improvement": 0.0,
                    "avg_flip_rate": 0.0,
                    "avg_stability_hat": 0.0,
                    "count": 0,
                }
            grouped[key]["avg_flip_rate_improvement"] += float(item["flip_rate_improvement"])
            grouped[key]["avg_flip_rate"] += float(item["flip_rate"])
            grouped[key]["avg_stability_hat"] += float(item["stability_hat"])
            grouped[key]["count"] += 1

    rows = []
    for item in grouped.values():
        c = max(1, int(item["count"]))
        rows.append(
            {
                "dimension": item["dimension"],
                "value": item["value"],
                "avg_flip_rate_improvement": item["avg_flip_rate_improvement"] / c,
                "avg_flip_rate": item["avg_flip_rate"] / c,
                "avg_stability_hat": item["avg_stability_hat"] / c,
                "count": item["count"],
            }
        )

    rows.sort(
        key=lambda row: (
            float(row["avg_flip_rate_improvement"]),
            float(row["avg_stability_hat"]),
        ),
        reverse=True,
    )
    return rows[:max(0, top_k)]


def _shots_bucket(shots: int) -> str:
    if shots <= 64:
        return "low"
    if shots <= 256:
        return "medium"
    return "high"


def _observed_condition_cell(
    observation: Mapping[str, Any],
    *,
    context_conditions: Mapping[str, Any] | None,
    cell_dimensions: Sequence[str],
) -> dict[str, Any]:
    cell: dict[str, Any] = {}
    for dim in cell_dimensions:
        if dim == "shots_bucket":
            cell["shots_bucket"] = _shots_bucket(int(observation.get("shots", 0)))
            continue
        cell[dim] = observation.get(dim)
    if context_conditions:
        for k, v in context_conditions.items():
            cell[k] = v
    return cell


def _cell_key(cell: Mapping[str, Any], *, key_order: Sequence[str]) -> tuple[Any, ...]:
    return tuple(cell.get(k) for k in key_order)


def _cell_stats_from_counts(
    *,
    conditions: Mapping[str, Any],
    flips: int,
    total: int,
    confidence_level: float,
    stability_threshold: float,
) -> dict[str, Any]:
    stable = max(0, total - flips)
    estimate = estimate_binomial_rate(
        successes=stable,
        total=max(1, total),
        confidence=confidence_level,
    )
    decision = conservative_stability_decision(
        estimate=estimate,
        stability_threshold=stability_threshold,
    ).value
    return {
        "conditions": dict(conditions),
        "n_eval": int(total),
        "flip_count": int(flips),
        "stable_count": int(stable),
        "flip_rate": 0.0 if total <= 0 else flips / total,
        "stability_hat": estimate.rate,
        "stability_ci_low": estimate.ci_low,
        "stability_ci_high": estimate.ci_high,
        "decision": decision,
    }


def _hamming_one_diff(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    varying_dimensions: Sequence[str],
) -> str | None:
    changed: list[str] = []
    for dim in varying_dimensions:
        if left.get(dim) != right.get(dim):
            changed.append(dim)
            if len(changed) > 1:
                return None
    return changed[0] if len(changed) == 1 else None


def _build_minimal_lockdown_set(
    observations: Sequence[Mapping[str, Any]],
    *,
    varying_dimensions: Sequence[str],
    context_conditions: Mapping[str, Any] | None,
    confidence_level: float,
    stability_threshold: float,
    max_lock_dims: int,
    top_k: int,
) -> dict[str, Any]:
    if not observations:
        return {"best": None, "candidates": []}

    all_candidates: list[dict[str, Any]] = []
    max_depth = min(max_lock_dims, len(varying_dimensions))
    for depth in range(1, max_depth + 1):
        for dims in itertools.combinations(varying_dimensions, depth):
            grouped: dict[tuple[Any, ...], dict[str, int]] = defaultdict(lambda: {"total": 0, "flips": 0})
            conditions_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
            for obs in observations:
                cond = _observed_condition_cell(
                    obs,
                    context_conditions=context_conditions,
                    cell_dimensions=dims,
                )
                key_order = list(dims)
                if context_conditions:
                    key_order.extend(context_conditions.keys())
                key = _cell_key(cond, key_order=key_order)
                grouped[key]["total"] += 1
                grouped[key]["flips"] += 1 if bool(obs.get("is_flip", False)) else 0
                conditions_by_key[key] = cond
            for key, counts in grouped.items():
                stats = _cell_stats_from_counts(
                    conditions=conditions_by_key[key],
                    flips=counts["flips"],
                    total=counts["total"],
                    confidence_level=confidence_level,
                    stability_threshold=stability_threshold,
                )
                if stats["decision"] != "stable":
                    continue
                all_candidates.append(
                    {
                        "lock_dimensions": list(dims),
                        **stats,
                    }
                )
        # Minimal lockdown means the first depth where stable candidates exist.
        if all_candidates:
            break

    if not all_candidates:
        return {"best": None, "candidates": []}

    all_candidates.sort(
        key=lambda row: (
            -int(row["n_eval"]),
            -float(row["stability_ci_low"]),
            -float(row["stability_hat"]),
        )
    )
    return {
        "best": all_candidates[0],
        "candidates": all_candidates[: max(0, top_k)],
    }


def build_conditional_robustness_summary(
    *,
    observations_by_delta: Mapping[str, Sequence[Mapping[str, Any]]],
    stability_threshold: float,
    confidence_level: float,
    context_conditions: Mapping[str, Any] | None = None,
    cell_dimensions: Sequence[str] = ("optimization_level", "layout_method", "shots_bucket"),
    max_lock_dims: int = 2,
    top_k: int = 5,
) -> dict[str, Any]:
    cells_by_delta: dict[str, list[dict[str, Any]]] = {}
    robust_core_by_delta: dict[str, list[dict[str, Any]]] = {}
    failure_frontier_by_delta: dict[str, list[dict[str, Any]]] = {}
    minimal_lockdown_set_by_delta: dict[str, dict[str, Any]] = {}

    for delta, observations in observations_by_delta.items():
        grouped: dict[tuple[Any, ...], dict[str, int]] = defaultdict(lambda: {"total": 0, "flips": 0})
        conditions_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
        key_order = list(cell_dimensions)
        if context_conditions:
            key_order.extend(context_conditions.keys())

        for obs in observations:
            cond = _observed_condition_cell(
                obs,
                context_conditions=context_conditions,
                cell_dimensions=cell_dimensions,
            )
            key = _cell_key(cond, key_order=key_order)
            grouped[key]["total"] += 1
            grouped[key]["flips"] += 1 if bool(obs.get("is_flip", False)) else 0
            conditions_by_key[key] = cond

        cells: list[dict[str, Any]] = []
        for key, counts in grouped.items():
            cells.append(
                _cell_stats_from_counts(
                    conditions=conditions_by_key[key],
                    flips=counts["flips"],
                    total=counts["total"],
                    confidence_level=confidence_level,
                    stability_threshold=stability_threshold,
                )
            )
        cells.sort(
            key=lambda row: (
                -int(row["n_eval"]),
                -float(row["stability_ci_low"]),
                float(row["flip_rate"]),
            )
        )
        cells_by_delta[str(delta)] = cells

        stable_cells = [row for row in cells if str(row["decision"]) == "stable"]
        robust_core_by_delta[str(delta)] = stable_cells[: max(0, top_k)]

        frontier: list[dict[str, Any]] = []
        unstable_cells = [row for row in cells if str(row["decision"]) == "unstable"]
        for stable in stable_cells:
            for unstable in unstable_cells:
                changed_dim = _hamming_one_diff(
                    stable["conditions"],
                    unstable["conditions"],
                    varying_dimensions=cell_dimensions,
                )
                if changed_dim is None:
                    continue
                frontier.append(
                    {
                        "changed_dimension": changed_dim,
                        "stable_conditions": stable["conditions"],
                        "unstable_conditions": unstable["conditions"],
                        "stable_ci_low": stable["stability_ci_low"],
                        "unstable_ci_high": unstable["stability_ci_high"],
                        "stable_n_eval": stable["n_eval"],
                        "unstable_n_eval": unstable["n_eval"],
                    }
                )
        frontier.sort(
            key=lambda row: (
                -min(int(row["stable_n_eval"]), int(row["unstable_n_eval"])),
                -float(row["stable_ci_low"]),
                float(row["unstable_ci_high"]),
            )
        )
        failure_frontier_by_delta[str(delta)] = frontier[: max(0, top_k)]

        minimal_lockdown_set_by_delta[str(delta)] = _build_minimal_lockdown_set(
            observations,
            varying_dimensions=cell_dimensions,
            context_conditions=context_conditions,
            confidence_level=confidence_level,
            stability_threshold=stability_threshold,
            max_lock_dims=max_lock_dims,
            top_k=top_k,
        )

    return {
        "condition_dimensions": list(cell_dimensions),
        "context_conditions": dict(context_conditions or {}),
        "cells_by_delta": cells_by_delta,
        "robust_core_by_delta": robust_core_by_delta,
        "failure_frontier_by_delta": failure_frontier_by_delta,
        "minimal_lockdown_set_by_delta": minimal_lockdown_set_by_delta,
    }


def compute_effect_diagnostics(
    *,
    observations_by_delta: Mapping[str, Sequence[Mapping[str, Any]]],
    varying_dimensions: Sequence[str] = (
        "seed_transpiler",
        "optimization_level",
        "layout_method",
        "shots_bucket",
        "seed_simulator",
    ),
    context_conditions: Mapping[str, Any] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    by_delta: dict[str, dict[str, Any]] = {}

    for delta, observations in observations_by_delta.items():
        main_effects: list[dict[str, Any]] = []
        spread_by_dim: dict[str, float] = {}

        for dim in varying_dimensions:
            grouped: dict[Any, dict[str, int]] = defaultdict(lambda: {"total": 0, "flips": 0})
            for obs in observations:
                cond = _observed_condition_cell(
                    obs,
                    context_conditions=context_conditions,
                    cell_dimensions=[dim],
                )
                value = cond.get(dim)
                grouped[value]["total"] += 1
                grouped[value]["flips"] += 1 if bool(obs.get("is_flip", False)) else 0
            if not grouped:
                continue
            rows = []
            rates: list[float] = []
            total_eval = 0
            for value, counts in grouped.items():
                total = int(counts["total"])
                flips = int(counts["flips"])
                rate = 0.0 if total <= 0 else flips / total
                rows.append({"value": value, "n_eval": total, "flip_rate": rate})
                rates.append(rate)
                total_eval += total
            spread = (max(rates) - min(rates)) if rates else 0.0
            spread_by_dim[dim] = spread
            rows.sort(key=lambda row: int(row["n_eval"]), reverse=True)
            main_effects.append(
                {
                    "dimension": dim,
                    "effect_score": spread,
                    "n_levels": len(rows),
                    "n_eval": total_eval,
                    "by_value": rows[: max(1, top_k)],
                }
            )
        main_effects.sort(key=lambda row: float(row["effect_score"]), reverse=True)

        interaction_effects: list[dict[str, Any]] = []
        for dim_a, dim_b in itertools.combinations(varying_dimensions, 2):
            grouped_pair: dict[tuple[Any, Any], dict[str, int]] = defaultdict(lambda: {"total": 0, "flips": 0})
            for obs in observations:
                cond = _observed_condition_cell(
                    obs,
                    context_conditions=context_conditions,
                    cell_dimensions=[dim_a, dim_b],
                )
                key = (cond.get(dim_a), cond.get(dim_b))
                grouped_pair[key]["total"] += 1
                grouped_pair[key]["flips"] += 1 if bool(obs.get("is_flip", False)) else 0
            if not grouped_pair:
                continue
            pair_rates = []
            total_eval = 0
            for counts in grouped_pair.values():
                total = int(counts["total"])
                flips = int(counts["flips"])
                pair_rates.append(0.0 if total <= 0 else flips / total)
                total_eval += total
            joint_spread = (max(pair_rates) - min(pair_rates)) if pair_rates else 0.0
            main_ref = max(spread_by_dim.get(dim_a, 0.0), spread_by_dim.get(dim_b, 0.0))
            interaction_score = max(0.0, joint_spread - main_ref)
            interaction_effects.append(
                {
                    "dimensions": [dim_a, dim_b],
                    "interaction_score": interaction_score,
                    "joint_spread": joint_spread,
                    "reference_main_effect": main_ref,
                    "n_cells": len(grouped_pair),
                    "n_eval": total_eval,
                }
            )
        interaction_effects.sort(
            key=lambda row: (
                float(row["interaction_score"]),
                float(row["joint_spread"]),
                int(row["n_eval"]),
            ),
            reverse=True,
        )

        by_delta[str(delta)] = {
            "main_effects": main_effects[: max(0, top_k)],
            "interaction_effects": interaction_effects[: max(0, top_k)],
        }

    return {
        "dimensions": list(varying_dimensions),
        "context_conditions": dict(context_conditions or {}),
        "by_delta": by_delta,
    }


def compute_stability_vs_shots(
    score_rows: Sequence[ScoreRow],
    claim_spec: RankingClaim | Mapping[str, Any],
    baseline_config: PerturbationKey | Mapping[str, int | str | None] | None,
    threshold: float,
    confidence_level: float,
) -> list[dict[str, Any]]:
    claim = _parse_ranking_claim(claim_spec)
    baseline_key_target = _parse_baseline_key(baseline_config)

    rows_by_instance: dict[str, list[ScoreRow]] = defaultdict(list)
    for row in score_rows:
        rows_by_instance[row.instance_id].append(row)

    per_shots_counts: dict[int, dict[str, int]] = defaultdict(lambda: {"total": 0, "flips": 0})
    for instance_rows in rows_by_instance.values():
        paired_scores = collect_paired_scores(instance_rows, claim.method_a, claim.method_b)
        shots_values = sorted({int(key[3]) for key in paired_scores})
        for shots in shots_values:
            subset_keys = [key for key in paired_scores if int(key[3]) == shots]
            if len(subset_keys) < 2:
                continue

            if baseline_key_target in subset_keys:
                chosen_baseline = baseline_key_target
            else:
                chosen_baseline = sorted(subset_keys)[0]

            baseline_scores = paired_scores[chosen_baseline]
            baseline_relation = claim.relation(*baseline_scores)

            total = len(subset_keys) - 1
            flips = 0
            for key in subset_keys:
                if key == chosen_baseline:
                    continue
                if claim.relation(*paired_scores[key]) != baseline_relation:
                    flips += 1

            per_shots_counts[shots]["total"] += total
            per_shots_counts[shots]["flips"] += flips

    rows: list[dict[str, Any]] = []
    for shots in sorted(per_shots_counts):
        total = int(per_shots_counts[shots]["total"])
        if total <= 0:
            continue
        flips = int(per_shots_counts[shots]["flips"])
        stability = estimate_binomial_rate(
            successes=total - flips,
            total=total,
            confidence=confidence_level,
        )
        decision = conservative_stability_decision(
            estimate=stability,
            stability_threshold=threshold,
        ).value
        rows.append(
            {
                "shots": shots,
                "n_eval": total,
                "flip_rate": flips / total,
                "stability_hat": stability.rate,
                "stability_ci_low": stability.ci_low,
                "stability_ci_high": stability.ci_high,
                "ci_width": stability.ci_high - stability.ci_low,
                "decision": decision,
            }
        )

    return rows


def minimum_shots_for_stable(shots_rows: Sequence[Mapping[str, Any]]) -> int | None:
    stable_shots = [int(row["shots"]) for row in shots_rows if str(row.get("decision")) == "stable"]
    return min(stable_shots) if stable_shots else None



def rank_flip_root_cause_by_dimension(
    claim: RankingClaim,
    *,
    baseline_scores: ScorePair,
    baseline_key: PerturbationKey,
    paired_scores: Mapping[PerturbationKey, ScorePair],
    top_k: int = 5,
) -> Dict[str, Any]:
    baseline_relation = claim.relation(*baseline_scores)
    baseline_margin = _claim_margin(claim, *baseline_scores)
    active_dimensions = _analysis_dimensions(paired_scores)

    totals_by_dim_value: dict[str, dict[str, int]] = {d: {} for d in active_dimensions}
    flips_by_dim_value: dict[str, dict[str, int]] = {d: {} for d in active_dimensions}
    flip_events: list[dict[str, Any]] = []

    total_perturbations = 0
    total_flips = 0

    for key, (score_a, score_b) in paired_scores.items():
        if key == baseline_key:
            continue

        total_perturbations += 1
        perturbed_relation = claim.relation(score_a, score_b)
        is_flip = perturbed_relation != baseline_relation
        margin = _claim_margin(claim, score_a, score_b)
        margin_to_threshold = margin - claim.delta
        if is_flip:
            total_flips += 1
            if baseline_relation == Relation.A_GT_B:
                severity = max(0.0, claim.delta - margin)
            elif baseline_relation == Relation.A_LT_B:
                severity = max(0.0, margin - claim.delta)
            else:
                severity = abs(margin_to_threshold)
            flip_events.append(
                {
                    "config": _key_to_config(key),
                    "score_a": score_a,
                    "score_b": score_b,
                    "baseline_relation": baseline_relation.value,
                    "perturbed_relation": perturbed_relation.value,
                    "margin": margin,
                    "margin_to_threshold": margin_to_threshold,
                    "flip_severity": severity,
                    "margin_shift_vs_baseline": margin - baseline_margin,
                }
            )

        for dim_name in active_dimensions:
            dim_idx = DIMENSION_INDEX[dim_name]
            value = str(key[dim_idx])
            totals_by_dim_value[dim_name][value] = totals_by_dim_value[dim_name].get(value, 0) + 1
            if is_flip:
                flips_by_dim_value[dim_name][value] = flips_by_dim_value[dim_name].get(value, 0) + 1

    by_dimension: dict[str, dict[str, dict[str, float | int]]] = {}
    for dim_name in active_dimensions:
        dim_stats: dict[str, dict[str, float | int]] = {}
        for value, total in sorted(totals_by_dim_value[dim_name].items()):
            flips = flips_by_dim_value[dim_name].get(value, 0)
            dim_stats[value] = {
                "total": total,
                "flips": flips,
                "flip_rate": 0.0 if total == 0 else flips / total,
            }
        by_dimension[dim_name] = dim_stats

    top_flip_configs = sorted(
        flip_events,
        key=lambda e: (float(e["flip_severity"]), abs(float(e["margin_shift_vs_baseline"]))),
        reverse=True,
    )[:max(0, top_k)]

    return {
        "baseline_relation": baseline_relation.value,
        "total": total_perturbations,
        "flips": total_flips,
        "flip_rate": 0.0 if total_perturbations == 0 else total_flips / total_perturbations,
        "by_dimension": by_dimension,
        "top_flip_configs": top_flip_configs,
    }
