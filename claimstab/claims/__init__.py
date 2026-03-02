# claimstab/claims/__init__.py
from .decision import DecisionClaimResult, TieBreak, decision_in_top_k, evaluate_decision_claim, top_k_labels
from .diagnostics import (
    aggregate_lockdown_recommendations,
    compute_stability_vs_shots,
    conditional_rank_flip_summary,
    minimum_shots_for_stable,
    rank_flip_root_cause_by_dimension,
    single_knob_lockdown_recommendation,
)
from .distribution import (
    DistributionClaimResult,
    evaluate_distribution_claim,
    js_distance,
    normalize_counts,
    tvd_distance,
)
from .evaluation import collect_paired_scores, perturbation_key
from .ranking import RankFlipSummary, RankingClaim, Relation, compute_rank_flip_summary
from .stability import (
    BinomialEstimate,
    StabilityDecision,
    ci_width,
    conservative_stability_decision,
    estimate_binomial_rate,
    estimate_clustered_stability,
    estimate_stability_from_outcomes,
    wilson_interval,
)

__all__ = [
    "RankingClaim",
    "Relation",
    "RankFlipSummary",
    "compute_rank_flip_summary",
    "perturbation_key",
    "collect_paired_scores",
    "StabilityDecision",
    "BinomialEstimate",
    "ci_width",
    "wilson_interval",
    "estimate_binomial_rate",
    "estimate_clustered_stability",
    "estimate_stability_from_outcomes",
    "conservative_stability_decision",
    "TieBreak",
    "DecisionClaimResult",
    "top_k_labels",
    "decision_in_top_k",
    "evaluate_decision_claim",
    "DistributionClaimResult",
    "normalize_counts",
    "tvd_distance",
    "js_distance",
    "evaluate_distribution_claim",
    "rank_flip_root_cause_by_dimension",
    "conditional_rank_flip_summary",
    "single_knob_lockdown_recommendation",
    "aggregate_lockdown_recommendations",
    "compute_stability_vs_shots",
    "minimum_shots_for_stable",
]
