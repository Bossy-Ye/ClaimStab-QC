from __future__ import annotations

import math
import unittest

from claimstab.analysis.rq import build_rq_summary


class TestRQ2Attribution(unittest.TestCase):
    def test_std_driver_score_highlights_shots_dependency(self) -> None:
        payload = {
            "meta": {"task": "maxcut"},
            "comparative": {"space_claim_delta": []},
            "experiments": [
                {
                    "overall": {
                        "diagnostics": {
                            "by_delta_dimension": {
                                "0.0": {
                                    "shots": {
                                        "64": {"flips": 100, "total": 100},
                                        "256": {"flips": 50, "total": 100},
                                        "1024": {"flips": 0, "total": 100},
                                    },
                                    "seed_transpiler": {
                                        "0": {"flips": 75, "total": 150},
                                        "1": {"flips": 75, "total": 150},
                                    },
                                }
                            }
                        }
                    }
                }
            ],
        }

        rq = build_rq_summary(payload)
        rows = rq["rq2_drivers"]["all_dimensions"]
        by_dim = {str(row["dimension"]): row for row in rows}

        self.assertIn("shots", by_dim)
        self.assertIn("seed_transpiler", by_dim)

        shots_score = float(by_dim["shots"]["driver_score"])
        seed_score = float(by_dim["seed_transpiler"]["driver_score"])
        expected_shots_std = math.sqrt(1.0 / 6.0)

        self.assertAlmostEqual(shots_score, expected_shots_std, places=6)
        self.assertAlmostEqual(seed_score, 0.0, places=12)
        self.assertGreater(shots_score, seed_score + 0.3)
        self.assertAlmostEqual(
            float(by_dim["shots"]["flip_rate"]),
            float(by_dim["seed_transpiler"]["flip_rate"]),
            places=12,
        )
        self.assertEqual(rq["rq2_drivers"]["metric_name"], "std_flip_rate_across_values")


if __name__ == "__main__":
    unittest.main()
