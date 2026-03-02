import unittest

from claimstab.claims.stability import (
    StabilityDecision,
    ci_width,
    conservative_stability_decision,
    estimate_binomial_rate,
)


class TestStability(unittest.TestCase):
    def test_conservative_decision_stable(self) -> None:
        estimate = estimate_binomial_rate(successes=99, total=100, confidence=0.95)
        decision = conservative_stability_decision(estimate=estimate, stability_threshold=0.9)
        self.assertEqual(decision, StabilityDecision.STABLE)

    def test_conservative_decision_inconclusive(self) -> None:
        estimate = estimate_binomial_rate(successes=93, total=100, confidence=0.95)
        decision = conservative_stability_decision(estimate=estimate, stability_threshold=0.95)
        self.assertEqual(decision, StabilityDecision.INCONCLUSIVE)

    def test_conservative_decision_unstable(self) -> None:
        estimate = estimate_binomial_rate(successes=60, total=100, confidence=0.95)
        decision = conservative_stability_decision(estimate=estimate, stability_threshold=0.95)
        self.assertEqual(decision, StabilityDecision.UNSTABLE)

    def test_ci_width_non_negative(self) -> None:
        estimate = estimate_binomial_rate(successes=60, total=100, confidence=0.95)
        self.assertGreaterEqual(ci_width(estimate), 0.0)


if __name__ == "__main__":
    unittest.main()
