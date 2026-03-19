import unittest

from qiskit import qasm2

from claimstab.tasks.maxcut import MaxCutTask, MaxCutTaskPlugin
from claimstab.tasks.graphs import GraphInstance, large_suite
from claimstab.tasks.instances import ProblemInstance
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.space import (
    CompilationPerturbation,
    ExecutionPerturbation,
    HybridOptimizationPerturbation,
    PerturbationConfig,
)


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


class TestMaxCutHybridInitialization(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = GraphInstance(
            graph_id="maxcut_hybrid_test",
            num_nodes=4,
            edges=[(0, 1), (1, 2), (2, 3), (0, 3)],
        )
        self.instance = ProblemInstance(instance_id="maxcut_hybrid_test", payload=self.graph)
        self.method = MethodSpec(name="QAOA_p2", kind="qaoa", params={"p": 2})

    @staticmethod
    def _cfg(seed: int) -> PerturbationConfig:
        return PerturbationConfig(
            compilation=CompilationPerturbation(seed_transpiler=0, optimization_level=1, layout_method="sabre"),
            execution=ExecutionPerturbation(shots=256, seed_simulator=0),
            hybrid_opt=HybridOptimizationPerturbation(init_strategy="random", init_seed=seed),
        )

    def test_random_init_is_seed_deterministic(self) -> None:
        plugin = MaxCutTaskPlugin(
            hybrid_optimization={
                "enabled": True,
                "init_strategies": ["random"],
                "init_seeds": [0, 1, 2],
            }
        )
        c1 = plugin.build_with_config(self.instance, self.method, self._cfg(3)).circuit
        c2 = plugin.build_with_config(self.instance, self.method, self._cfg(3)).circuit
        c3 = plugin.build_with_config(self.instance, self.method, self._cfg(4)).circuit

        self.assertEqual(c1.count_ops(), c2.count_ops())
        self.assertEqual(qasm2.dumps(c1), qasm2.dumps(c2))
        self.assertNotEqual(qasm2.dumps(c1), qasm2.dumps(c3))

    def test_hybrid_axes_exposed_only_when_enabled(self) -> None:
        disabled = MaxCutTaskPlugin()
        self.assertEqual(disabled.hybrid_space_axes(), (None, None))

        enabled = MaxCutTaskPlugin(
            hybrid_optimization={
                "enabled": True,
                "init_strategies": ["fixed", "random"],
                "init_seeds": [0, 1],
            }
        )
        strategies, seeds = enabled.hybrid_space_axes()
        self.assertEqual(strategies, ["fixed", "random"])
        self.assertEqual(seeds, [0, 1])


if __name__ == "__main__":
    unittest.main()
