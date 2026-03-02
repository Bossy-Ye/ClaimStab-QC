# claimstab/tasks/maxcut.py
from __future__ import annotations

from typing import Callable, Dict, Tuple

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector

from claimstab.tasks.graphs import GraphInstance
from claimstab.tasks.instances import ProblemInstance

Counts = Dict[str, int]


class MaxCutTask:
    """
    MaxCut task adapter for ClaimStab-QC.

    Day-2 change:
      - graph is injected (GraphInstance)
      - graph_id stored for paper-facing outputs
    """

    def __init__(self, instance: ProblemInstance) -> None:
        graph: GraphInstance = instance.payload
        self.instance_id = instance.instance_id
        self.graph = graph
        self.num_qubits = graph.num_nodes
        self.edges = graph.edges

    def build(self, method) -> Tuple[QuantumCircuit, Callable[[Counts], float]]:
        if method.kind == "qaoa":
            circuit = self._build_qaoa_circuit(p=method.p)
            metric_fn = self._expectation_metric
            return circuit, metric_fn

        if method.kind == "random":
            circuit = self._build_random_baseline()
            metric_fn = self._expectation_metric
            return circuit, metric_fn

        raise ValueError(f"Unknown method kind: {method.kind}")

    def _build_qaoa_circuit(self, p: int) -> QuantumCircuit:
        qc = QuantumCircuit(self.num_qubits)

        # initial state |+>^n
        qc.h(range(self.num_qubits))

        # one gamma/beta per layer
        gammas = ParameterVector("gamma", length=p)
        betas = ParameterVector("beta", length=p)

        for layer in range(p):
            gamma = gammas[layer]
            beta = betas[layer]

            # ---- Cost unitary for MaxCut: ZZ interactions on edges
            for (i, j) in self.edges:
                # Option A (preferred if available): direct ZZ rotation
                qc.rzz(2 * gamma, i, j)

                # Option B (equivalent decomposition), if you prefer:
                # qc.cx(i, j)
                # qc.rz(2 * gamma, j)
                # qc.cx(i, j)

            # ---- Mixer unitary: X rotations
            qc.rx(2 * beta, range(self.num_qubits))

        # Day-2: fixed parameters (no optimizer), but now correct shape for p layers
        # You can pick any fixed values; below repeats your old ones per layer.
        bind = {}
        for layer in range(p):
            bind[gammas[layer]] = 0.8
            bind[betas[layer]] = 0.4

        qc = qc.assign_parameters(bind)
        qc.measure_all()
        return qc

    def _build_random_baseline(self) -> QuantumCircuit:
        qc = QuantumCircuit(self.num_qubits)
        for i in range(self.num_qubits):
            qc.h(i)
        qc.measure_all()
        return qc

    def _expectation_metric(self, counts: Counts) -> float:
        total = sum(counts.values())
        if total == 0:
            return 0.0

        exp = 0.0
        for bitstring, c in counts.items():
            exp += (c / total) * self._cut_value(bitstring)
        return exp

    def _cut_value(self, bitstring: str) -> int:
        bits = list(map(int, bitstring[::-1]))  # Qiskit endianness
        value = 0
        for (i, j) in self.edges:
            if bits[i] != bits[j]:
                value += 1
        return value