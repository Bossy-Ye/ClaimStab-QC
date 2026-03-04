from __future__ import annotations

import unittest

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.factory import make_task, parse_methods
from claimstab.tasks.ghz_structural import GHZStructuralTaskPlugin


class TestGHZStructuralTask(unittest.TestCase):
    def test_instances_cover_qubit_range(self) -> None:
        task = GHZStructuralTaskPlugin(min_qubits=6, max_qubits=10, step=2)
        suite = task.instances("large")
        sizes = [int(inst.meta["num_qubits"]) for inst in suite if inst.meta]
        self.assertEqual(sizes, [6, 8, 10])

    def test_supported_methods_build(self) -> None:
        task = GHZStructuralTaskPlugin(min_qubits=6, max_qubits=6, step=2)
        inst = task.instances("core")[0]
        for kind in ("ghz_linear", "ghz_star", "random_baseline"):
            built = task.build(inst, MethodSpec(name=kind, kind=kind))
            self.assertGreater(getattr(built.circuit, "num_qubits", 0), 0)
            # Metric must always produce a bounded scalar.
            score = built.metric_fn({"0" * built.circuit.num_qubits: 512, "1" * built.circuit.num_qubits: 512})
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_factory_builtin_ghz(self) -> None:
        spec = {
            "task": {"kind": "ghz", "suite": "core", "params": {"min_qubits": 6, "max_qubits": 8, "step": 2}},
            "methods": [
                {"name": "GHZ_Linear", "kind": "ghz_linear"},
                {"name": "GHZ_Star", "kind": "ghz_star"},
            ],
        }
        task, suite = make_task(spec["task"], default_suite="core")
        methods = parse_methods(spec, task_kind="ghz")
        self.assertEqual(getattr(task, "name", ""), "ghz")
        self.assertEqual(suite, "core")
        self.assertEqual([m.name for m in methods], ["GHZ_Linear", "GHZ_Star"])


if __name__ == "__main__":
    unittest.main()

