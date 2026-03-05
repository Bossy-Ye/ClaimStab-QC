from __future__ import annotations

import unittest

import pandas as pd

from claimstab.figures.attribution import _select_attribution_metric


class TestAttributionFigure(unittest.TestCase):
    def test_prefers_driver_score_when_available(self) -> None:
        frame = pd.DataFrame(
            {
                "dimension": ["shots", "seed_transpiler"],
                "flip_rate": [0.2, 0.2],
                "driver_score": [0.4, 0.0],
            }
        )
        metric_col, metric_label = _select_attribution_metric(frame)
        self.assertEqual(metric_col, "driver_score")
        self.assertIn("std of flip rate", metric_label)

    def test_fallback_uses_flip_rate_from_counts(self) -> None:
        frame = pd.DataFrame(
            {
                "dimension": ["shots"],
                "flips": [1],
                "total": [4],
            }
        )
        metric_col, _ = _select_attribution_metric(frame)
        self.assertEqual(metric_col, "flip_rate")
        self.assertAlmostEqual(float(frame.loc[0, "flip_rate"]), 0.25, places=8)


if __name__ == "__main__":
    unittest.main()
