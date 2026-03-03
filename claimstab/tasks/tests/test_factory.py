from __future__ import annotations

import unittest

from claimstab.tasks.factory import make_task, parse_methods


class TestTaskFactory(unittest.TestCase):
    def test_parse_methods_default(self) -> None:
        methods = parse_methods({})
        self.assertEqual([m.name for m in methods], ["QAOA_p1", "QAOA_p2", "RandomBaseline"])

    def test_parse_methods_default_bv(self) -> None:
        methods = parse_methods({}, task_kind="bv")
        self.assertEqual([m.name for m in methods], ["BVOracle", "RandomBaseline"])

    def test_make_task_builtin_maxcut(self) -> None:
        task, suite = make_task(None, default_suite="core")
        self.assertEqual(getattr(task, "name", None), "maxcut")
        self.assertEqual(suite, "core")
        instances = task.instances("core")
        self.assertGreaterEqual(len(instances), 1)

    def test_make_task_external_module_class(self) -> None:
        task, suite = make_task(
            {
                "kind": "external",
                "entrypoint": "examples.custom_task_demo.toy_task:ToyTask",
                "suite": "toy",
                "params": {"num_qubits": 4, "num_instances": 2},
            },
            default_suite="core",
        )
        self.assertEqual(suite, "toy")
        instances = task.instances("toy")
        self.assertEqual(len(instances), 2)
        methods = parse_methods(
            {
                "methods": [
                    {"name": "HadamardAll", "kind": "hadamard"},
                ]
            }
        )
        built = task.build(instances[0], methods[0])
        # BuiltWorkflow-like shape
        circuit = getattr(built, "circuit", None)
        self.assertIsNotNone(circuit)
        self.assertEqual(circuit.num_qubits, 4)


if __name__ == "__main__":
    unittest.main()
