from __future__ import annotations

import unittest

from claimstab.baselines.naive import compare_naive_vs_claimstab, evaluate_naive_baseline


class TestNaiveBaseline(unittest.TestCase):
    def test_compare_overclaim(self) -> None:
        label = compare_naive_vs_claimstab(
            naive_result=True,
            claimstab_decision="inconclusive",
            claimstab_ci_low=0.8,
            claimstab_ci_high=0.98,
            threshold=0.95,
        )
        self.assertEqual(label, "naive_overclaim")

    def test_compare_underclaim(self) -> None:
        label = compare_naive_vs_claimstab(
            naive_result=False,
            claimstab_decision="stable",
            claimstab_ci_low=0.96,
            claimstab_ci_high=0.99,
            threshold=0.95,
        )
        self.assertEqual(label, "naive_underclaim")

    def test_evaluate_returns_baseline_config(self) -> None:
        payload = evaluate_naive_baseline(
            claim_type="ranking",
            baseline_holds=True,
            claimstab_decision="stable",
            stability_ci_low=0.96,
            stability_ci_high=0.99,
            threshold=0.95,
        )
        self.assertIn("baseline_config", payload)
        self.assertEqual(payload["comparison"], "agree")


if __name__ == "__main__":
    unittest.main()
