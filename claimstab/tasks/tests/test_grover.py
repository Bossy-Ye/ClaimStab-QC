from __future__ import annotations

import unittest

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.grover import GroverTaskPlugin


class TestGroverTask(unittest.TestCase):
    def test_instances_and_build(self) -> None:
        plugin = GroverTaskPlugin(min_qubits=4, max_qubits=5, instances_per_qubit=2)
        instances = plugin.instances("core")
        self.assertGreaterEqual(len(instances), 4)
        built = plugin.build(instances[0], MethodSpec(name="GroverOracle", kind="grover"))
        self.assertGreater(built.circuit.num_qubits, 0)
        self.assertGreaterEqual(len(built.circuit.clbits), 1)

    def test_uniform_baseline_supported(self) -> None:
        plugin = GroverTaskPlugin(min_qubits=4, max_qubits=4, instances_per_qubit=1)
        inst = plugin.instances("core")[0]
        built = plugin.build(inst, MethodSpec(name="UniformBaseline", kind="uniform"))
        self.assertEqual(built.circuit.num_qubits, 4)
        self.assertEqual(len(built.circuit.clbits), 4)


if __name__ == "__main__":
    unittest.main()
