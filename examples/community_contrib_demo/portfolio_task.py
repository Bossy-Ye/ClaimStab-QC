from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class PortfolioPayload:
    num_qubits: int
    weights: tuple[float, ...]


def _make_weights(instance_idx: int, num_qubits: int) -> tuple[float, ...]:
    base = [((instance_idx + 1) * (i + 3)) % 11 + 1 for i in range(num_qubits)]
    total = float(sum(base))
    return tuple(v / total for v in base)


class PortfolioAllocationTask:
    """Example external community task: weighted portfolio bit-allocation objective."""

    name = "portfolio_allocation"

    def __init__(self, num_qubits: int = 6, num_instances: int = 8) -> None:
        self.num_qubits = int(num_qubits)
        self.num_instances = int(num_instances)

    def instances(self, suite: str) -> list[ProblemInstance]:
        count = self.num_instances
        suite_name = str(suite).strip().lower()
        if suite_name == "core":
            count = min(count, 6)
        elif suite_name == "large":
            count = max(count, 12)
        out: list[ProblemInstance] = []
        for idx in range(count):
            weights = _make_weights(idx, self.num_qubits)
            out.append(
                ProblemInstance(
                    instance_id=f"portfolio_{suite}_{idx}",
                    payload=PortfolioPayload(num_qubits=self.num_qubits, weights=weights),
                    meta={"instance_type": "community_portfolio"},
                )
            )
        return out

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, PortfolioPayload):
            raise ValueError("PortfolioAllocationTask got unsupported payload.")
        n = payload.num_qubits
        weights = payload.weights
        qc = QuantumCircuit(n)

        if method.kind == "uniform_mix":
            qc.h(range(n))
        elif method.kind == "conservative":
            theta = float(method.params.get("theta", 0.9))
            qc.ry(theta, range(n))
        elif method.kind == "risk_aware":
            theta_high = float(method.params.get("theta_high", 1.8))
            theta_low = float(method.params.get("theta_low", 0.8))
            threshold = sorted(weights)[len(weights) // 2]
            for q, w in enumerate(weights):
                qc.ry(theta_high if w >= threshold else theta_low, q)
        else:
            raise ValueError(f"Unsupported method kind: {method.kind}")

        qc.measure_all()

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total == 0:
                return 0.0
            score = 0.0
            for bitstring, c in counts.items():
                prob = c / total
                # Qiskit bitstrings are high->low; map qubit q to index n-1-q.
                weighted_ones = 0.0
                for q, w in enumerate(weights):
                    if bitstring[n - 1 - q] == "1":
                        weighted_ones += w
                score += prob * weighted_ones
            return score

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)
