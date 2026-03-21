from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claimstab.tasks.factory import make_task, parse_methods


class TestTaskFactory(unittest.TestCase):
    def test_parse_methods_default(self) -> None:
        methods = parse_methods({})
        self.assertEqual([m.name for m in methods], ["QAOA_p1", "QAOA_p2", "RandomBaseline"])

    def test_parse_methods_default_bv(self) -> None:
        methods = parse_methods({}, task_kind="bv")
        self.assertEqual([m.name for m in methods], ["BVOracle", "RandomBaseline"])

    def test_parse_methods_default_grover(self) -> None:
        methods = parse_methods({}, task_kind="grover")
        self.assertEqual([m.name for m in methods], ["GroverOracle", "UniformBaseline"])

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
                "entrypoint": "examples.community.custom_task_demo.toy_task:ToyTask",
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

    def test_make_task_external_qec_pilot_module_class(self) -> None:
        task, suite = make_task(
            {
                "kind": "external",
                "entrypoint": "examples.community.qec_pilot_demo.qec_decoder_task:RepetitionCodeDecoderTask",
                "suite": "core",
                "params": {"distance": 5, "physical_error_rate": 0.15, "num_instances": 4},
            },
            default_suite="core",
        )
        self.assertEqual(suite, "core")
        instances = task.instances("core")
        self.assertEqual(len(instances), 4)
        methods = parse_methods(
            {
                "methods": [
                    {"name": "GlobalMajority", "kind": "global_majority"},
                ]
            }
        )
        built = task.build(instances[0], methods[0])
        circuit = getattr(built, "circuit", None)
        self.assertIsNotNone(circuit)
        self.assertEqual(circuit.num_qubits, 5)

    def test_make_task_external_file_path_class(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            module_path = Path(td) / "external_task.py"
            module_path.write_text(
                """
from claimstab.tasks.instances import ProblemInstance

class FilePathTask:
    name = "filepath_task"

    def __init__(self, num_instances=2):
        self.num_instances = int(num_instances)

    def instances(self, suite):
        return [ProblemInstance(instance_id=f"{suite}_{i}", payload={"i": i}) for i in range(self.num_instances)]

    def build(self, instance, method):
        return object()
""".strip()
                + "\n",
                encoding="utf-8",
            )
            task, suite = make_task(
                {
                    "kind": "external",
                    "entrypoint": f"{module_path}:FilePathTask",
                    "suite": "core",
                    "params": {"num_instances": 3},
                },
                default_suite="core",
            )
            self.assertEqual(suite, "core")
            self.assertEqual(len(task.instances("core")), 3)


if __name__ == "__main__":
    unittest.main()
