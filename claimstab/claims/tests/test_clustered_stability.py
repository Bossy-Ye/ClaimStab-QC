import unittest

from claimstab.claims.ranking import RankingClaim
from claimstab.claims.stability import estimate_clustered_stability
from claimstab.runners.matrix_runner import ScoreRow


def _rows(instance_id: str, seed: int, sa: float, sb: float) -> list[ScoreRow]:
    common = dict(
        instance_id=instance_id,
        seed_transpiler=seed,
        optimization_level=1,
        transpiled_depth=4,
        transpiled_size=10,
        layout_method="sabre",
        shots=1024,
        seed_simulator=0,
    )
    return [
        ScoreRow(method="A", score=sa, **common),
        ScoreRow(method="B", score=sb, **common),
    ]


class TestClusteredStability(unittest.TestCase):
    def test_clustered_bootstrap_summary(self) -> None:
        rows = []
        # Instance 1: stable (no flips vs baseline)
        rows += _rows("g1", 0, 1.2, 1.0)
        rows += _rows("g1", 1, 1.3, 1.0)
        rows += _rows("g1", 2, 1.25, 1.0)
        # Instance 2: unstable (all flips vs baseline)
        rows += _rows("g2", 0, 1.2, 1.0)
        rows += _rows("g2", 1, 0.9, 1.0)
        rows += _rows("g2", 2, 0.85, 1.0)

        result = estimate_clustered_stability(
            rows,
            RankingClaim(method_a="A", method_b="B", delta=0.0),
            baseline_config={
                "seed_transpiler": 0,
                "optimization_level": 1,
                "layout_method": "sabre",
                "shots": 1024,
                "seed_simulator": 0,
            },
            stability_threshold=0.95,
            confidence_level=0.95,
            n_boot=500,
            seed=7,
        )

        self.assertEqual(result["n_instances_used"], 2)
        self.assertAlmostEqual(result["clustered_stability_mean"], 0.5, places=2)
        self.assertLessEqual(result["clustered_stability_ci_low"], result["clustered_stability_mean"])
        self.assertGreaterEqual(result["clustered_stability_ci_high"], result["clustered_stability_mean"])


if __name__ == "__main__":
    unittest.main()
