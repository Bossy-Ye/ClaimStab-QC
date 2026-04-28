from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import sqrt
from statistics import NormalDist
from typing import Protocol, Sequence


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


class InferencePolicy(Protocol):
    name: str

    def interval(self, successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
        ...

    def estimate(self, successes: int, total: int, confidence: float = 0.95) -> BinomialEstimate:
        ...

    def decide(self, estimate: BinomialEstimate, stability_threshold: float) -> StabilityDecision:
        ...


class WilsonInferencePolicy:
    """Default conservative binomial inference policy based on Wilson CI."""

    name = "wilson"

    def interval(self, successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
        return wilson_interval(successes=successes, total=total, confidence=confidence)

    def estimate(self, successes: int, total: int, confidence: float = 0.95) -> BinomialEstimate:
        return estimate_binomial_rate(successes=successes, total=total, confidence=confidence)

    def decide(self, estimate: BinomialEstimate, stability_threshold: float) -> StabilityDecision:
        return conservative_stability_decision(estimate=estimate, stability_threshold=stability_threshold)


class BayesianBetaPolicy:
    """
    Bayesian beta-binomial policy using a normal approximation around posterior mean.

    Notes:
    - Prior defaults to Beta(1, 1) (uniform).
    - Interval is an approximate equal-tail credible interval.
    """

    name = "bayesian_beta"

    def __init__(self, *, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> None:
        if prior_alpha <= 0.0 or prior_beta <= 0.0:
            raise ValueError("prior_alpha and prior_beta must be > 0")
        self.prior_alpha = float(prior_alpha)
        self.prior_beta = float(prior_beta)

    def interval(self, successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
        if not 0.0 < confidence < 1.0:
            raise ValueError(f"confidence must be in (0,1), got {confidence}")
        if total < 0:
            raise ValueError(f"total must be >=0, got {total}")
        if successes < 0 or successes > total:
            raise ValueError(f"successes must satisfy 0 <= successes <= total, got {successes}/{total}")

        alpha_post = self.prior_alpha + successes
        beta_post = self.prior_beta + (total - successes)
        denom = alpha_post + beta_post
        mean = alpha_post / denom
        var = (alpha_post * beta_post) / ((denom * denom) * (denom + 1.0))
        z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
        margin = z * sqrt(max(var, 0.0))
        low = max(0.0, mean - margin)
        high = min(1.0, mean + margin)
        return low, high

    def estimate(self, successes: int, total: int, confidence: float = 0.95) -> BinomialEstimate:
        low, high = self.interval(successes=successes, total=total, confidence=confidence)
        alpha_post = self.prior_alpha + successes
        beta_post = self.prior_beta + (total - successes)
        rate = alpha_post / (alpha_post + beta_post)
        return BinomialEstimate(
            successes=successes,
            total=total,
            rate=rate,
            ci_low=low,
            ci_high=high,
            confidence=confidence,
        )

    def decide(self, estimate: BinomialEstimate, stability_threshold: float) -> StabilityDecision:
        return conservative_stability_decision(estimate=estimate, stability_threshold=stability_threshold)


def resolve_inference_policy(
    name: str | None,
    *,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> InferencePolicy:
    key = (name or "wilson").strip().lower()
    if key == "wilson":
        return WilsonInferencePolicy()
    if key == "bayesian_beta":
        return BayesianBetaPolicy(prior_alpha=prior_alpha, prior_beta=prior_beta)
    raise ValueError(f"Unknown inference policy '{name}'. Use one of: wilson, bayesian_beta")


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


def wilson_ci_proportion(k: int, n: int, z: float = 1.96) -> dict[str, float | int]:
    """
    Repository mapping note:
    - revision instructions referenced `audit/inference/wilson_ci.py`
    - this repository centralizes Wilson helpers in `claimstab/inference/policies.py`

    Compute a Wilson confidence interval for a proportion k / n.
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    if k < 0 or k > n:
        raise ValueError(f"k must satisfy 0 <= k <= n, got {k}/{n}")
    p_hat = k / n
    denominator = 1.0 + z**2 / n
    center = (p_hat + z**2 / (2.0 * n)) / denominator
    margin = (z * sqrt((p_hat * (1.0 - p_hat) / n) + (z**2 / (4.0 * n**2)))) / denominator
    return {
        "point_estimate": round(p_hat, 4),
        "ci_low": round(center - margin, 4),
        "ci_high": round(center + margin, 4),
        "ci_width": round(2.0 * margin, 4),
        "n": n,
        "k": k,
    }


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


def ci_width(estimate: BinomialEstimate) -> float:
    return max(0.0, estimate.ci_high - estimate.ci_low)
