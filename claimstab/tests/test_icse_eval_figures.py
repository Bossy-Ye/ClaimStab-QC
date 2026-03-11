from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from claimstab.figures.icse_eval import (
    plot_claim_distribution,
    plot_cost_confidence_tradeoff,
    plot_space_flip_rate,
    plot_stability_profile,
    save_publication_figure,
)


class TestICSEEvalFigures(unittest.TestCase):
    def test_stability_profile_and_space_flip_rate(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "claim_pair": "A>B",
                    "space_preset": "compilation_only",
                    "delta": 0.0,
                    "flip_rate_mean": 0.04,
                    "stability_hat": 0.97,
                    "stability_ci_low": 0.95,
                    "stability_ci_high": 0.99,
                    "decision": "stable",
                },
                {
                    "claim_pair": "A>B",
                    "space_preset": "combined_light",
                    "delta": 0.0,
                    "flip_rate_mean": 0.13,
                    "stability_hat": 0.87,
                    "stability_ci_low": 0.83,
                    "stability_ci_high": 0.91,
                    "decision": "unstable",
                },
                {
                    "claim_pair": "A>B",
                    "space_preset": "sampling_only",
                    "delta": 0.0,
                    "flip_rate_mean": 0.24,
                    "stability_hat": 0.74,
                    "stability_ci_low": 0.68,
                    "stability_ci_high": 0.79,
                    "decision": "unstable",
                },
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fig1 = plot_stability_profile(df)
            refs1 = save_publication_figure(fig1, root / "figure1")
            self.assertTrue(Path(str(refs1["pdf"])).exists())
            self.assertTrue(Path(str(refs1["svg"])).exists())
            self.assertTrue(Path(str(refs1["png"])).exists())

            fig2 = plot_space_flip_rate(df)
            refs2 = save_publication_figure(fig2, root / "figure2")
            self.assertTrue(Path(str(refs2["pdf"])).exists())
            self.assertTrue(Path(str(refs2["svg"])).exists())
            self.assertTrue(Path(str(refs2["png"])).exists())

    def test_claim_distribution_and_cost_confidence(self) -> None:
        dist = pd.DataFrame(
            [
                {"task": "MaxCut", "decision": "unstable"},
                {"task": "MaxCut", "decision": "unstable"},
                {"task": "GHZ", "decision": "stable"},
                {"task": "BV", "decision": "stable"},
                {"task": "Grover", "decision": "unstable"},
            ]
        )
        tradeoff = pd.DataFrame(
            [
                {"strategy": "full_factorial", "cost": 495, "ci_width": 0.0825},
                {"strategy": "random_k_32", "cost": 155, "ci_width": 0.1454},
                {"strategy": "random_k_64", "cost": 315, "ci_width": 0.1036},
                {"strategy": "adaptive_ci", "cost": 495, "ci_width": 0.0825},
                {"strategy": "adaptive_ci_tuned", "cost": 320, "ci_width": 0.1026},
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            refs3 = save_publication_figure(plot_claim_distribution(dist), root / "figure3")
            refs4 = save_publication_figure(plot_cost_confidence_tradeoff(tradeoff), root / "figure4")
            self.assertTrue(Path(str(refs3["pdf"])).exists())
            self.assertTrue(Path(str(refs3["svg"])).exists())
            self.assertTrue(Path(str(refs4["png"])).exists())


if __name__ == "__main__":
    unittest.main()
