from __future__ import annotations

import unittest

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.bernstein_vazirani import BernsteinVaziraniTaskPlugin


class TestBernsteinVaziraniTask(unittest.TestCase):
    def test_instances_and_build(self) -> None:
        plugin = BernsteinVaziraniTaskPlugin()
        instances = plugin.instances("core")
        self.assertGreaterEqual(len(instances), 20)
        lengths = sorted({len(inst.payload.hidden_string) for inst in instances})
        self.assertEqual(lengths[0], 4)
        self.assertEqual(lengths[-1], 10)
        built = plugin.build(instances[0], MethodSpec(name="BVOracle", kind="bv"))
        self.assertGreater(built.circuit.num_qubits, 0)
        self.assertGreaterEqual(len(built.circuit.clbits), 1)

    def test_large_suite_has_30_instances(self) -> None:
        plugin = BernsteinVaziraniTaskPlugin()
        instances = plugin.instances("large")
        self.assertEqual(len(instances), 30)

    def test_small_qubit_range_is_capped_by_unique_capacity(self) -> None:
        plugin = BernsteinVaziraniTaskPlugin(min_qubits=1, max_qubits=1, instances_per_qubit=10)
        instances = plugin.instances("core")
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].payload.hidden_string, "1")


if __name__ == "__main__":
    unittest.main()
