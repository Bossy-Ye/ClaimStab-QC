from __future__ import annotations

from dataclasses import dataclass


NAIVE_BASELINE_CONFIG = {
    "seed_transpiler": 0,
    "optimization_level": 1,
    "layout_method": "trivial",
    "shots": 1024,
    "seed_simulator": 0,
}


@dataclass(frozen=True)
class NaiveComparison:
    claim_type: str
    baseline_config: dict[str, int | str]
    naive_holds: bool
    comparison: str

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_type": self.claim_type,
            "baseline_config": dict(self.baseline_config),
            "naive_holds": self.naive_holds,
            "comparison": self.comparison,
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
    claimstab_decision: str,
    stability_ci_low: float,
    stability_ci_high: float,
    threshold: float,
) -> dict[str, object]:
    comparison = compare_naive_vs_claimstab(
        naive_result=bool(baseline_holds),
        claimstab_decision=str(claimstab_decision),
        claimstab_ci_low=float(stability_ci_low),
        claimstab_ci_high=float(stability_ci_high),
        threshold=float(threshold),
    )
    return NaiveComparison(
        claim_type=str(claim_type),
        baseline_config=dict(NAIVE_BASELINE_CONFIG),
        naive_holds=bool(baseline_holds),
        comparison=comparison,
    ).to_dict()
