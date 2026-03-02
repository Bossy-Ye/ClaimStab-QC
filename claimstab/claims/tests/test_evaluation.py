import unittest

from claimstab.claims.evaluation import collect_paired_scores
from claimstab.runners.matrix_runner import ScoreRow


def _row(method: str, score: float, layout: str) -> ScoreRow:
    return ScoreRow(
        instance_id="g1",
        seed_transpiler=0,
        optimization_level=0,
        transpiled_depth=1,
        transpiled_size=1,
        method=method,
        score=score,
        seed_simulator=0,
        shots=1024,
        layout_method=layout,
    )


class TestEvaluation(unittest.TestCase):
    def test_collect_paired_scores_keeps_layout_dimension(self) -> None:
        rows = [
            _row("A", 1.0, "trivial"),
            _row("B", 0.5, "trivial"),
            _row("A", 2.0, "sabre"),
            _row("B", 1.5, "sabre"),
        ]

        paired = collect_paired_scores(rows, "A", "B")

        self.assertEqual(len(paired), 2)
        self.assertEqual(paired[(0, 0, "trivial", 1024, 0)], (1.0, 0.5))
        self.assertEqual(paired[(0, 0, "sabre", 1024, 0)], (2.0, 1.5))

    def test_collect_paired_scores_requires_both_methods(self) -> None:
        rows = [_row("A", 1.0, "trivial")]

        with self.assertRaises(ValueError):
            collect_paired_scores(rows, "A", "B")


if __name__ == "__main__":
    unittest.main()
