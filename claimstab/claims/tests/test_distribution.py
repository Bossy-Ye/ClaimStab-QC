import unittest

from claimstab.claims.distribution import (
    evaluate_distribution_claim,
    js_distance,
    normalize_counts,
    tvd_distance,
)


class TestDistribution(unittest.TestCase):
    def test_normalize_counts(self) -> None:
        dist = normalize_counts({"00": 2, "11": 2})
        self.assertEqual(dist["00"], 0.5)
        self.assertEqual(dist["11"], 0.5)

    def test_tvd_and_js_identical_distributions_are_zero(self) -> None:
        p = {"0": 0.5, "1": 0.5}
        q = {"0": 0.5, "1": 0.5}
        self.assertEqual(tvd_distance(p, q), 0.0)
        self.assertEqual(js_distance(p, q), 0.0)

    def test_evaluate_distribution_claim_primary_and_sanity(self) -> None:
        result = evaluate_distribution_claim(
            {"0": 90, "1": 10},
            {"0": 10, "1": 90},
            epsilon=0.2,
            primary_distance="tvd",
            sanity_distance="js",
        )
        self.assertFalse(result.primary_holds)
        self.assertFalse(result.sanity_holds)


if __name__ == "__main__":
    unittest.main()
