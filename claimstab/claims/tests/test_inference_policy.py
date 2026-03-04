import unittest

from claimstab.claims.stability import (
    BayesianBetaPolicy,
    BinomialEstimate,
    DEFAULT_INFERENCE_POLICY,
    StabilityDecision,
    evaluate_binomial_with_policy,
    resolve_inference_policy,
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

    def test_resolve_policy_by_name(self) -> None:
        wilson = resolve_inference_policy("wilson")
        self.assertEqual(wilson.name, "wilson")
        bayes = resolve_inference_policy("bayesian_beta")
        self.assertEqual(bayes.name, "bayesian_beta")
        with self.assertRaises(ValueError):
            resolve_inference_policy("unknown")

    def test_bayesian_policy_estimate(self) -> None:
        policy = BayesianBetaPolicy(prior_alpha=1.0, prior_beta=1.0)
        est = policy.estimate(successes=9, total=10, confidence=0.95)
        # Posterior mean under Beta(1,1) prior is (s+1)/(n+2).
        self.assertAlmostEqual(est.rate, 10 / 12, places=8)
        self.assertGreaterEqual(est.ci_low, 0.0)
        self.assertLessEqual(est.ci_high, 1.0)
        self.assertLessEqual(est.ci_low, est.ci_high)

    def test_evaluate_with_policy_name(self) -> None:
        estimate, decision = evaluate_binomial_with_policy(
            successes=95,
            total=100,
            confidence=0.95,
            stability_threshold=0.9,
            policy_name="bayesian_beta",
        )
        self.assertGreater(estimate.rate, 0.0)
        self.assertIn(decision, {StabilityDecision.STABLE, StabilityDecision.INCONCLUSIVE, StabilityDecision.UNSTABLE})


if __name__ == "__main__":
    unittest.main()
