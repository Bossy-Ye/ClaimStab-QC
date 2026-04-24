from __future__ import annotations

import math
import random
from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.space import PerturbationConfig
from claimstab.tasks.base import BuiltWorkflow, TaskSpecError
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class Clause:
    left: int
    left_negated: bool
    right: int
    right_negated: bool


@dataclass(frozen=True)
class Max2SATPayload:
    num_vars: int
    clauses: tuple[Clause, ...]


@dataclass(frozen=True)
class Max2SATHybridInitPolicy:
    enabled: bool = False
    init_strategies: tuple[str, ...] = ("fixed",)
    init_seeds: tuple[int, ...] = (0,)

    @staticmethod
    def disabled() -> "Max2SATHybridInitPolicy":
        return Max2SATHybridInitPolicy(enabled=False, init_strategies=("fixed",), init_seeds=(0,))


def _core_instances() -> list[Max2SATPayload]:
    formulas = [
        (
            4,
            (
                Clause(0, False, 1, False),
                Clause(0, True, 2, False),
                Clause(1, False, 2, True),
                Clause(2, False, 3, False),
                Clause(1, True, 3, True),
            ),
        ),
        (
            4,
            (
                Clause(0, False, 1, True),
                Clause(1, False, 2, False),
                Clause(0, True, 3, False),
                Clause(2, True, 3, False),
                Clause(0, False, 2, False),
            ),
        ),
        (
            4,
            (
                Clause(0, True, 1, True),
                Clause(1, False, 2, False),
                Clause(2, False, 3, True),
                Clause(0, False, 3, False),
                Clause(1, False, 3, False),
                Clause(0, True, 2, True),
            ),
        ),
        (
            4,
            (
                Clause(0, False, 1, False),
                Clause(0, False, 2, True),
                Clause(1, True, 3, False),
                Clause(2, False, 3, False),
                Clause(0, True, 3, True),
                Clause(1, False, 2, False),
            ),
        ),
        (
            4,
            (
                Clause(0, True, 1, False),
                Clause(1, False, 2, True),
                Clause(2, False, 3, False),
                Clause(0, False, 3, False),
                Clause(0, False, 2, False),
                Clause(1, True, 3, True),
            ),
        ),
        (
            4,
            (
                Clause(0, False, 1, True),
                Clause(0, True, 2, False),
                Clause(1, False, 3, False),
                Clause(2, True, 3, False),
                Clause(0, False, 3, True),
                Clause(1, False, 2, False),
            ),
        ),
    ]
    return [Max2SATPayload(num_vars=n, clauses=clauses) for n, clauses in formulas]


def _literal_value(bit: int, negated: bool) -> int:
    return 1 - bit if negated else bit


class Max2SATQAOAPilotTask:
    """External Max-2-SAT second-family pilot with QAOA-style heuristics."""

    name = "max2sat_qaoa_pilot"

    def __init__(self, num_instances: int = 6, hybrid_optimization: dict[str, object] | None = None) -> None:
        self.num_instances = int(num_instances)
        if self.num_instances <= 0:
            raise TaskSpecError("num_instances must be >= 1")
        self.hybrid_init_policy = self._parse_hybrid_init_policy(hybrid_optimization)

    @staticmethod
    def _parse_hybrid_init_policy(raw: dict[str, object] | None) -> Max2SATHybridInitPolicy:
        if not isinstance(raw, dict):
            return Max2SATHybridInitPolicy.disabled()

        enabled = bool(raw.get("enabled", False))
        if not enabled:
            return Max2SATHybridInitPolicy.disabled()

        raw_strategies = raw.get("init_strategies", ["fixed", "random"])
        if isinstance(raw_strategies, (str, bytes)):
            raw_strategies = [raw_strategies]
        if not isinstance(raw_strategies, list) or not raw_strategies:
            raise TaskSpecError("max2sat.task.params.hybrid_optimization.init_strategies must be a non-empty list.")
        init_strategies = tuple(str(v).strip().lower() for v in raw_strategies if str(v).strip())
        if not init_strategies:
            raise TaskSpecError("max2sat hybrid init strategies cannot be empty.")
        for strategy in init_strategies:
            if strategy not in {"fixed", "random"}:
                raise TaskSpecError(
                    f"Unsupported max2sat hybrid init strategy '{strategy}'. Use one of: fixed, random."
                )

        raw_seeds = raw.get("init_seeds", list(range(10)))
        if isinstance(raw_seeds, int):
            raw_seeds = [raw_seeds]
        if not isinstance(raw_seeds, list) or not raw_seeds:
            raise TaskSpecError("max2sat.task.params.hybrid_optimization.init_seeds must be a non-empty list.")
        try:
            init_seeds = tuple(int(v) for v in raw_seeds)
        except Exception as exc:
            raise TaskSpecError("max2sat hybrid init seeds must be integers.") from exc

        return Max2SATHybridInitPolicy(
            enabled=True,
            init_strategies=init_strategies,
            init_seeds=init_seeds,
        )

    def hybrid_space_axes(self) -> tuple[list[str] | None, list[int] | None]:
        if not self.hybrid_init_policy.enabled:
            return None, None
        return list(self.hybrid_init_policy.init_strategies), list(self.hybrid_init_policy.init_seeds)

    def instances(self, suite: str) -> list[ProblemInstance]:
        library = _core_instances()
        count = min(len(library), self.num_instances)
        out: list[ProblemInstance] = []
        for idx, payload in enumerate(library[:count]):
            out.append(
                ProblemInstance(
                    instance_id=f"max2sat_{suite}_{idx}",
                    payload=payload,
                    meta={
                        "instance_type": "max2sat_qaoa_pilot",
                        "num_vars": payload.num_vars,
                        "num_clauses": len(payload.clauses),
                    },
                )
            )
        return out

    def _apply_clause_phase(self, qc: QuantumCircuit, clause: Clause, gamma: float) -> None:
        flipped: list[int] = []
        for qubit, negated in ((clause.left, clause.left_negated), (clause.right, clause.right_negated)):
            if not negated:
                qc.x(qubit)
                flipped.append(qubit)
        # After literal-aligned X gates, the unique unsatisfied assignment for the
        # clause is mapped to |11>. CP(gamma) therefore applies an exact diagonal
        # phase gadget for the clause-unsatisfied projector, up to the sign
        # convention absorbed into gamma.
        qc.cp(gamma, clause.left, clause.right)
        for qubit in reversed(flipped):
            qc.x(qubit)

    def _resolve_qaoa_initialization(
        self,
        *,
        perturbation: PerturbationConfig | None,
    ) -> tuple[str, int]:
        if not self.hybrid_init_policy.enabled:
            return "fixed", 0

        if perturbation is not None and perturbation.hybrid_opt is not None:
            strategy = str(perturbation.hybrid_opt.init_strategy).strip().lower()
            seed = int(perturbation.hybrid_opt.init_seed)
        else:
            strategy = str(self.hybrid_init_policy.init_strategies[0]).strip().lower()
            seed = int(self.hybrid_init_policy.init_seeds[0])

        if strategy not in {"fixed", "random"}:
            raise TaskSpecError(
                f"Unsupported max2sat hybrid init strategy '{strategy}'. Use one of: fixed, random."
            )
        return strategy, seed

    @staticmethod
    def _resolved_angles(p: int, *, init_strategy: str, init_seed: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
        if init_strategy == "fixed":
            if p == 1:
                return (0.82,), (0.42,)
            if p == 2:
                return (0.76, 0.58), (0.40, 0.28)
            raise TaskSpecError("Max2SATQAOAPilotTask supports only p in {1, 2}.")

        rng = random.Random(int(init_seed))
        gammas = tuple(rng.uniform(0.0, math.pi) for _ in range(p))
        betas = tuple(rng.uniform(0.0, math.pi / 2.0) for _ in range(p))
        return gammas, betas

    def _build_qaoa(self, payload: Max2SATPayload, gammas: tuple[float, ...], betas: tuple[float, ...]) -> QuantumCircuit:
        qc = QuantumCircuit(payload.num_vars)
        qc.h(range(payload.num_vars))
        for gamma, beta in zip(gammas, betas):
            for clause in payload.clauses:
                self._apply_clause_phase(qc, clause, gamma)
            qc.rx(2.0 * beta, range(payload.num_vars))
        qc.measure_all()
        return qc

    def build(
        self,
        instance: ProblemInstance,
        method: MethodSpec,
        *,
        perturbation: PerturbationConfig | None = None,
    ) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, Max2SATPayload):
            raise TaskSpecError("Max2SATQAOAPilotTask got unsupported payload.")

        if method.kind == "qaoa":
            p = int(method.params.get("p", method.p or 1))
            init_strategy, init_seed = self._resolve_qaoa_initialization(perturbation=perturbation)
            gammas, betas = self._resolved_angles(p, init_strategy=init_strategy, init_seed=init_seed)
            qc = self._build_qaoa(payload, gammas=gammas, betas=betas)
        elif method.kind in {"random_baseline", "random"}:
            qc = QuantumCircuit(payload.num_vars)
            qc.h(range(payload.num_vars))
            qc.measure_all()
        else:
            raise TaskSpecError(f"Unsupported Max-2-SAT method kind: {method.kind}")

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total <= 0:
                return 0.0

            expectation = 0.0
            for bitstring, shot_count in counts.items():
                bits = [int(bit) for bit in bitstring[::-1]]
                satisfied = 0
                for clause in payload.clauses:
                    left_val = _literal_value(bits[clause.left], clause.left_negated)
                    right_val = _literal_value(bits[clause.right], clause.right_negated)
                    if left_val or right_val:
                        satisfied += 1
                expectation += (shot_count / total) * satisfied
            return expectation

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)

    def build_with_config(self, instance: ProblemInstance, method: MethodSpec, config: PerturbationConfig) -> BuiltWorkflow:
        return self.build(instance, method, perturbation=config)
