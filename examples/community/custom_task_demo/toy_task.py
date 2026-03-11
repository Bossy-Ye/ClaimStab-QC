from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class ToyPayload:
    num_qubits: int


class ToyTask:
    """External task plugin demo for ClaimStab.

    Supported method kinds:
    - hadamard: apply H on all qubits
    - zero: leave |0...0>
    - biased_rx: RX(theta) on all qubits (theta from method.params.theta, default pi/4)
    """

    name = "toy"

    def __init__(self, num_qubits: int = 6, num_instances: int = 3) -> None:
        self.num_qubits = int(num_qubits)
        self.num_instances = int(num_instances)

    def instances(self, suite: str) -> list[ProblemInstance]:
        # suite string kept for interface compatibility; this toy plugin uses fixed synthetic instances.
        return [
            ProblemInstance(instance_id=f"toy_{suite}_{i}", payload=ToyPayload(num_qubits=self.num_qubits))
            for i in range(self.num_instances)
        ]

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        n = int(getattr(payload, "num_qubits", self.num_qubits))

        qc = QuantumCircuit(n)
        if method.kind == "hadamard":
            qc.h(range(n))
        elif method.kind == "zero":
            pass
        elif method.kind == "biased_rx":
            theta = float(method.params.get("theta", 0.78539816339))
            qc.rx(theta, range(n))
        else:
            raise ValueError(f"ToyTask unsupported method kind: {method.kind}")

        qc.measure_all()

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total == 0:
                return 0.0
            ones = 0.0
            for bitstring, c in counts.items():
                ones += (c / total) * bitstring.count("1")
            return ones / n

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)
