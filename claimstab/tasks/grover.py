from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.instances import ProblemInstance
from claimstab.tasks.registry import register_task


@dataclass(frozen=True)
class GroverInstance:
    num_qubits: int
    marked_state: str
    iterations: int


def _suite_target_count(suite: str) -> int:
    key = suite.strip().lower()
    if key in {"core", "toy"}:
        return 8
    if key in {"standard"}:
        return 12
    if key in {"large"}:
        return 16
    return 8


def _deterministic_marked_state(num_qubits: int, index: int) -> str:
    modulus = 1 << num_qubits
    value = (index * 7 + num_qubits * 3 + 1) % modulus
    if value == 0:
        value = 1
    return format(value, f"0{num_qubits}b")


def _default_iterations(num_qubits: int) -> int:
    ideal = max(1, int(round((pi / 4.0) * sqrt(float(1 << num_qubits)) - 0.5)))
    # Keep runtime practical while preserving Grover-like amplification behavior.
    return max(1, min(ideal, 2))


class GroverTaskPlugin:
    """Built-in Grover task plugin for distribution-claim stress tests."""

    name = "grover"

    def __init__(
        self,
        *,
        min_qubits: int = 6,
        max_qubits: int = 10,
        instances_per_qubit: int = 3,
    ) -> None:
        if min_qubits <= 0 or max_qubits < min_qubits:
            raise TaskSpecError("Grover task requires 0 < min_qubits <= max_qubits.")
        if instances_per_qubit <= 0:
            raise TaskSpecError("Grover task requires instances_per_qubit > 0.")
        self.min_qubits = int(min_qubits)
        self.max_qubits = int(max_qubits)
        self.instances_per_qubit = int(instances_per_qubit)

    def instances(self, suite: str) -> list[ProblemInstance]:
        target = _suite_target_count(suite)
        n_values = list(range(self.min_qubits, self.max_qubits + 1))
        if not n_values:
            raise TaskSpecError("Grover task has empty qubit range.")
        out: list[ProblemInstance] = []
        idx = 0
        while len(out) < target:
            n = n_values[idx % len(n_values)]
            local_idx = idx // len(n_values)
            if local_idx >= self.instances_per_qubit:
                local_idx = local_idx % self.instances_per_qubit
            marked = _deterministic_marked_state(n, index=local_idx + 1)
            payload = GroverInstance(
                num_qubits=n,
                marked_state=marked,
                iterations=_default_iterations(n),
            )
            out.append(
                ProblemInstance(
                    instance_id=f"grover_n{n}_{len(out)}",
                    payload=payload,
                    meta={"target_label": marked, "num_qubits": n},
                )
            )
            idx += 1
        return out

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, GroverInstance):
            raise TaskSpecError("Grover task received unsupported instance payload.")
        n = int(payload.num_qubits)
        marked = str(payload.marked_state)

        if method.kind in {"grover", "grover_oracle"}:
            iterations = int(method.params.get("iterations", payload.iterations))
            circuit = self._build_grover_circuit(n, marked_state=marked, iterations=max(1, iterations))
        elif method.kind in {"uniform", "random", "random_baseline"}:
            circuit = self._build_uniform_circuit(n)
        else:
            raise TaskSpecError(f"Grover task does not support method kind '{method.kind}'.")

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(int(v) for v in counts.values())
            if total <= 0:
                return 0.0
            return float(int(counts.get(marked, 0))) / float(total)

        return BuiltWorkflow(circuit=circuit, metric_fn=metric_fn)

    @staticmethod
    def _build_uniform_circuit(num_qubits: int) -> QuantumCircuit:
        qc = QuantumCircuit(num_qubits, num_qubits)
        qc.h(range(num_qubits))
        qc.measure(range(num_qubits), range(num_qubits))
        return qc

    def _build_grover_circuit(self, num_qubits: int, *, marked_state: str, iterations: int) -> QuantumCircuit:
        qc = QuantumCircuit(num_qubits, num_qubits)
        qc.h(range(num_qubits))
        for _ in range(iterations):
            self._apply_phase_oracle(qc, marked_state=marked_state)
            self._apply_diffusion(qc, num_qubits=num_qubits)
        qc.measure(range(num_qubits), range(num_qubits))
        return qc

    @staticmethod
    def _apply_phase_oracle(qc: QuantumCircuit, *, marked_state: str) -> None:
        n = len(marked_state)
        for q, bit in enumerate(reversed(marked_state)):
            if bit == "0":
                qc.x(q)
        if n == 1:
            qc.z(0)
        else:
            target = n - 1
            controls = list(range(n - 1))
            qc.h(target)
            qc.mcx(controls, target)
            qc.h(target)
        for q, bit in enumerate(reversed(marked_state)):
            if bit == "0":
                qc.x(q)

    @staticmethod
    def _apply_diffusion(qc: QuantumCircuit, *, num_qubits: int) -> None:
        qc.h(range(num_qubits))
        qc.x(range(num_qubits))
        if num_qubits == 1:
            qc.z(0)
        else:
            target = num_qubits - 1
            controls = list(range(num_qubits - 1))
            qc.h(target)
            qc.mcx(controls, target)
            qc.h(target)
        qc.x(range(num_qubits))
        qc.h(range(num_qubits))


register_task("grover", GroverTaskPlugin)
