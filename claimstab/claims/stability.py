from __future__ import annotations

from random import Random
from typing import Any, Mapping, Sequence

from claimstab.claims.evaluation import PerturbationKey, collect_paired_scores
from claimstab.claims.ranking import RankingClaim
from claimstab.inference.policies import (
    BinomialEstimate,
    InferencePolicy,
    StabilityDecision,
    WilsonInferencePolicy,
    ci_width,
    conservative_stability_decision,
    estimate_binomial_rate,
    estimate_stability_from_outcomes,
    wilson_interval,
)
from claimstab.runners.matrix_runner import ScoreRow

DEFAULT_INFERENCE_POLICY: InferencePolicy = WilsonInferencePolicy()


def evaluate_binomial_with_policy(
    *,
    successes: int,
    total: int,
    confidence: float,
    stability_threshold: float,
    policy: InferencePolicy | None = None,
) -> tuple[BinomialEstimate, StabilityDecision]:
    """
    Policy-pluggable inference entrypoint.

    Backward compatibility:
    - if no policy is given, defaults to WilsonInferencePolicy.
    """
    active = policy or DEFAULT_INFERENCE_POLICY
    estimate = active.estimate(successes=successes, total=total, confidence=confidence)
    decision = active.decide(estimate=estimate, stability_threshold=stability_threshold)
    return estimate, decision


def estimate_clustered_stability(
    score_rows: Sequence[ScoreRow],
    claim: RankingClaim,
    baseline_config: PerturbationKey | Mapping[str, int | str | None],
    *,
    stability_threshold: float,
    confidence_level: float,
    n_boot: int = 2000,
    seed: int = 0,
) -> dict[str, Any]:
    if n_boot <= 0:
        raise ValueError("n_boot must be > 0")

    if isinstance(baseline_config, tuple):
        baseline_key = baseline_config
    else:
        baseline_key = (
            int(baseline_config["seed_transpiler"]),
            int(baseline_config["optimization_level"]),
            str(baseline_config["layout_method"]) if baseline_config["layout_method"] is not None else None,
            int(baseline_config["shots"]),
            int(baseline_config["seed_simulator"]) if baseline_config["seed_simulator"] is not None else None,
        )

    rows_by_instance: dict[str, list[ScoreRow]] = {}
    for row in score_rows:
        rows_by_instance.setdefault(row.instance_id, []).append(row)

    per_instance_stability: list[float] = []
    used_instances = 0
    for instance_rows in rows_by_instance.values():
        paired = collect_paired_scores(instance_rows, claim.method_a, claim.method_b)
        if baseline_key not in paired:
            continue
        baseline_relation = claim.relation(*paired[baseline_key])
        flips = 0
        total = 0
        for key, pair in paired.items():
            if key == baseline_key:
                continue
            total += 1
            if claim.relation(*pair) != baseline_relation:
                flips += 1
        if total == 0:
            continue
        used_instances += 1
        per_instance_stability.append(1.0 - flips / total)

    if not per_instance_stability:
        return {
            "clustered_stability_mean": 0.0,
            "clustered_stability_ci_low": 0.0,
            "clustered_stability_ci_high": 1.0,
            "clustered_decision": StabilityDecision.INCONCLUSIVE.value,
            "n_instances_used": 0,
            "n_boot": n_boot,
        }

    mean_stability = sum(per_instance_stability) / len(per_instance_stability)
    rng = Random(seed)
    boot_means: list[float] = []
    n = len(per_instance_stability)
    for _ in range(n_boot):
        sample = [per_instance_stability[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    alpha = 1.0 - confidence_level
    lo_idx = max(0, int((alpha / 2.0) * (n_boot - 1)))
    hi_idx = min(n_boot - 1, int((1.0 - alpha / 2.0) * (n_boot - 1)))
    ci_low = boot_means[lo_idx]
    ci_high = boot_means[hi_idx]

    estimate = BinomialEstimate(
        successes=0,
        total=0,
        rate=mean_stability,
        ci_low=ci_low,
        ci_high=ci_high,
        confidence=confidence_level,
    )
    decision = conservative_stability_decision(estimate=estimate, stability_threshold=stability_threshold).value
    return {
        "clustered_stability_mean": mean_stability,
        "clustered_stability_ci_low": ci_low,
        "clustered_stability_ci_high": ci_high,
        "clustered_decision": decision,
        "n_instances_used": used_instances,
        "n_boot": n_boot,
    }
