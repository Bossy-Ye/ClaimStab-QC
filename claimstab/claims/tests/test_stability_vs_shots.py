import unittest

from claimstab.claims.diagnostics import compute_stability_vs_shots, minimum_shots_for_stable
from claimstab.runners.matrix_runner import ScoreRow


def _score_pair_rows(
    *,
    instance_id: str,
    seed_transpiler: int,
    shots: int,
    seed_simulator: int,
    score_a: float,
    score_b: float,
) -> list[ScoreRow]:
    common = dict(
        instance_id=instance_id,
        seed_transpiler=seed_transpiler,
        optimization_level=1,
        transpiled_depth=8,
        transpiled_size=12,
        layout_method="sabre",
        seed_simulator=seed_simulator,
        shots=shots,
    )
    return [
        ScoreRow(method="A", score=score_a, **common),
        ScoreRow(method="B", score=score_b, **common),
    ]


def _synthetic_rows_for_shot(
    *,
    instance_id: str,
    shots: int,
    total_evals: int,
    flips: int,
) -> list[ScoreRow]:
    rows: list[ScoreRow] = []
    rows.extend(
        _score_pair_rows(
            instance_id=instance_id,
            seed_transpiler=0,
            shots=shots,
            seed_simulator=0,
            score_a=1.0,
            score_b=0.0,
        )
    )
    for idx in range(1, total_evals + 1):
        if idx <= flips:
            score_a, score_b = 0.0, 1.0
        else:
            score_a, score_b = 1.0, 0.0
        rows.extend(
            _score_pair_rows(
                instance_id=instance_id,
                seed_transpiler=idx,
                shots=shots,
                seed_simulator=idx,
                score_a=score_a,
                score_b=score_b,
            )
        )
    return rows


class TestStabilityVsShots(unittest.TestCase):
    def test_minimum_shots_for_stable_detected(self) -> None:
        rows = []
        rows.extend(_synthetic_rows_for_shot(instance_id="g1", shots=256, total_evals=10, flips=2))
        rows.extend(_synthetic_rows_for_shot(instance_id="g1", shots=1024, total_evals=300, flips=2))

        shot_rows = compute_stability_vs_shots(
            rows,
            claim_spec={"method_a": "A", "method_b": "B", "delta": 0.0},
            baseline_config={
                "seed_transpiler": 0,
                "optimization_level": 1,
                "layout_method": "sabre",
                "shots": 256,
                "seed_simulator": 0,
            },
            threshold=0.95,
            confidence_level=0.95,
        )

        self.assertEqual([int(r["shots"]) for r in shot_rows], [256, 1024])
        self.assertNotEqual(shot_rows[0]["decision"], "stable")
        self.assertEqual(shot_rows[1]["decision"], "stable")
        self.assertEqual(minimum_shots_for_stable(shot_rows), 1024)

    def test_decision_uses_ci_low_not_point_estimate(self) -> None:
        rows = _synthetic_rows_for_shot(instance_id="g1", shots=1024, total_evals=20, flips=1)

        shot_rows = compute_stability_vs_shots(
            rows,
            claim_spec={"method_a": "A", "method_b": "B", "delta": 0.0},
            baseline_config={
                "seed_transpiler": 0,
                "optimization_level": 1,
                "layout_method": "sabre",
                "shots": 1024,
                "seed_simulator": 0,
            },
            threshold=0.95,
            confidence_level=0.95,
        )

        self.assertEqual(len(shot_rows), 1)
        row = shot_rows[0]
        self.assertGreaterEqual(float(row["stability_hat"]), 0.95)
        self.assertLess(float(row["stability_ci_low"]), 0.95)
        self.assertNotEqual(row["decision"], "stable")

    def test_single_point_case_returns_none_when_not_stable(self) -> None:
        rows = _synthetic_rows_for_shot(instance_id="g1", shots=1024, total_evals=10, flips=2)

        shot_rows = compute_stability_vs_shots(
            rows,
            claim_spec={"method_a": "A", "method_b": "B", "delta": 0.0},
            baseline_config={
                "seed_transpiler": 0,
                "optimization_level": 1,
                "layout_method": "sabre",
                "shots": 1024,
                "seed_simulator": 0,
            },
            threshold=0.95,
            confidence_level=0.95,
        )

        self.assertEqual(len(shot_rows), 1)
        self.assertNotEqual(shot_rows[0]["decision"], "stable")
        self.assertIsNone(minimum_shots_for_stable(shot_rows))


if __name__ == "__main__":
    unittest.main()
