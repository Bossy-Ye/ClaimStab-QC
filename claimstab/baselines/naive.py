from __future__ import annotations

from dataclasses import dataclass


NAIVE_BASELINE_CONFIG = {
    "seed_transpiler": 0,
    "optimization_level": 1,
    "layout_method": "trivial",
    "shots": 1024,
    "seed_simulator": 0,
}
NAIVE_POLICY_LEGACY = "legacy_strict_all"
NAIVE_POLICY_REALISTIC = "default_researcher_v1"
NAIVE_POLICY_DEFAULT = NAIVE_POLICY_LEGACY
DEFAULT_ACCEPTANCE_THRESHOLD = 2.0 / 3.0


@dataclass(frozen=True)
class NaiveComparison:
    claim_type: str
    baseline_config: dict[str, int | str]
    naive_holds: bool
    comparison: str
    naive_policy: str
    naive_holds_rate: float
    naive_sample_size: int
    naive_acceptance_threshold: float

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_type": self.claim_type,
            "baseline_config": dict(self.baseline_config),
            "naive_holds": self.naive_holds,
            "comparison": self.comparison,
            "naive_policy": self.naive_policy,
            "naive_holds_rate": self.naive_holds_rate,
            "naive_sample_size": self.naive_sample_size,
            "naive_acceptance_threshold": self.naive_acceptance_threshold,
        }


def compare_naive_vs_claimstab(
    *,
    naive_result: bool,
    claimstab_decision: str,
    claimstab_ci_low: float,
    claimstab_ci_high: float,
    threshold: float,
) -> str:
    _ = (claimstab_ci_low, claimstab_ci_high, threshold)
    if naive_result and claimstab_decision in {"unstable", "inconclusive"}:
        return "naive_overclaim"
    if (not naive_result) and claimstab_decision == "stable":
        return "naive_underclaim"
    if claimstab_decision in {"stable", "unstable", "inconclusive"}:
        return "agree"
    return "naive_uninformative"


def evaluate_naive_baseline(
    *,
    claim_type: str,
    baseline_holds: bool,
    baseline_holds_successes: int | None = None,
    baseline_holds_total: int | None = None,
    claimstab_decision: str,
    stability_ci_low: float,
    stability_ci_high: float,
    threshold: float,
    naive_policy: str = NAIVE_POLICY_DEFAULT,
    naive_acceptance_threshold: float = DEFAULT_ACCEPTANCE_THRESHOLD,
) -> dict[str, object]:
    sample_size = int(baseline_holds_total) if baseline_holds_total is not None and int(baseline_holds_total) > 0 else 1
    if baseline_holds_successes is None:
        successes = sample_size if baseline_holds else 0
    else:
        successes = int(baseline_holds_successes)
    successes = max(0, min(successes, sample_size))
    hold_rate = float(successes / sample_size) if sample_size > 0 else (1.0 if baseline_holds else 0.0)

    if naive_policy == NAIVE_POLICY_REALISTIC and sample_size > 1:
        naive_result = hold_rate >= float(naive_acceptance_threshold)
    elif naive_policy == NAIVE_POLICY_REALISTIC:
        naive_result = bool(baseline_holds)
    else:
        # Legacy baseline semantics: strict "all baseline checks must hold".
        naive_result = bool(baseline_holds)

    comparison = compare_naive_vs_claimstab(
        naive_result=bool(naive_result),
        claimstab_decision=str(claimstab_decision),
        claimstab_ci_low=float(stability_ci_low),
        claimstab_ci_high=float(stability_ci_high),
        threshold=float(threshold),
    )
    return NaiveComparison(
        claim_type=str(claim_type),
        baseline_config=dict(NAIVE_BASELINE_CONFIG),
        naive_holds=bool(naive_result),
        comparison=comparison,
        naive_policy=str(naive_policy),
        naive_holds_rate=hold_rate,
        naive_sample_size=sample_size,
        naive_acceptance_threshold=float(naive_acceptance_threshold),
    ).to_dict()
