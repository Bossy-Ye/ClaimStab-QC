import unittest

from claimstab.claims.stability import (
    BinomialEstimate,
    DEFAULT_INFERENCE_POLICY,
    StabilityDecision,
    evaluate_binomial_with_policy,
)


class _AlwaysInconclusivePolicy:
    name = "always_inconclusive"

    def interval(self, successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
        return (0.4, 0.6)

    def estimate(self, successes: int, total: int, confidence: float = 0.95) -> BinomialEstimate:
        return BinomialEstimate(
            successes=successes,
            total=total,
            rate=0.5,
            ci_low=0.4,
            ci_high=0.6,
            confidence=confidence,
        )

    def decide(self, estimate: BinomialEstimate, stability_threshold: float) -> StabilityDecision:
        return StabilityDecision.INCONCLUSIVE


class TestInferencePolicy(unittest.TestCase):
    def test_default_policy_is_wilson(self) -> None:
        estimate, decision = evaluate_binomial_with_policy(
            successes=95,
            total=100,
            confidence=0.95,
            stability_threshold=0.9,
            policy=None,
        )
        self.assertEqual(DEFAULT_INFERENCE_POLICY.name, "wilson")
        self.assertGreaterEqual(estimate.rate, 0.95)
        self.assertIn(decision, {StabilityDecision.STABLE, StabilityDecision.INCONCLUSIVE})

    def test_custom_policy_is_respected(self) -> None:
        estimate, decision = evaluate_binomial_with_policy(
            successes=100,
            total=100,
            confidence=0.95,
            stability_threshold=0.95,
            policy=_AlwaysInconclusivePolicy(),
        )
        self.assertEqual(estimate.ci_low, 0.4)
        self.assertEqual(estimate.ci_high, 0.6)
        self.assertEqual(decision, StabilityDecision.INCONCLUSIVE)


if __name__ == "__main__":
    unittest.main()
