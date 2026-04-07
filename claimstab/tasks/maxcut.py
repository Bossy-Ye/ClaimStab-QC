# claimstab/tasks/maxcut.py
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, Tuple

from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.space import PerturbationConfig
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.graphs import GraphInstance
from claimstab.tasks.instances import ProblemInstance
from claimstab.tasks.suites import load_suite

Counts = Dict[str, int]


@dataclass(frozen=True)
class MaxCutHybridInitPolicy:
    enabled: bool = False
    init_strategies: tuple[str, ...] = ("fixed",)
    init_seeds: tuple[int, ...] = (0,)

    @staticmethod
    def disabled() -> "MaxCutHybridInitPolicy":
        return MaxCutHybridInitPolicy(enabled=False, init_strategies=("fixed",), init_seeds=(0,))


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

    def build(
        self,
        method,
        *,
        perturbation: PerturbationConfig | None = None,
        hybrid_init_policy: MaxCutHybridInitPolicy | None = None,
    ) -> Tuple[QuantumCircuit, Callable[[Counts], float]]:
        if method.kind == "qaoa":
            p = method.params.get("p", method.p)
            if p is None:
                raise TaskSpecError("MaxCutTask requires method.params.p for kind='qaoa'.")
            init_strategy, init_seed = self._resolve_qaoa_initialization(
                perturbation=perturbation,
                hybrid_init_policy=hybrid_init_policy,
            )
            circuit = self._build_qaoa_circuit(
                p=int(p),
                init_strategy=init_strategy,
                init_seed=int(init_seed),
            )
            metric_fn = self._expectation_metric
            return circuit, metric_fn

        if method.kind in {"random", "random_baseline"}:
            circuit = self._build_random_baseline()
            metric_fn = self._expectation_metric
            return circuit, metric_fn

        raise ValueError(f"Unknown method kind: {method.kind}")

    def _resolve_qaoa_initialization(
        self,
        *,
        perturbation: PerturbationConfig | None,
        hybrid_init_policy: MaxCutHybridInitPolicy | None,
    ) -> tuple[str, int]:
        policy = hybrid_init_policy or MaxCutHybridInitPolicy.disabled()
        if not policy.enabled:
            return "fixed", 0

        if perturbation is not None and perturbation.hybrid_opt is not None:
            strategy = str(perturbation.hybrid_opt.init_strategy).strip().lower()
            seed = int(perturbation.hybrid_opt.init_seed)
        else:
            strategy = str(policy.init_strategies[0]).strip().lower()
            seed = int(policy.init_seeds[0])

        if strategy not in {"fixed", "random"}:
            raise TaskSpecError(
                f"Unsupported MaxCut hybrid init strategy '{strategy}'. Use one of: fixed, random."
            )
        return strategy, seed

    def _build_qaoa_circuit(self, p: int, *, init_strategy: str, init_seed: int) -> QuantumCircuit:
        qc = QuantumCircuit(self.num_qubits)

        # initial state |+>^n
        qc.h(range(self.num_qubits))

        # one gamma/beta per layer
        gammas = ParameterVector("gamma", length=p)
        betas = ParameterVector("beta", length=p)

        for layer in range(p):
            gamma = gammas[layer]
            beta = betas[layer]

            # Cost unitary for MaxCut: each RZZ(2*gamma) realizes exp(-i * gamma * Z_i Z_j).
            # The omitted identity term from (I - Z_i Z_j) / 2 contributes only a global
            # phase, so it does not affect optimization or rank ordering of bitstrings.
            for (i, j) in self.edges:
                qc.rzz(2 * gamma, i, j)

            # Standard transverse-field mixer.
            qc.rx(2 * beta, range(self.num_qubits))

        # Fixed-default or seeded-random initialization (no optimizer loop in this benchmark).
        bind = {}
        if init_strategy == "fixed":
            for layer in range(p):
                bind[gammas[layer]] = 0.8
                bind[betas[layer]] = 0.4
        else:
            rng = random.Random(int(init_seed))
            for layer in range(p):
                bind[gammas[layer]] = rng.uniform(0.0, math.pi)
                bind[betas[layer]] = rng.uniform(0.0, math.pi / 2.0)

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


class MaxCutTaskPlugin:
    """Built-in maxcut task plugin."""

    name = "maxcut"

    def __init__(self, **_params) -> None:
        self.params = dict(_params)
        self.hybrid_init_policy = self._parse_hybrid_init_policy(self.params)

    @staticmethod
    def _parse_hybrid_init_policy(params: dict[str, object]) -> MaxCutHybridInitPolicy:
        raw = params.get("hybrid_optimization")
        if not isinstance(raw, dict):
            return MaxCutHybridInitPolicy.disabled()

        enabled = bool(raw.get("enabled", False))
        if not enabled:
            return MaxCutHybridInitPolicy.disabled()

        raw_strategies = raw.get("init_strategies", ["fixed", "random"])
        if isinstance(raw_strategies, (str, bytes)):
            raw_strategies = [raw_strategies]
        if not isinstance(raw_strategies, list) or not raw_strategies:
            raise TaskSpecError("maxcut.task.params.hybrid_optimization.init_strategies must be a non-empty list.")
        init_strategies = tuple(str(v).strip().lower() for v in raw_strategies if str(v).strip())
        if not init_strategies:
            raise TaskSpecError("maxcut hybrid init strategies cannot be empty.")
        for strategy in init_strategies:
            if strategy not in {"fixed", "random"}:
                raise TaskSpecError(
                    f"Unsupported maxcut hybrid init strategy '{strategy}'. Use one of: fixed, random."
                )

        raw_seeds = raw.get("init_seeds", list(range(10)))
        if isinstance(raw_seeds, int):
            raw_seeds = [raw_seeds]
        if not isinstance(raw_seeds, list) or not raw_seeds:
            raise TaskSpecError("maxcut.task.params.hybrid_optimization.init_seeds must be a non-empty list.")
        try:
            init_seeds = tuple(int(v) for v in raw_seeds)
        except Exception as exc:
            raise TaskSpecError("maxcut hybrid init seeds must be integers.") from exc

        return MaxCutHybridInitPolicy(
            enabled=True,
            init_strategies=init_strategies,
            init_seeds=init_seeds,
        )

    def hybrid_space_axes(self) -> tuple[list[str] | None, list[int] | None]:
        if not self.hybrid_init_policy.enabled:
            return None, None
        return list(self.hybrid_init_policy.init_strategies), list(self.hybrid_init_policy.init_seeds)

    def instances(self, suite: str) -> list[ProblemInstance]:
        return load_suite(suite)

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        circuit, metric_fn = MaxCutTask(instance).build(method, hybrid_init_policy=self.hybrid_init_policy)
        return BuiltWorkflow(circuit=circuit, metric_fn=metric_fn)

    def build_with_config(
        self,
        instance: ProblemInstance,
        method: MethodSpec,
        perturbation: PerturbationConfig,
    ) -> BuiltWorkflow:
        circuit, metric_fn = MaxCutTask(instance).build(
            method,
            perturbation=perturbation,
            hybrid_init_policy=self.hybrid_init_policy,
        )
        return BuiltWorkflow(circuit=circuit, metric_fn=metric_fn)


from claimstab.tasks.registry import register_task

register_task("maxcut", MaxCutTaskPlugin)
