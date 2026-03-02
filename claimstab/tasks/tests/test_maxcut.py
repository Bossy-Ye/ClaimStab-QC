import unittest

from claimstab.tasks.maxcut import MaxCutTask
from claimstab.tasks.graphs import GraphInstance, large_suite
from claimstab.tasks.instances import ProblemInstance
from claimstab.methods.spec import MethodSpec


class TestMaxCutQAOA(unittest.TestCase):

    def setUp(self):
        # Simple graph (5 nodes, 7 edges)
        graph = GraphInstance(
            graph_id="maxcut_test",
            num_nodes=5,
            edges=[(0, 1), (1, 2), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4)],
        )
        self.instance = ProblemInstance(
            instance_id="maxcut_test",
            payload=graph,
        )

        self.task = MaxCutTask(self.instance)
        self.method = MethodSpec(name="QAOA_p1", kind="qaoa", p=1)

    def test_qaoa_binds_all_parameters(self):
        circuit, _ = self.task.build(self.method)

        # After assign_parameters, there should be NO free parameters
        self.assertEqual(
            len(circuit.parameters),
            0,
            "QAOA circuit has unbound parameters",
        )

    def test_qaoa_has_measurements(self):
        circuit, _ = self.task.build(self.method)

        self.assertTrue(
            circuit.num_clbits > 0,
            "QAOA circuit has no classical bits (missing measurements)",
        )

    def test_qaoa_qubit_count(self):
        circuit, _ = self.task.build(self.method)
        print(circuit)
        self.assertEqual(
            circuit.num_qubits,
            5,
            "QAOA circuit qubit count does not match graph size",
        )


class TestGraphSuites(unittest.TestCase):
    def test_large_suite_has_expected_size_and_unique_ids(self):
        suite = large_suite()
        self.assertEqual(len(suite), 30)
        ids = [inst.instance_id for inst in suite]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
