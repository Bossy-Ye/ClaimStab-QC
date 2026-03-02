from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ClaimSpec:
    method_a: str
    method_b: str
    delta: float


@dataclass(frozen=True)
class BaselineSpec:
    seed_transpiler: int
    optimization_level: int
    layout_method: str
    shots: int
    seed_simulator: int


@dataclass(frozen=True)
class GraphSummary:
    total: int
    flips: int
    flip_rate: float


@dataclass(frozen=True)
class ClaimEvaluationResult:
    claim: ClaimSpec
    baseline: BaselineSpec
    perturbation_space_size: int
    per_graph: Dict[str, GraphSummary]
    overall: Dict[str, float | int]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["per_graph"] = {k: asdict(v) for k, v in self.per_graph.items()}
        return payload
