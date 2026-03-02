from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from claimstab.claims.evaluation import PerturbationKey, ScorePair
from claimstab.claims.ranking import RankingClaim
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate

DIMENSION_NAMES = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]
DIMENSION_INDEX = {name: idx for idx, name in enumerate(DIMENSION_NAMES)}


def _key_to_config(key: PerturbationKey) -> dict[str, int | str | None]:
    return {
        "seed_transpiler": key[0],
        "optimization_level": key[1],
        "layout_method": key[2],
        "shots": key[3],
        "seed_simulator": key[4],
    }


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
    baseline_holds = claim.holds(*baseline_scores)
    baseline_margin = _claim_margin(claim, *baseline_scores)

    flips = 0
    for key in subset_keys:
        if key == chosen_baseline:
            continue
        if claim.holds(*paired_scores[key]) != baseline_holds:
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
        "baseline_holds": baseline_holds,
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
    for dim_name in DIMENSION_NAMES:
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



def rank_flip_root_cause_by_dimension(
    claim: RankingClaim,
    *,
    baseline_scores: ScorePair,
    baseline_key: PerturbationKey,
    paired_scores: Mapping[PerturbationKey, ScorePair],
    top_k: int = 5,
) -> Dict[str, Any]:
    baseline_holds = claim.holds(*baseline_scores)
    baseline_margin = _claim_margin(claim, *baseline_scores)

    totals_by_dim_value: dict[str, dict[str, int]] = {d: {} for d in DIMENSION_NAMES}
    flips_by_dim_value: dict[str, dict[str, int]] = {d: {} for d in DIMENSION_NAMES}
    flip_events: list[dict[str, Any]] = []

    total_perturbations = 0
    total_flips = 0

    for key, (score_a, score_b) in paired_scores.items():
        if key == baseline_key:
            continue

        total_perturbations += 1
        perturbed_holds = claim.holds(score_a, score_b)
        is_flip = perturbed_holds != baseline_holds
        margin = _claim_margin(claim, score_a, score_b)
        margin_to_threshold = margin - claim.delta
        if is_flip:
            total_flips += 1
            if baseline_holds:
                severity = max(0.0, claim.delta - margin)
            else:
                severity = max(0.0, margin - claim.delta)
            flip_events.append(
                {
                    "config": _key_to_config(key),
                    "score_a": score_a,
                    "score_b": score_b,
                    "perturbed_holds": perturbed_holds,
                    "margin": margin,
                    "margin_to_threshold": margin_to_threshold,
                    "flip_severity": severity,
                    "margin_shift_vs_baseline": margin - baseline_margin,
                }
            )

        for dim_idx, dim_name in enumerate(DIMENSION_NAMES):
            value = str(key[dim_idx])
            totals_by_dim_value[dim_name][value] = totals_by_dim_value[dim_name].get(value, 0) + 1
            if is_flip:
                flips_by_dim_value[dim_name][value] = flips_by_dim_value[dim_name].get(value, 0) + 1

    by_dimension: dict[str, dict[str, dict[str, float | int]]] = {}
    for dim_name in DIMENSION_NAMES:
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
        "baseline_holds": baseline_holds,
        "total": total_perturbations,
        "flips": total_flips,
        "flip_rate": 0.0 if total_perturbations == 0 else total_flips / total_perturbations,
        "by_dimension": by_dimension,
        "top_flip_configs": top_flip_configs,
    }
