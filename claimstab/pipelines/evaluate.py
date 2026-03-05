from __future__ import annotations

from collections import defaultdict
from typing import Any

from claimstab.claims.decision import decision_in_top_k, evaluate_decision_claim
from claimstab.claims.diagnostics import conditional_rank_flip_summary, rank_flip_root_cause_by_dimension, single_knob_lockdown_recommendation
from claimstab.claims.distribution import evaluate_distribution_claim
from claimstab.claims.evaluation import collect_paired_scores, perturbation_key
from claimstab.claims.ranking import HigherIsBetter, RankingClaim, compute_rank_flip_summary
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.runners.matrix_runner import ScoreRow


def _bucket_problem_size(value: int) -> str:
    if value <= 6:
        return "small"
    if value <= 10:
        return "medium"
    return "large"


def _bucket_density(value: float) -> str:
    if value <= 0.25:
        return "sparse"
    if value <= 0.45:
        return "mid"
    return "dense"


def _bucket_transpiled_depth(depth: int | None) -> str | None:
    if depth is None:
        return None
    if depth <= 40:
        return "depth_low"
    if depth <= 120:
        return "depth_mid"
    return "depth_high"


def _bucket_two_qubit_count(two_q: int | None) -> str | None:
    if two_q is None:
        return None
    if two_q <= 20:
        return "twoq_low"
    if two_q <= 60:
        return "twoq_mid"
    return "twoq_high"


def derive_instance_strata(
    *,
    task_kind: str,
    graph_id: str,
    instance: Any | None,
    graph_rows: list[ScoreRow],
    method_name: str,
    baseline_key: tuple[int, int, str | None, int, int | None],
) -> dict[str, object]:
    strata: dict[str, object] = {}

    payload = getattr(instance, "payload", None) if instance is not None else None
    meta = getattr(instance, "meta", None) if instance is not None else None

    if task_kind == "maxcut":
        n_nodes = getattr(payload, "num_nodes", None)
        edges = getattr(payload, "edges", None)
        if isinstance(n_nodes, int) and n_nodes > 0:
            strata["graph_size_bucket"] = _bucket_problem_size(int(n_nodes))
        if isinstance(n_nodes, int) and n_nodes > 1 and isinstance(edges, list):
            density = (2.0 * len(edges)) / float(n_nodes * (n_nodes - 1))
            strata["edge_density_bucket"] = _bucket_density(density)
        if str(graph_id).startswith("ring"):
            strata["instance_family"] = "ring"
        elif str(graph_id).startswith("er_"):
            strata["instance_family"] = "erdos_renyi"
        else:
            strata["instance_family"] = "other_graph"
    elif task_kind == "bv":
        hidden = getattr(payload, "hidden_string", None)
        if isinstance(hidden, str) and hidden:
            strata["input_size_bucket"] = _bucket_problem_size(len(hidden))
        strata["instance_family"] = "bv"
    elif task_kind == "ghz":
        n_qubits = getattr(payload, "num_qubits", None)
        if not isinstance(n_qubits, int) and isinstance(meta, dict):
            mq = meta.get("num_qubits")
            if isinstance(mq, int):
                n_qubits = mq
        if isinstance(n_qubits, int) and n_qubits > 0:
            strata["input_size_bucket"] = _bucket_problem_size(n_qubits)
        strata["instance_family"] = "ghz"

    baseline_depth: int | None = None
    baseline_twoq: int | None = None
    for row in graph_rows:
        if row.method != method_name:
            continue
        if perturbation_key(row) != baseline_key:
            continue
        baseline_depth = int(row.transpiled_depth)
        baseline_twoq = int(row.two_qubit_count) if row.two_qubit_count is not None else None
        break
    depth_bucket = _bucket_transpiled_depth(baseline_depth)
    twoq_bucket = _bucket_two_qubit_count(baseline_twoq)
    if depth_bucket is not None:
        strata["transpiled_depth_bucket"] = depth_bucket
    if twoq_bucket is not None:
        strata["two_qubit_count_bucket"] = twoq_bucket
    if not strata:
        strata["instance_family"] = "all"
    return strata


def evaluate_auxiliary_claim_examples(
    *,
    method_scores_by_key: dict[tuple[int, int, str | None, int, int | None], dict[str, float]],
    baseline_key: tuple[int, int, str | None, int, int | None],
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    if baseline_key not in method_scores_by_key:
        return {}

    keys = sorted(method_scores_by_key)
    baseline_scores = method_scores_by_key[baseline_key]
    selected_label = sorted(baseline_scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    accepted_outcomes = []
    for key in keys:
        scores = method_scores_by_key[key]
        accepted_outcomes.append(
            decision_in_top_k(
                selected_label=selected_label,
                scores=scores,
                k=2,
                higher_is_better=True,
            )
        )
    decision_res = evaluate_decision_claim(
        accepted_outcomes,
        stability_threshold=stability_threshold,
        confidence=confidence_level,
    )

    winners: dict[tuple[int, int, str | None, int, int | None], str] = {}
    for key in keys:
        scores = method_scores_by_key[key]
        winners[key] = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    shots_values = sorted({int(k[3]) for k in keys})
    low_keys: list[tuple[int, int, str | None, int, int | None]]
    high_keys: list[tuple[int, int, str | None, int, int | None]]
    if len(shots_values) >= 2:
        low_keys = [k for k in keys if int(k[3]) == shots_values[0]]
        high_keys = [k for k in keys if int(k[3]) == shots_values[-1]]
        observed_group = f"shots={shots_values[0]}"
        reference_group = f"shots={shots_values[-1]}"
    else:
        low_keys = [k for k in keys if (int(k[4]) if k[4] is not None else 0) % 2 == 0]
        high_keys = [k for k in keys if (int(k[4]) if k[4] is not None else 0) % 2 == 1]
        observed_group = "seed_simulator_even"
        reference_group = "seed_simulator_odd"

    observed_counts: dict[str, int] = defaultdict(int)
    reference_counts: dict[str, int] = defaultdict(int)
    for k in low_keys:
        observed_counts[winners[k]] += 1
    for k in high_keys:
        reference_counts[winners[k]] += 1

    distribution_payload: dict[str, object] = {}
    if observed_counts and reference_counts:
        dist_res = evaluate_distribution_claim(
            observed_counts=observed_counts,
            reference_counts=reference_counts,
            epsilon=0.20,
            primary_distance="js",
            sanity_distance="tvd",
        )
        distribution_payload = {
            "observed_group": observed_group,
            "reference_group": reference_group,
            "observed_counts": dict(observed_counts),
            "reference_counts": dict(reference_counts),
            "epsilon": dist_res.epsilon,
            "primary_distance": dist_res.primary_distance,
            "primary_value": dist_res.primary_value,
            "primary_holds": dist_res.primary_holds,
            "sanity_distance": dist_res.sanity_distance,
            "sanity_value": dist_res.sanity_value,
            "sanity_holds": dist_res.sanity_holds,
            "distances_agree": dist_res.distances_agree,
        }

    return {
        "decision_example": {
            "selected_label": selected_label,
            "rule": "selected baseline winner remains in top-2 under perturbation",
            "accepted": decision_res.accepted,
            "total": decision_res.total,
            "acceptance_rate": decision_res.acceptance_rate,
            "ci_low": decision_res.ci_low,
            "ci_high": decision_res.ci_high,
            "decision": decision_res.decision.value,
        },
        "distribution_example": distribution_payload,
    }


def evaluate_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method_a: str,
    method_b: str,
    deltas: list[float],
    higher_is_better: bool,
    baseline_key: tuple[int, int, str | None, int, int | None],
    stability_threshold: float,
    confidence_level: float,
    top_k_unstable: int,
) -> dict[str, object]:
    direction = HigherIsBetter.YES if higher_is_better else HigherIsBetter.NO
    base_claim = RankingClaim(method_a=method_a, method_b=method_b, delta=0.0, direction=direction)

    paired_scores = collect_paired_scores(rows, method_a, method_b)
    if baseline_key not in paired_scores:
        raise ValueError(f"Baseline key missing from sampled set: {baseline_key}")

    baseline_a, baseline_b = paired_scores[baseline_key]
    perturbed_pairs = [scores for key, scores in paired_scores.items() if key != baseline_key]
    shot_values = sorted({int(key[3]) for key in paired_scores})
    seed_values = sorted({int(key[4]) for key in paired_scores if key[4] is not None})

    by_delta_flip: dict[float, list[float]] = defaultdict(list)
    by_delta_decision: dict[float, list[str]] = defaultdict(list)

    delta_sweep = []
    factor_attribution: dict[str, dict[str, object]] = {}
    lockdown_recommendation: dict[str, dict[str, object]] = {}
    conditional_stability: dict[str, list[dict[str, object]]] = {}
    flip_observations_by_delta: dict[str, list[dict[str, object]]] = {}

    for delta in deltas:
        claim = RankingClaim(
            method_a=base_claim.method_a,
            method_b=base_claim.method_b,
            delta=delta,
            direction=base_claim.direction,
        )
        summary = compute_rank_flip_summary(
            claim=claim,
            baseline_score_a=baseline_a,
            baseline_score_b=baseline_b,
            perturbed_scores=perturbed_pairs,
        )

        stable_count = summary.total - summary.flips
        estimate = estimate_binomial_rate(
            successes=stable_count,
            total=summary.total,
            confidence=confidence_level,
        )
        decision = conservative_stability_decision(
            estimate=estimate,
            stability_threshold=stability_threshold,
        ).value
        baseline_holds = claim.holds(baseline_a, baseline_b)
        baseline_relation = claim.relation(baseline_a, baseline_b)
        baseline_margin = (baseline_a - baseline_b) if higher_is_better else (baseline_b - baseline_a)
        claim_holds_count = sum(1 for pair in paired_scores.values() if claim.holds(*pair))
        claim_holds_rate = claim_holds_count / len(paired_scores) if paired_scores else 0.0

        delta_flip_observations: list[dict[str, object]] = []
        for key, (score_a, score_b) in paired_scores.items():
            if key == baseline_key:
                continue
            perturbed_relation = claim.relation(score_a, score_b)
            margin = (score_a - score_b) if higher_is_better else (score_b - score_a)
            delta_flip_observations.append(
                {
                    "seed_transpiler": int(key[0]),
                    "optimization_level": int(key[1]),
                    "layout_method": key[2],
                    "shots": int(key[3]),
                    "seed_simulator": int(key[4]) if key[4] is not None else None,
                    "baseline_relation": baseline_relation.value,
                    "perturbed_relation": perturbed_relation.value,
                    "is_flip": perturbed_relation != baseline_relation,
                    "margin": margin,
                    "margin_to_threshold": margin - float(delta),
                    "margin_shift_vs_baseline": margin - baseline_margin,
                }
            )
        flip_observations_by_delta[str(delta)] = delta_flip_observations

        delta_record = {
            "delta": delta,
            "total": summary.total,
            "flips": summary.flips,
            "flip_rate": summary.flip_rate,
            "stability_hat": estimate.rate,
            "stability_ci_low": estimate.ci_low,
            "stability_ci_high": estimate.ci_high,
            "decision": decision,
            "baseline_holds": baseline_holds,
            "baseline_relation": baseline_relation.value,
            "claim_holds_count": claim_holds_count,
            "claim_total_count": len(paired_scores),
            "claim_holds_rate": claim_holds_rate,
        }
        delta_sweep.append(delta_record)
        by_delta_flip[delta].append(summary.flip_rate)
        by_delta_decision[delta].append(decision)
        factor_attribution[str(delta)] = rank_flip_root_cause_by_dimension(
            claim=claim,
            baseline_scores=(baseline_a, baseline_b),
            baseline_key=baseline_key,
            paired_scores=paired_scores,
            top_k=top_k_unstable,
        )
        lockdown_recommendation[str(delta)] = single_knob_lockdown_recommendation(
            claim,
            paired_scores=paired_scores,
            baseline_key=baseline_key,
            global_flip_rate=summary.flip_rate,
            stability_threshold=stability_threshold,
            confidence_level=confidence_level,
            top_k=2,
        )

        constraints_to_try: list[dict[str, int | str | None]] = [{}]
        if shot_values:
            constraints_to_try.append({"shots": shot_values[-1]})
            if seed_values:
                constraints_to_try.append({"shots": shot_values[-1], "seed_simulator": seed_values[0]})
        rows_conditional: list[dict[str, object]] = []
        for constraint in constraints_to_try:
            summary_cond = conditional_rank_flip_summary(
                claim,
                paired_scores=paired_scores,
                baseline_key=baseline_key,
                constraints=constraint,
                stability_threshold=stability_threshold,
                confidence_level=confidence_level,
            )
            if summary_cond is None:
                continue
            rows_conditional.append(summary_cond)
        conditional_stability[str(delta)] = rows_conditional

    return {
        "sampled_configurations": len(paired_scores),
        "delta_sweep": delta_sweep,
        "factor_attribution": factor_attribution,
        "lockdown_recommendation": lockdown_recommendation,
        "conditional_stability": conditional_stability,
        "flip_observations_by_delta": flip_observations_by_delta,
        "by_delta_flip": by_delta_flip,
        "by_delta_decision": by_delta_decision,
        "paired_scores": paired_scores,
    }


def evaluate_decision_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method: str,
    top_k: int,
    instance_target_label: str,
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    method_rows = [row for row in rows if row.method == method]
    outcomes: list[bool] = []
    failures: list[dict[str, object]] = []
    for row in method_rows:
        counts = row.counts or {}
        try:
            accepted = decision_in_top_k(
                selected_label=instance_target_label,
                scores={str(k): float(v) for k, v in counts.items()},
                k=top_k,
                higher_is_better=True,
            )
        except ValueError:
            accepted = False
        outcomes.append(accepted)
        if not accepted:
            failures.append(
                {
                    "config": {
                        "seed_transpiler": row.seed_transpiler,
                        "optimization_level": row.optimization_level,
                        "layout_method": row.layout_method,
                        "shots": row.shots,
                        "seed_simulator": row.seed_simulator,
                    },
                    "target_label": instance_target_label,
                    "counts": counts,
                }
            )

    result = evaluate_decision_claim(
        outcomes,
        stability_threshold=stability_threshold,
        confidence=confidence_level,
    )
    return {
        "accepted": result.accepted,
        "total": result.total,
        "holds_rate": result.acceptance_rate,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "decision": result.decision.value,
        "top_failures": failures[:5],
    }


def evaluate_distribution_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method: str,
    baseline_key: tuple[int, int, str | None, int, int | None],
    key_sort_value,
    epsilon: float,
    primary_distance: str,
    sanity_distance: str,
    reference_shots: int | str | None,
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    method_rows = [row for row in rows if row.method == method and isinstance(row.counts, dict) and row.counts]
    counts_by_key: dict[tuple[int, int, str | None, int, int | None], dict[str, int]] = {}
    for row in method_rows:
        key = perturbation_key(row)
        counts_by_key[key] = {str(k): int(v) for k, v in (row.counts or {}).items()}

    if not counts_by_key:
        estimate = estimate_binomial_rate(successes=0, total=0, confidence=confidence_level)
        return {
            "accepted": 0,
            "total": 0,
            "flip_rate": 0.0,
            "holds_rate": estimate.rate,
            "ci_low": estimate.ci_low,
            "ci_high": estimate.ci_high,
            "decision": conservative_stability_decision(
                estimate=estimate,
                stability_threshold=stability_threshold,
            ).value,
            "reference_config": None,
            "reference_shots": reference_shots,
            "top_violations": [],
            "distance_observations": [],
        }

    reference_key: tuple[int, int, str | None, int, int | None] | None = None
    if isinstance(reference_shots, int):
        candidates = [key for key in counts_by_key if int(key[3]) == int(reference_shots)]
        if candidates:
            reference_key = sorted(candidates, key=key_sort_value)[0]
    elif isinstance(reference_shots, str):
        token = reference_shots.strip().lower()
        if token == "baseline" and baseline_key in counts_by_key:
            reference_key = baseline_key
        elif token == "max":
            max_shots = max(int(key[3]) for key in counts_by_key)
            candidates = [key for key in counts_by_key if int(key[3]) == max_shots]
            reference_key = sorted(candidates, key=key_sort_value)[0]

    if reference_key is None and baseline_key in counts_by_key:
        reference_key = baseline_key
    if reference_key is None:
        max_shots = max(int(key[3]) for key in counts_by_key)
        candidates = [key for key in counts_by_key if int(key[3]) == max_shots]
        reference_key = sorted(candidates, key=key_sort_value)[0]

    reference_counts = counts_by_key[reference_key]

    outcomes: list[bool] = []
    distance_rows: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []
    for key, observed_counts in counts_by_key.items():
        if key == reference_key:
            continue
        dist_res = evaluate_distribution_claim(
            observed_counts=observed_counts,
            reference_counts=reference_counts,
            epsilon=epsilon,
            primary_distance=primary_distance,
            sanity_distance=sanity_distance,
        )
        holds = bool(dist_res.primary_holds)
        outcomes.append(holds)
        obs = {
            "seed_transpiler": int(key[0]),
            "optimization_level": int(key[1]),
            "layout_method": key[2],
            "shots": int(key[3]),
            "seed_simulator": int(key[4]) if key[4] is not None else None,
            "primary_distance": dist_res.primary_distance,
            "primary_value": float(dist_res.primary_value),
            "primary_holds": bool(dist_res.primary_holds),
            "sanity_distance": dist_res.sanity_distance,
            "sanity_value": float(dist_res.sanity_value),
            "sanity_holds": bool(dist_res.sanity_holds),
            "distances_agree": bool(dist_res.distances_agree),
        }
        distance_rows.append(obs)
        if not holds:
            violations.append({**obs, "observed_counts": dict(observed_counts)})

    accepted = sum(1 for flag in outcomes if flag)
    total = len(outcomes)
    estimate = estimate_binomial_rate(successes=accepted, total=total, confidence=confidence_level)
    decision = conservative_stability_decision(
        estimate=estimate,
        stability_threshold=stability_threshold,
    ).value
    violations.sort(key=lambda row: float(row.get("primary_value", 0.0)), reverse=True)
    return {
        "accepted": accepted,
        "total": total,
        "flip_rate": (1.0 - estimate.rate) if total > 0 else 0.0,
        "holds_rate": estimate.rate,
        "ci_low": estimate.ci_low,
        "ci_high": estimate.ci_high,
        "decision": decision,
        "reference_config": {
            "seed_transpiler": int(reference_key[0]),
            "optimization_level": int(reference_key[1]),
            "layout_method": reference_key[2],
            "shots": int(reference_key[3]),
            "seed_simulator": int(reference_key[4]) if reference_key[4] is not None else None,
        },
        "reference_shots": int(reference_key[3]),
        "top_violations": violations[:5],
        "distance_observations": distance_rows,
    }
