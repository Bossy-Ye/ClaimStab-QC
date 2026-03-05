from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claimstab.figures.robustness import plot_rq5_robustness_map, plot_rq6_decision_counts, plot_rq7_top_main_effects


class TestRobustnessFigures(unittest.TestCase):
    def test_plot_rq5_robustness_map(self) -> None:
        payload = {
            "experiments": [
                {
                    "overall": {
                        "conditional_robustness": {
                            "cells_by_delta": {
                                "0.0": [
                                    {"decision": "stable"},
                                    {"decision": "unstable"},
                                ],
                                "0.05": [
                                    {"decision": "unstable"},
                                    {"decision": "unstable"},
                                    {"decision": "inconclusive"},
                                ],
                            }
                        }
                    }
                }
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "rq5"
            ref = plot_rq5_robustness_map(payload, out)
            self.assertIsNotNone(ref)
            assert ref is not None
            self.assertTrue(Path(ref["png"]).exists())
            self.assertTrue(Path(ref["pdf"]).exists())

    def test_plot_rq6_decision_counts(self) -> None:
        rq6 = {
            "decision_counts": {
                "stable": 5,
                "unstable": 3,
                "inconclusive": 2,
            }
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "rq6"
            ref = plot_rq6_decision_counts(rq6, out)
            self.assertIsNotNone(ref)
            assert ref is not None
            self.assertTrue(Path(ref["png"]).exists())
            self.assertTrue(Path(ref["pdf"]).exists())

    def test_plot_rq7_top_main_effects(self) -> None:
        rq7 = {
            "top_main_effects": [
                {"dimension": "shots_bucket", "effect_score": 0.8},
                {"dimension": "layout_method", "effect_score": 0.2},
                {"dimension": "seed_simulator", "effect_score": 0.05},
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "rq7"
            ref = plot_rq7_top_main_effects(rq7, out)
            self.assertIsNotNone(ref)
            assert ref is not None
            self.assertTrue(Path(ref["png"]).exists())
            self.assertTrue(Path(ref["pdf"]).exists())


if __name__ == "__main__":
    unittest.main()
