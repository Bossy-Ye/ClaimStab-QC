from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from claimstab.runners.matrix_runner import ScoreRow

PerturbationKey = Tuple[int, int, str | None, int, int | None]
ScorePair = Tuple[float, float]


def perturbation_key(row: ScoreRow) -> PerturbationKey:
    return (
        row.seed_transpiler,
        row.optimization_level,
        row.layout_method,
        row.shots,
        row.seed_simulator,
    )


def collect_paired_scores(
    rows: List[ScoreRow],
    method_a: str,
    method_b: str,
) -> Dict[PerturbationKey, ScorePair]:
    by_key: Dict[PerturbationKey, Dict[str, float]] = defaultdict(dict)
    for row in rows:
        by_key[perturbation_key(row)][row.method] = row.score

    paired: Dict[PerturbationKey, ScorePair] = {}
    for key, method_scores in by_key.items():
        if method_a not in method_scores or method_b not in method_scores:
            raise ValueError(f"Missing method scores for key={key}; got methods={sorted(method_scores)}")
        paired[key] = (method_scores[method_a], method_scores[method_b])

    return paired
