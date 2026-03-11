from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claimstab.figures.plot_rq4_adaptive import plot_rq4_adaptive


class TestRQ4AdaptiveFigures(unittest.TestCase):
    def test_plot_rq4_adaptive_outputs(self) -> None:
        summary = {
            "strategies": [
                {
                    "strategy": "full_factorial",
                    "strategy_group": "full_factorial",
                    "k_used": 100,
                    "agreement_with_factorial": {"rate": 1.0},
                    "rows_by_delta": [
                        {"delta": 0.0, "n_claim_evals": 3000, "stability_ci_low": 0.80, "stability_ci_high": 0.92},
                        {"delta": 0.01, "n_claim_evals": 3000, "stability_ci_low": 0.72, "stability_ci_high": 0.88},
                    ],
                },
                {
                    "strategy": "random_k_32",
                    "strategy_group": "random_k",
                    "k_used": 32,
                    "agreement_with_factorial": {"rate": 0.5},
                    "rows_by_delta": [
                        {"delta": 0.0, "n_claim_evals": 960, "stability_ci_low": 0.72, "stability_ci_high": 0.90},
                        {"delta": 0.01, "n_claim_evals": 960, "stability_ci_low": 0.66, "stability_ci_high": 0.86},
                    ],
                },
                {
                    "strategy": "adaptive_ci",
                    "strategy_group": "adaptive_ci",
                    "k_used": 58,
                    "agreement_with_factorial": {"rate": 1.0},
                    "rows_by_delta": [
                        {"delta": 0.0, "n_claim_evals": 1740, "stability_ci_low": 0.75, "stability_ci_high": 0.89},
                        {"delta": 0.01, "n_claim_evals": 1740, "stability_ci_low": 0.69, "stability_ci_high": 0.85},
                    ],
                },
                {
                    "strategy": "adaptive_ci_tuned",
                    "strategy_group": "adaptive_ci_tuned",
                    "k_used": 42,
                    "agreement_with_factorial": {"rate": 1.0},
                    "rows_by_delta": [
                        {"delta": 0.0, "n_claim_evals": 1260, "stability_ci_low": 0.73, "stability_ci_high": 0.90},
                        {"delta": 0.01, "n_claim_evals": 1260, "stability_ci_low": 0.67, "stability_ci_high": 0.86},
                    ],
                },
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            refs = plot_rq4_adaptive(summary, Path(td))
            self.assertEqual(int(refs["points"]), 4)
            ci = refs.get("ci_width_vs_cost") or {}
            ag = refs.get("agreement_vs_cost") or {}
            self.assertTrue(Path(str(ci.get("pdf"))).exists())
            self.assertTrue(Path(str(ci.get("png"))).exists())
            self.assertTrue(Path(str(ag.get("pdf"))).exists())
            self.assertTrue(Path(str(ag.get("png"))).exists())


if __name__ == "__main__":
    unittest.main()
