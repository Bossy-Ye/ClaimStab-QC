from __future__ import annotations

import itertools
import math
import unittest

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.graphs import GraphInstance
from claimstab.tasks.instances import ProblemInstance
from claimstab.tasks.maxcut import MaxCutTask


def _cut_value(bits: tuple[int, ...], edges: list[tuple[int, int]]) -> int:
    return sum(1 for i, j in edges if bits[i] != bits[j])


def _ising_energy(bits: tuple[int, ...], edges: list[tuple[int, int]]) -> int:
    spins = [1 if bit == 0 else -1 for bit in bits]
    return sum(spins[i] * spins[j] for i, j in edges)


class TestMaxCutHamiltonianSanity(unittest.TestCase):
    def test_bruteforce_cut_objective_matches_ising_form(self) -> None:
        graph = GraphInstance(
            graph_id="triangle_tail",
            num_nodes=4,
            edges=[(0, 1), (1, 2), (0, 2), (2, 3)],
        )
        edges = list(graph.edges)
        num_edges = len(edges)

        assignments = list(itertools.product((0, 1), repeat=graph.num_nodes))
        cuts = {bits: _cut_value(bits, edges) for bits in assignments}
        energies = {bits: _ising_energy(bits, edges) for bits in assignments}

        for bits in assignments:
            self.assertEqual(cuts[bits], (num_edges - energies[bits]) // 2)

        max_cut = max(cuts.values())
        min_energy = min(energies.values())
        argmax_cut = {bits for bits, value in cuts.items() if value == max_cut}
        argmin_energy = {bits for bits, value in energies.items() if value == min_energy}
        self.assertEqual(argmax_cut, argmin_energy)

    def test_cost_layer_uses_one_rzz_per_edge_with_expected_angle(self) -> None:
        graph = GraphInstance(
            graph_id="path3",
            num_nodes=3,
            edges=[(0, 1), (1, 2)],
        )
        instance = ProblemInstance(instance_id="path3", payload=graph)
        task = MaxCutTask(instance)
        method = MethodSpec(name="QAOA_p1", kind="qaoa", p=1)
        circuit, _ = task.build(method)

        rzz_angles = [float(inst.operation.params[0]) for inst in circuit.data if inst.operation.name == "rzz"]
        self.assertEqual(len(rzz_angles), len(graph.edges))
        for angle in rzz_angles:
            self.assertTrue(math.isclose(angle, 1.6, rel_tol=1e-12, abs_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
