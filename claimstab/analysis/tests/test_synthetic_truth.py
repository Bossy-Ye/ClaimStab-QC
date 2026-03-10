from __future__ import annotations

import unittest

from claimstab.analysis.synthetic_truth import run_truth_grid, simulate_truth_profile


class TestSyntheticTruth(unittest.TestCase):
    def test_ci_width_shrinks_with_more_samples(self) -> None:
        low_n = simulate_truth_profile(true_stability=0.95, n_evals=32, trials=250, seed=5)
        high_n = simulate_truth_profile(true_stability=0.95, n_evals=256, trials=250, seed=5)
        self.assertGreater(float(low_n["mean_ci_width"]), float(high_n["mean_ci_width"]))

    def test_stable_rate_monotone_with_true_stability(self) -> None:
        weak = simulate_truth_profile(true_stability=0.85, n_evals=256, trials=300, seed=7)
        near = simulate_truth_profile(true_stability=0.95, n_evals=256, trials=300, seed=7)
        strong = simulate_truth_profile(true_stability=0.99, n_evals=256, trials=300, seed=7)
        self.assertLess(float(weak["decision_rates"]["stable"]), float(near["decision_rates"]["stable"]))
        self.assertLess(float(near["decision_rates"]["stable"]), float(strong["decision_rates"]["stable"]))

    def test_grid_contains_expected_rows(self) -> None:
        summary = run_truth_grid(
            true_stabilities=[0.9, 0.95],
            n_values=[64, 128],
            trials=100,
            seed=11,
        )
        rows = summary.get("rows", [])
        self.assertEqual(len(rows), 4)
        signatures = {(float(row["true_stability"]), int(row["n_evals"])) for row in rows}
        self.assertIn((0.9, 64), signatures)
        self.assertIn((0.95, 128), signatures)


if __name__ == "__main__":
    unittest.main()
