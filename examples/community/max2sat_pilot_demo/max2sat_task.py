from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
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

    def __init__(self, num_instances: int = 6) -> None:
        self.num_instances = int(num_instances)
        if self.num_instances <= 0:
            raise TaskSpecError("num_instances must be >= 1")

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
        qc.cp(gamma, clause.left, clause.right)
        for qubit in reversed(flipped):
            qc.x(qubit)

    def _build_qaoa(self, payload: Max2SATPayload, gammas: tuple[float, ...], betas: tuple[float, ...]) -> QuantumCircuit:
        qc = QuantumCircuit(payload.num_vars)
        qc.h(range(payload.num_vars))
        for gamma, beta in zip(gammas, betas):
            for clause in payload.clauses:
                self._apply_clause_phase(qc, clause, gamma)
            qc.rx(2.0 * beta, range(payload.num_vars))
        qc.measure_all()
        return qc

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        if not isinstance(payload, Max2SATPayload):
            raise TaskSpecError("Max2SATQAOAPilotTask got unsupported payload.")

        if method.kind == "qaoa":
            p = int(method.params.get("p", method.p or 1))
            if p == 1:
                qc = self._build_qaoa(payload, gammas=(0.82,), betas=(0.42,))
            elif p == 2:
                qc = self._build_qaoa(payload, gammas=(0.76, 0.58), betas=(0.40, 0.28))
            else:
                raise TaskSpecError("Max2SATQAOAPilotTask supports only p in {1, 2}.")
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

    def build_with_config(self, instance: ProblemInstance, method: MethodSpec, _config) -> BuiltWorkflow:
        return self.build(instance, method)
