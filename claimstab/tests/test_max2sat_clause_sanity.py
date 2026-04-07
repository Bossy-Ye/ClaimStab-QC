from __future__ import annotations

import cmath
import itertools
import unittest

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from examples.community.max2sat_pilot_demo.max2sat_task import (
    Clause,
    Max2SATQAOAPilotTask,
    _core_instances,
)


def _literal_value(bit: int, negated: bool) -> int:
    return 1 - bit if negated else bit


def _clause_unsatisfied(bits: tuple[int, int], clause: Clause) -> bool:
    left_val = _literal_value(bits[clause.left], clause.left_negated)
    right_val = _literal_value(bits[clause.right], clause.right_negated)
    return not (left_val or right_val)


class TestMax2SATClauseSanity(unittest.TestCase):
    def test_clause_phase_gadget_matches_unsatisfied_projector(self) -> None:
        task = Max2SATQAOAPilotTask()
        gamma = 0.37

        for left_negated, right_negated in itertools.product((False, True), repeat=2):
            clause = Clause(0, left_negated, 1, right_negated)
            qc = QuantumCircuit(2)
            task._apply_clause_phase(qc, clause, gamma)
            unitary = Operator(qc).data

            for row in range(4):
                for col in range(4):
                    if row != col:
                        self.assertAlmostEqual(abs(unitary[row, col]), 0.0, places=12)

            for x0, x1 in itertools.product((0, 1), repeat=2):
                index = x0 + 2 * x1
                observed = unitary[index, index]
                expected = cmath.exp(1j * gamma) if _clause_unsatisfied((x0, x1), clause) else 1.0 + 0.0j
                self.assertAlmostEqual(observed.real, expected.real, places=12)
                self.assertAlmostEqual(observed.imag, expected.imag, places=12)

    def test_exhaustive_assignments_align_max_sat_with_min_unsatisfied(self) -> None:
        for payload in _core_instances():
            assignments = list(itertools.product((0, 1), repeat=payload.num_vars))
            satisfied_counts: dict[tuple[int, ...], int] = {}
            unsatisfied_counts: dict[tuple[int, ...], int] = {}

            for bits in assignments:
                satisfied = 0
                for clause in payload.clauses:
                    left_val = _literal_value(bits[clause.left], clause.left_negated)
                    right_val = _literal_value(bits[clause.right], clause.right_negated)
                    if left_val or right_val:
                        satisfied += 1
                satisfied_counts[bits] = satisfied
                unsatisfied_counts[bits] = len(payload.clauses) - satisfied

            max_sat = max(satisfied_counts.values())
            min_unsat = min(unsatisfied_counts.values())
            self.assertEqual(max_sat + min_unsat, len(payload.clauses))

            argmax_sat = {bits for bits, value in satisfied_counts.items() if value == max_sat}
            argmin_unsat = {bits for bits, value in unsatisfied_counts.items() if value == min_unsat}
            self.assertEqual(argmax_sat, argmin_unsat)


if __name__ == "__main__":
    unittest.main()
