from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.instances import ProblemInstance
from claimstab.tasks.registry import register_task


@dataclass(frozen=True)
class GHZInstance:
    num_qubits: int


class GHZStructuralTaskPlugin:
    """
    Circuit-level structural benchmark based on GHZ state preparation.

    This task is intentionally compilation-focused:
    - `ghz_linear` uses nearest-neighbor CNOT chain.
    - `ghz_star` uses star CNOT pattern from qubit 0.

    On line-like coupling maps, these methods induce different transpilation
    overhead (depth / 2Q count), which makes them suitable for structural claims.
    """

    name = "ghz"

    def __init__(
        self,
        *,
        min_qubits: int = 6,
        max_qubits: int = 12,
        step: int = 2,
    ) -> None:
        if min_qubits < 2:
            raise TaskSpecError("GHZ task requires min_qubits >= 2.")
        if max_qubits < min_qubits:
            raise TaskSpecError("GHZ task requires max_qubits >= min_qubits.")
        if step <= 0:
            raise TaskSpecError("GHZ task requires step > 0.")
        self.min_qubits = int(min_qubits)
        self.max_qubits = int(max_qubits)
        self.step = int(step)

    def instances(self, suite: str) -> list[ProblemInstance]:
        key = suite.strip().lower()
        if key in {"core", "toy"}:
            qubits = [self.min_qubits, min(self.min_qubits + self.step, self.max_qubits)]
        elif key in {"standard"}:
            qubits = list(range(self.min_qubits, min(self.max_qubits, self.min_qubits + 4 * self.step) + 1, self.step))
        elif key in {"large"}:
            qubits = list(range(self.min_qubits, self.max_qubits + 1, self.step))
        else:
            qubits = [self.min_qubits, min(self.min_qubits + self.step, self.max_qubits)]

        out: list[ProblemInstance] = []
        for idx, n in enumerate(sorted(set(int(q) for q in qubits if int(q) >= 2))):
            out.append(
                ProblemInstance(
                    instance_id=f"ghz_n{n}_{idx}",
                    payload=GHZInstance(num_qubits=n),
                    meta={"num_qubits": n},
                )
            )
        return out

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, GHZInstance):
            raise TaskSpecError("GHZ task received unsupported instance payload.")
        n = payload.num_qubits

        if method.kind == "ghz_linear":
            qc = self._build_ghz_linear(n)
        elif method.kind == "ghz_star":
            qc = self._build_ghz_star(n)
        elif method.kind in {"random", "random_baseline"}:
            qc = self._build_random_baseline(n)
        else:
            raise TaskSpecError(f"GHZ task does not support method kind '{method.kind}'.")

        target_zero = "0" * n
        target_one = "1" * n

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total <= 0:
                return 0.0
            # GHZ support mass: probability on |0...0> or |1...1>.
            return float(counts.get(target_zero, 0) + counts.get(target_one, 0)) / float(total)

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)

    @staticmethod
    def _build_ghz_linear(num_qubits: int) -> QuantumCircuit:
        qc = QuantumCircuit(num_qubits, num_qubits)
        qc.h(0)
        for q in range(num_qubits - 1):
            qc.cx(q, q + 1)
        qc.measure(range(num_qubits), range(num_qubits))
        return qc

    @staticmethod
    def _build_ghz_star(num_qubits: int) -> QuantumCircuit:
        qc = QuantumCircuit(num_qubits, num_qubits)
        qc.h(0)
        for q in range(1, num_qubits):
            qc.cx(0, q)
        qc.measure(range(num_qubits), range(num_qubits))
        return qc

    @staticmethod
    def _build_random_baseline(num_qubits: int) -> QuantumCircuit:
        qc = QuantumCircuit(num_qubits, num_qubits)
        for q in range(num_qubits):
            qc.h(q)
        qc.measure(range(num_qubits), range(num_qubits))
        return qc


register_task("ghz", GHZStructuralTaskPlugin)

