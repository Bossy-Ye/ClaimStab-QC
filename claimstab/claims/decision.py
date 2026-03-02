from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from claimstab.claims.stability import (
    BinomialEstimate,
    StabilityDecision,
    conservative_stability_decision,
    estimate_stability_from_outcomes,
)


class TieBreak(str, Enum):
    LEXICOGRAPHIC = "lexicographic"


@dataclass(frozen=True)
class DecisionClaimResult:
    acceptance_rate: float
    ci_low: float
    ci_high: float
    decision: StabilityDecision
    accepted: int
    total: int



def top_k_labels(
    scores: Mapping[str, float],
    *,
    k: int,
    higher_is_better: bool = True,
    tie_break: TieBreak = TieBreak.LEXICOGRAPHIC,
) -> list[str]:
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    if not scores:
        raise ValueError("scores must not be empty")
    if tie_break != TieBreak.LEXICOGRAPHIC:
        raise ValueError(f"Unsupported tie_break: {tie_break}")

    sign = -1.0 if higher_is_better else 1.0
    ordered = sorted(scores.items(), key=lambda kv: (sign * kv[1], kv[0]))
    k_eff = min(k, len(ordered))
    return [label for label, _ in ordered[:k_eff]]



def decision_in_top_k(
    selected_label: str,
    scores: Mapping[str, float],
    *,
    k: int,
    higher_is_better: bool = True,
    tie_break: TieBreak = TieBreak.LEXICOGRAPHIC,
) -> bool:
    return selected_label in set(
        top_k_labels(
            scores,
            k=k,
            higher_is_better=higher_is_better,
            tie_break=tie_break,
        )
    )



def evaluate_decision_claim(
    accepted_outcomes: Sequence[bool],
    *,
    stability_threshold: float,
    confidence: float = 0.95,
) -> DecisionClaimResult:
    estimate: BinomialEstimate = estimate_stability_from_outcomes(
        outcomes=accepted_outcomes,
        confidence=confidence,
    )
    decision = conservative_stability_decision(
        estimate=estimate,
        stability_threshold=stability_threshold,
    )
    return DecisionClaimResult(
        acceptance_rate=estimate.rate,
        ci_low=estimate.ci_low,
        ci_high=estimate.ci_high,
        decision=decision,
        accepted=estimate.successes,
        total=estimate.total,
    )
