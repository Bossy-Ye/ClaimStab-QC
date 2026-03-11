from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claimstab.spec import apply_spec_defaults, load_spec, validate_spec


class TestSpecValidation(unittest.TestCase):
    def test_defaults_apply_backward_compatibility(self) -> None:
        spec = {"suite": "core"}
        normalized = apply_spec_defaults(spec)
        self.assertEqual(normalized["spec_version"], 1)
        self.assertEqual(normalized["backend"]["noise_model"], "none")
        self.assertFalse(normalized["device_profile"]["enabled"])

    def test_validate_accepts_minimal_v1(self) -> None:
        spec = {
            "spec_version": 1,
            "suite": "core",
            "sampling": {"mode": "full_factorial", "seed": 0},
            "decision_rule": {"threshold": 0.95, "confidence_level": 0.95},
        }
        validate_spec(spec)

    def test_validate_rejects_invalid_sampling_mode(self) -> None:
        spec = {
            "spec_version": 1,
            "suite": "core",
            "sampling": {"mode": "bad_mode"},
        }
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_load_spec_from_yaml(self) -> None:
        text = """
        suite: core
        sampling:
          mode: random_k
          sample_size: 5
          seed: 3
        """
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.yml"
            path.write_text(text, encoding="utf-8")
            spec = load_spec(path, validate=False)
            self.assertEqual(spec["spec_version"], 1)
            self.assertEqual(spec["sampling"]["mode"], "random_k")
            self.assertEqual(spec["sampling"]["sample_size"], 5)

    def test_validate_allows_external_task_and_custom_suite(self) -> None:
        spec = {
            "spec_version": 1,
            "suite": "toy",
            "task": {
                "kind": "external",
                "entrypoint": "examples.community.custom_task_demo.toy_task:ToyTask",
                "suite": "toy",
                "params": {"num_qubits": 4},
            },
            "methods": [
                {"name": "HadamardAll", "kind": "hadamard"},
                {"name": "ZeroState", "kind": "zero"},
            ],
            "sampling": {"mode": "random_k", "sample_size": 8, "seed": 1},
            "decision_rule": {"threshold": 0.95, "confidence_level": 0.95},
        }
        validate_spec(spec)

    def test_defaults_map_legacy_repeats_to_seed_simulator(self) -> None:
        spec = {
            "suite": "core",
            "perturbation_space": {"shots": [256, 1024], "repeats": [0, 1, 2]},
            "baseline": {"shots": 1024, "repeats": 0},
        }
        normalized = apply_spec_defaults(spec)
        self.assertEqual(normalized["perturbation_space"]["seed_simulator"], [0, 1, 2])
        self.assertNotIn("repeats", normalized["perturbation_space"])
        self.assertNotIn("repeats", normalized["baseline"])
        self.assertIn("repeats", normalized["meta"]["deprecated_field_used"])

    def test_validate_distribution_claim_fields(self) -> None:
        spec = {
            "spec_version": 1,
            "suite": "core",
            "task": {"kind": "grover", "suite": "core"},
            "methods": [
                {"name": "GroverOracle", "kind": "grover"},
                {"name": "UniformBaseline", "kind": "uniform"},
            ],
            "claims": [
                {
                    "type": "distribution",
                    "method": "GroverOracle",
                    "epsilon": 0.05,
                    "primary_distance": "js",
                    "sanity_distance": "tvd",
                    "reference_shots": "max",
                    "metric_name": "objective",
                }
            ],
            "sampling": {"mode": "random_k", "sample_size": 8, "seed": 1},
            "decision_rule": {"threshold": 0.95, "confidence_level": 0.95},
        }
        validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
