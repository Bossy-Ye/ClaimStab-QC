from __future__ import annotations

import unittest

from claimstab.analysis.sanity import compare_delta_sweeps, mutate_ranking_rows, summarize_ranking_rows_by_graph
from claimstab.runners.matrix_runner import ScoreRow


def _score_row(
    *,
    instance_id: str,
    method: str,
    score: float,
    seed_transpiler: int,
    shots: int = 1024,
) -> ScoreRow:
    return ScoreRow(
        instance_id=instance_id,
        seed_transpiler=seed_transpiler,
        optimization_level=1,
        transpiled_depth=8,
        transpiled_size=8,
        method=method,
        metric_name="objective",
        score=score,
        layout_method="trivial",
        seed_simulator=0,
        shots=shots,
    )


class TestSanityHelpers(unittest.TestCase):
    def test_baseline_relation_flip_reduces_stability(self) -> None:
        baseline_key = (0, 1, "trivial", 1024, 0, None, None)
        rows_by_graph = {
            "g1": [
                _score_row(instance_id="g1", method="MethodA", score=0.90, seed_transpiler=0),
                _score_row(instance_id="g1", method="MethodB", score=0.50, seed_transpiler=0),
                _score_row(instance_id="g1", method="MethodA", score=0.88, seed_transpiler=1),
                _score_row(instance_id="g1", method="MethodB", score=0.52, seed_transpiler=1),
                _score_row(instance_id="g1", method="MethodA", score=0.86, seed_transpiler=2),
                _score_row(instance_id="g1", method="MethodB", score=0.51, seed_transpiler=2),
                _score_row(instance_id="g1", method="MethodA", score=0.87, seed_transpiler=3),
                _score_row(instance_id="g1", method="MethodB", score=0.50, seed_transpiler=3),
                _score_row(instance_id="g1", method="MethodA", score=0.89, seed_transpiler=4),
                _score_row(instance_id="g1", method="MethodB", score=0.53, seed_transpiler=4),
                _score_row(instance_id="g1", method="MethodA", score=0.85, seed_transpiler=5),
                _score_row(instance_id="g1", method="MethodB", score=0.54, seed_transpiler=5),
                _score_row(instance_id="g1", method="MethodA", score=0.84, seed_transpiler=6),
                _score_row(instance_id="g1", method="MethodB", score=0.52, seed_transpiler=6),
            ]
        }

        original = summarize_ranking_rows_by_graph(
            rows_by_graph=rows_by_graph,
            method_a="MethodA",
            method_b="MethodB",
            deltas=[0.0, 0.1],
            higher_is_better=True,
            baseline_key=baseline_key,
            stability_threshold=0.5,
            confidence_level=0.95,
        )
        mutated_rows, mutation_meta = mutate_ranking_rows(
            rows_by_graph=rows_by_graph,
            method_a="MethodA",
            method_b="MethodB",
            baseline_key=baseline_key,
            deltas=[0.0, 0.1],
            higher_is_better=True,
            mutation_kind="baseline_relation_flip",
        )
        mutated = summarize_ranking_rows_by_graph(
            rows_by_graph=mutated_rows,
            method_a="MethodA",
            method_b="MethodB",
            deltas=[0.0, 0.1],
            higher_is_better=True,
            baseline_key=baseline_key,
            stability_threshold=0.5,
            confidence_level=0.95,
        )
        transitions = compare_delta_sweeps(original["delta_sweep"], mutated["delta_sweep"])

        self.assertEqual(mutation_meta.get("kind"), "baseline_relation_flip")
        self.assertEqual(original["delta_sweep"][0]["decision"], "stable")
        self.assertEqual(mutated["delta_sweep"][0]["decision"], "unstable")
        self.assertTrue(any(bool(row.get("mutated_less_stable")) for row in transitions))


if __name__ == "__main__":
    unittest.main()
