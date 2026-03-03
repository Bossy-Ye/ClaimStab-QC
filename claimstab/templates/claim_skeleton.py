"""Template: add a new claim evaluator.

Copy this file and register/import alongside existing claim modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate


@dataclass(frozen=True)
class MyClaim:
    name: str
    threshold: float

    def holds(self, observed_value: float) -> bool:
        """Return True if claim holds for one run outcome."""
        raise NotImplementedError


def evaluate_my_claim(outcomes: Iterable[float], *, stability_threshold: float, confidence: float) -> dict[str, float | str]:
    vals = list(outcomes)
    total = len(vals)
    holds = sum(1 for v in vals if MyClaim(name="my_claim", threshold=0.0).holds(v))

    estimate = estimate_binomial_rate(successes=holds, total=total, confidence=confidence)
    decision = conservative_stability_decision(estimate=estimate, stability_threshold=stability_threshold)

    return {
        "total": total,
        "holds": holds,
        "stability_hat": estimate.rate,
        "stability_ci_low": estimate.ci_low,
        "stability_ci_high": estimate.ci_high,
        "decision": decision.value,
    }
