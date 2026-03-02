# claimstab/claims/ranking.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HigherIsBetter(Enum):
    """Monotonicity of the evaluation metric."""
    YES = "higher_is_better"
    NO = "lower_is_better"


class Relation(str, Enum):
    A_GT_B = "A_GT_B"
    A_EQ_B = "A_EQ_B"
    A_LT_B = "A_LT_B"


@dataclass(frozen=True)
class RankingClaim:
    """
    Paper-level ranking claim.

    A ranking claim asserts that method A outranks method B under an evaluation
    metric m(.), up to a practical margin delta.

    Formalization (higher-is-better case):
        holds  <=>  m(A) >= m(B) + delta

    If lower-is-better:
        holds  <=>  m(A) <= m(B) - delta

    Notes:
    - This claim is *paper-level*: it is evaluated over observed outcomes,
      not over internal circuit structure.
    - delta encodes a *practical significance* threshold (delta=0 => non-strict ordering).
    """

    method_a: str
    method_b: str
    delta: float = 0.0
    direction: HigherIsBetter = HigherIsBetter.YES

    def holds(self, score_a: float, score_b: float) -> bool:
        """Return True iff the claim holds given two scalar scores."""
        if self.direction == HigherIsBetter.YES:
            return score_a >= score_b + self.delta
        else:
            return score_a <= score_b - self.delta

    def relation(self, score_a: float, score_b: float) -> Relation:
        """
        Return a 3-way relation among {A_GT_B, A_EQ_B, A_LT_B}
        under the claim's delta semantics.
        """
        if self.direction == HigherIsBetter.YES:
            if score_a >= score_b + self.delta:
                return Relation.A_GT_B
            if score_b >= score_a + self.delta:
                return Relation.A_LT_B
            return Relation.A_EQ_B
        else:
            # lower is better
            if score_a <= score_b - self.delta:
                return Relation.A_GT_B  # A better than B
            if score_b <= score_a - self.delta:
                return Relation.A_LT_B
            return Relation.A_EQ_B


@dataclass(frozen=True)
class RankFlip:
    """
    A rank flip event for a given perturbation configuration.

    Interpretation:
      - baseline_relation is baseline relation under delta semantics
      - perturbed_relation is perturbed relation under delta semantics
      - flip = relation change

    This is the atomic unit used to compute rank-flip rate.
    """
    baseline_relation: Relation
    perturbed_relation: Relation

    @property
    def flipped(self) -> bool:
        return self.baseline_relation != self.perturbed_relation


@dataclass(frozen=True)
class RankFlipSummary:
    """
    Aggregate stability summary for a RankingClaim over a perturbation set.
    """
    total: int
    flips: int

    @property
    def flip_rate(self) -> float:
        return 0.0 if self.total == 0 else self.flips / self.total


def compute_rank_flip_summary(
    claim: RankingClaim,
    baseline_score_a: float,
    baseline_score_b: float,
    perturbed_scores: list[tuple[float, float]],
) -> RankFlipSummary:
    """
    Compute rank-flip summary over a list of perturbed (score_a, score_b).

    Day-1 usage:
      - baseline is typically one chosen configuration (e.g., seed=0,opt=0)
      - perturbed_scores are outcomes under other (seed,opt) configs
    """
    baseline_relation = claim.relation(baseline_score_a, baseline_score_b)

    flips = 0
    for sa, sb in perturbed_scores:
        if claim.relation(sa, sb) != baseline_relation:
            flips += 1

    return RankFlipSummary(total=len(perturbed_scores), flips=flips)
