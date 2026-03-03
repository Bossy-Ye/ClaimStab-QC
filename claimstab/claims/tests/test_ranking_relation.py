import unittest

from claimstab.claims.ranking import HigherIsBetter, RankingClaim, Relation, compute_rank_flip_summary


class TestRankingRelation(unittest.TestCase):
    def test_relation_three_way_higher_is_better(self) -> None:
        claim = RankingClaim(method_a="A", method_b="B", delta=0.1, direction=HigherIsBetter.YES)
        self.assertEqual(claim.relation(1.2, 1.0), Relation.A_GT_B)
        self.assertEqual(claim.relation(1.0, 1.2), Relation.A_LT_B)
        self.assertEqual(claim.relation(1.05, 1.0), Relation.A_EQ_B)

    def test_relation_three_way_lower_is_better(self) -> None:
        claim = RankingClaim(method_a="A", method_b="B", delta=0.1, direction=HigherIsBetter.NO)
        self.assertEqual(claim.relation(0.8, 1.0), Relation.A_GT_B)
        self.assertEqual(claim.relation(1.1, 1.0), Relation.A_LT_B)
        self.assertEqual(claim.relation(0.95, 1.0), Relation.A_EQ_B)

    def test_flip_uses_relation_change(self) -> None:
        claim = RankingClaim(method_a="A", method_b="B", delta=0.1)
        summary = compute_rank_flip_summary(
            claim=claim,
            baseline_score_a=1.2,
            baseline_score_b=1.0,  # baseline: A_GT_B
            perturbed_scores=[
                (1.05, 1.0),  # A_EQ_B -> flip
                (1.2, 1.0),   # A_GT_B -> no flip
            ],
        )
        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.flips, 1)

    def test_larger_delta_can_reduce_near_tie_flips(self) -> None:
        baseline = (1.01, 1.00)
        perturbed = [(1.00, 1.01)]
        d0 = RankingClaim(method_a="A", method_b="B", delta=0.0)
        d2 = RankingClaim(method_a="A", method_b="B", delta=0.02)
        s0 = compute_rank_flip_summary(d0, baseline[0], baseline[1], perturbed)
        s2 = compute_rank_flip_summary(d2, baseline[0], baseline[1], perturbed)
        self.assertGreaterEqual(s0.flip_rate, s2.flip_rate)


if __name__ == "__main__":
    unittest.main()
