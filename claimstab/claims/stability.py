from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import sqrt
from random import Random
from statistics import NormalDist
from typing import Any, Mapping, Sequence

from claimstab.claims.evaluation import PerturbationKey, collect_paired_scores
from claimstab.claims.ranking import RankingClaim
from claimstab.runners.matrix_runner import ScoreRow


class StabilityDecision(str, Enum):
    STABLE = "stable"
    UNSTABLE = "unstable"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class BinomialEstimate:
    successes: int
    total: int
    rate: float
    ci_low: float
    ci_high: float
    confidence: float



def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0,1), got {confidence}")
    if total < 0:
        raise ValueError(f"total must be >=0, got {total}")
    if successes < 0 or successes > total:
        raise ValueError(f"successes must satisfy 0 <= successes <= total, got {successes}/{total}")

    if total == 0:
        return 0.0, 1.0

    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    phat = successes / total

    z2_over_n = (z * z) / total
    denom = 1.0 + z2_over_n

    center = (phat + z2_over_n / 2.0) / denom
    margin = (z / denom) * sqrt((phat * (1.0 - phat) / total) + (z * z) / (4.0 * total * total))

    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return low, high



def estimate_binomial_rate(successes: int, total: int, confidence: float = 0.95) -> BinomialEstimate:
    low, high = wilson_interval(successes=successes, total=total, confidence=confidence)
    rate = 0.0 if total == 0 else successes / total
    return BinomialEstimate(
        successes=successes,
        total=total,
        rate=rate,
        ci_low=low,
        ci_high=high,
        confidence=confidence,
    )


def ci_width(estimate: BinomialEstimate) -> float:
    return max(0.0, estimate.ci_high - estimate.ci_low)



def estimate_stability_from_outcomes(outcomes: Sequence[bool], confidence: float = 0.95) -> BinomialEstimate:
    successes = sum(1 for x in outcomes if x)
    total = len(outcomes)
    return estimate_binomial_rate(successes=successes, total=total, confidence=confidence)



def conservative_stability_decision(
    estimate: BinomialEstimate,
    stability_threshold: float,
) -> StabilityDecision:
    if not 0.0 <= stability_threshold <= 1.0:
        raise ValueError(f"stability_threshold must be in [0,1], got {stability_threshold}")

    if estimate.ci_low >= stability_threshold:
        return StabilityDecision.STABLE
    if estimate.ci_high < stability_threshold:
        return StabilityDecision.UNSTABLE
    return StabilityDecision.INCONCLUSIVE


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
