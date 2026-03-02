import unittest

from claimstab.claims.decision import (
    TieBreak,
    decision_in_top_k,
    evaluate_decision_claim,
    top_k_labels,
)
from claimstab.claims.stability import StabilityDecision


class TestDecision(unittest.TestCase):
    def test_top_k_labels_lexicographic_tie_break(self) -> None:
        labels = top_k_labels(
            {"B": 0.9, "A": 0.9, "C": 0.4},
            k=1,
            higher_is_better=True,
            tie_break=TieBreak.LEXICOGRAPHIC,
        )
        self.assertEqual(labels, ["A"])

    def test_decision_in_top_k(self) -> None:
        scores = {"A": 0.8, "B": 0.7, "C": 0.6}
        self.assertTrue(decision_in_top_k("B", scores, k=2))
        self.assertFalse(decision_in_top_k("C", scores, k=2))

    def test_evaluate_decision_claim_returns_conservative_status(self) -> None:
        result = evaluate_decision_claim(
            [True] * 8 + [False] * 2,
            stability_threshold=0.95,
            confidence=0.95,
        )
        self.assertIn(
            result.decision,
            {
                StabilityDecision.UNSTABLE,
                StabilityDecision.INCONCLUSIVE,
            },
        )


if __name__ == "__main__":
    unittest.main()
