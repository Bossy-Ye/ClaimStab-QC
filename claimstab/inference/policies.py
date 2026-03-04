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

