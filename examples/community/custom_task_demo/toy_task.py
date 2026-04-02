from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class ToyTaskConfig:
    num_qubits: int = 4
    num_instances: int = 2


class ToyTask:
    name = "toy"

    def __init__(self, num_qubits: int = 4, num_instances: int = 2) -> None:
        self.config = ToyTaskConfig(
            num_qubits=max(1, int(num_qubits)),
            num_instances=max(1, int(num_instances)),
        )

    def instances(self, suite: str) -> list[ProblemInstance]:
        return [
            ProblemInstance(
                instance_id=f"{suite}_{idx}",
                payload={"instance_index": idx, "num_qubits": self.config.num_qubits},
                meta={"suite": suite},
            )
            for idx in range(self.config.num_instances)
        ]

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        num_qubits = int(instance.payload.get("num_qubits", self.config.num_qubits))
        circuit = QuantumCircuit(num_qubits, num_qubits)

        kind = str(method.kind)
        if kind == "hadamard":
            for qubit in range(num_qubits):
                circuit.h(qubit)
        elif kind == "biased_rx":
            theta = float(method.params.get("theta", 1.0))
            for qubit in range(num_qubits):
                circuit.rx(theta, qubit)
        elif kind == "zero":
            pass
        else:
            raise ValueError(f"Unsupported toy-task method kind: {kind}")

        circuit.measure(range(num_qubits), range(num_qubits))

        def metric_fn(counts: dict[str, int]) -> float:
            # Reward richer observed support so HadamardAll outranks ZeroState in expectation.
            populated = sum(1 for shots in counts.values() if int(shots) > 0)
            total = max(1, len(counts))
            return float(populated) / float(total)

        return BuiltWorkflow(circuit=circuit, metric_fn=metric_fn)
