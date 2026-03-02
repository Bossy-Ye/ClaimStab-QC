import unittest

from claimstab.claims.diagnostics import (
    aggregate_lockdown_recommendations,
    conditional_rank_flip_summary,
    rank_flip_root_cause_by_dimension,
    single_knob_lockdown_recommendation,
)
from claimstab.claims.ranking import RankingClaim


class TestDiagnostics(unittest.TestCase):
    def test_rank_flip_root_cause_by_dimension_counts_flips(self) -> None:
        claim = RankingClaim(method_a="A", method_b="B", delta=0.0)
        baseline_key = (0, 0, "trivial", 1024, 0)
        paired_scores = {
            baseline_key: (1.0, 0.5),  # claim holds
            (1, 0, "trivial", 1024, 0): (0.1, 0.5),  # flip
            (2, 0, "sabre", 1024, 0): (2.0, 0.5),  # no flip
        }

        diag = rank_flip_root_cause_by_dimension(
            claim,
            baseline_scores=paired_scores[baseline_key],
            baseline_key=baseline_key,
            paired_scores=paired_scores,
        )

        self.assertEqual(diag["total"], 2)
        self.assertEqual(diag["flips"], 1)
        self.assertEqual(diag["by_dimension"]["seed_transpiler"]["1"]["flips"], 1)
        self.assertEqual(diag["by_dimension"]["layout_method"]["trivial"]["total"], 1)
        self.assertIn("top_flip_configs", diag)
        self.assertEqual(len(diag["top_flip_configs"]), 1)
        self.assertEqual(diag["top_flip_configs"][0]["config"]["seed_transpiler"], 1)

    def test_conditional_summary_and_lockdown_recommendation(self) -> None:
        claim = RankingClaim(method_a="A", method_b="B", delta=0.0)
        baseline_key = (0, 0, "trivial", 16, 0)
        paired_scores = {
            baseline_key: (1.0, 0.5),
            (0, 0, "trivial", 16, 1): (0.2, 0.5),
            (0, 0, "trivial", 1024, 0): (1.1, 0.5),
            (0, 0, "trivial", 1024, 1): (1.2, 0.5),
        }
        cond = conditional_rank_flip_summary(
            claim,
            paired_scores=paired_scores,
            baseline_key=baseline_key,
            constraints={"shots": 1024},
            stability_threshold=0.95,
            confidence_level=0.95,
        )
        self.assertIsNotNone(cond)
        self.assertEqual(cond["constraints"]["shots"], 1024)
        self.assertEqual(cond["flips"], 0)

        rec = single_knob_lockdown_recommendation(
            claim,
            paired_scores=paired_scores,
            baseline_key=baseline_key,
            global_flip_rate=1.0 / 3.0,
            stability_threshold=0.95,
            confidence_level=0.95,
            top_k=1,
        )
        self.assertEqual(rec["candidate_count"] > 0, True)
        self.assertEqual(len(rec["top_recommendations"]), 1)
        self.assertIn("flip_rate_improvement", rec["top_recommendations"][0])

    def test_aggregate_lockdown_recommendations(self) -> None:
        rows = aggregate_lockdown_recommendations(
            [
                {
                    "top_recommendations": [
                        {
                            "dimension": "shots",
                            "value": 1024,
                            "flip_rate_improvement": 0.3,
                            "flip_rate": 0.1,
                            "stability_hat": 0.9,
                        }
                    ]
                },
                {
                    "top_recommendations": [
                        {
                            "dimension": "shots",
                            "value": 1024,
                            "flip_rate_improvement": 0.2,
                            "flip_rate": 0.2,
                            "stability_hat": 0.8,
                        }
                    ]
                },
            ],
            top_k=1,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dimension"], "shots")
        self.assertEqual(rows[0]["value"], 1024)
        self.assertAlmostEqual(rows[0]["avg_flip_rate_improvement"], 0.25)


if __name__ == "__main__":
    unittest.main()
