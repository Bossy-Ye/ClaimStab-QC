from __future__ import annotations

import unittest
from unittest.mock import patch

from qiskit import QuantumCircuit

from claimstab.runners.qiskit_aer import AerRunConfig
from claimstab.runners.qiskit_ibm_runtime import QiskitIBMRuntimeRunner


class _FakeCounts:
    def get_counts(self):
        return {"0": 3, "1": 1}


class _FakePubResult:
    def join_data(self):
        return _FakeCounts()


class _FakeJob:
    def result(self):
        return [_FakePubResult()]


class _FakeSampler:
    def __init__(self, mode=None, options=None):
        self.mode = mode
        self.options = options

    def run(self, pubs, shots=None):
        self.last_pubs = pubs
        self.last_shots = shots
        return _FakeJob()


class _FakeBackend:
    num_qubits = 5
    target = type("Target", (), {"dt": None})()

    def name(self):
        return "ibm_test_backend"

    def status(self):
        return "active"


class _FakeService:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def backend(self, name, instance=None):
        self.last_backend = (name, instance)
        return _FakeBackend()

    def backends(self, instance=None, min_num_qubits=None):
        return [_FakeBackend()]


class TestQiskitIBMRuntimeRunner(unittest.TestCase):
    def test_requires_backend_name(self) -> None:
        with self.assertRaises(ValueError):
            QiskitIBMRuntimeRunner(backend_name=None, token="tok")

    def test_run_metric_uses_sampler_counts(self) -> None:
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)

        with (
            patch("claimstab.runners.qiskit_ibm_runtime._load_runtime_types", return_value=(_FakeService, _FakeSampler)),
            patch("claimstab.runners.qiskit_ibm_runtime.snapshot_from_backend", return_value={"backend_name": "ibm_test_backend"}),
            patch("claimstab.runners.qiskit_ibm_runtime.fingerprint", return_value="fp"),
            patch("claimstab.runners.qiskit_ibm_runtime.transpile", side_effect=lambda circuit, **_: circuit),
        ):
            runner = QiskitIBMRuntimeRunner(backend_name="ibm_test_backend", token="tok")
            score, details = runner.run_metric(
                qc,
                AerRunConfig(shots=4, optimization_level=1, seed_transpiler=7, layout_method="sabre"),
                lambda counts: counts.get("1", 0) / max(1, sum(counts.values())),
                return_details=True,
            )

        self.assertAlmostEqual(score, 0.25, places=8)
        self.assertEqual(details.device_provider, "ibm_runtime")
        self.assertEqual(details.device_name, "ibm_test_backend")
        self.assertEqual(details.device_snapshot_fingerprint, "fp")
        self.assertEqual(details.counts, {"0": 3, "1": 1})


if __name__ == "__main__":
    unittest.main()
