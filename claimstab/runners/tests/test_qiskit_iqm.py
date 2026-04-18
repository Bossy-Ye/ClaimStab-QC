from __future__ import annotations

import unittest
from unittest.mock import patch

from qiskit import QuantumCircuit

from claimstab.runners.qiskit_aer import AerRunConfig
from claimstab.runners.qiskit_iqm import QiskitIQMRunner


class _FakeIQMJobResult:
    def get_counts(self):
        return {"0000": 3, "1111": 1}


class _FakeIQMJob:
    def result(self):
        return _FakeIQMJobResult()


class _FakeIQMBackend:
    target = type("Target", (), {"dt": None})()

    def __init__(self, name: str, num_qubits: int = 54):
        self._name = name
        self.num_qubits = num_qubits

    def name(self):
        return self._name

    def run(self, circuit, shots=None):
        self.last_circuit = circuit
        self.last_shots = shots
        return _FakeIQMJob()


class _FakeIQMProvider:
    def __init__(self, server_url, **kwargs):
        self.server_url = server_url
        self.kwargs = kwargs

    def get_backend(self, name=None, calibration_set_id=None):
        del calibration_set_id
        return _FakeIQMBackend(name or "garnet")


class TestQiskitIQMRunner(unittest.TestCase):
    def test_requires_server_url_and_quantum_computer(self) -> None:
        with self.assertRaises(ValueError):
            QiskitIQMRunner(server_url=None, quantum_computer="vtt")
        with self.assertRaises(ValueError):
            QiskitIQMRunner(server_url="https://iqm.example", quantum_computer=None)

    def test_run_metric_uses_backend_counts(self) -> None:
        qc = QuantumCircuit(4, 4)
        qc.measure(range(4), range(4))

        with (
            patch("claimstab.runners.qiskit_iqm._load_iqm_provider_type", return_value=_FakeIQMProvider),
            patch("claimstab.runners.qiskit_iqm.snapshot_from_backend", return_value={"backend_name": "garnet"}),
            patch("claimstab.runners.qiskit_iqm.fingerprint", return_value="fp"),
            patch("claimstab.runners.qiskit_iqm.transpile", side_effect=lambda circuit, **_: circuit),
        ):
            runner = QiskitIQMRunner(
                server_url="https://iqm.example",
                quantum_computer="garnet",
                token="tok",
            )
            score, details = runner.run_metric(
                qc,
                AerRunConfig(shots=4, optimization_level=1, seed_transpiler=7, layout_method="sabre"),
                lambda counts: counts.get("1111", 0) / max(1, sum(counts.values())),
                return_details=True,
            )

        self.assertAlmostEqual(score, 0.25, places=8)
        self.assertEqual(details.device_provider, "iqm")
        self.assertEqual(details.device_name, "garnet")
        self.assertEqual(details.device_snapshot_fingerprint, "fp")
        self.assertEqual(details.counts, {"0000": 3, "1111": 1})
        self.assertEqual(details.device_mode, "hardware")

    def test_facade_backend_requires_mock_quantum_computer(self) -> None:
        with patch("claimstab.runners.qiskit_iqm._load_iqm_provider_type", return_value=_FakeIQMProvider):
            with self.assertRaises(ValueError):
                QiskitIQMRunner(
                    server_url="https://iqm.example",
                    quantum_computer="garnet",
                    backend_name="facade_aphrodite",
                    token="tok",
                )

    def test_facade_backend_marks_mode_as_facade(self) -> None:
        with (
            patch("claimstab.runners.qiskit_iqm._load_iqm_provider_type", return_value=_FakeIQMProvider),
            patch("claimstab.runners.qiskit_iqm.snapshot_from_backend", return_value={"backend_name": "facade_aphrodite"}),
            patch("claimstab.runners.qiskit_iqm.fingerprint", return_value="fp"),
        ):
            runner = QiskitIQMRunner(
                server_url="https://iqm.example",
                quantum_computer="garnet:mock",
                backend_name="facade_aphrodite",
                token="tok",
            )
        self.assertEqual(runner.device_mode, "facade")

    def test_available_backends_lists_default_and_facade(self) -> None:
        with patch("claimstab.runners.qiskit_iqm._load_iqm_provider_type", return_value=_FakeIQMProvider):
            rows = QiskitIQMRunner.available_backends(
                server_url="https://iqm.example",
                quantum_computer="garnet:mock",
                token="tok",
                include_facades=True,
            )

        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["mode"], "mock_hardware")
        self.assertTrue(any(row["name"] == "facade_aphrodite" for row in rows))


if __name__ == "__main__":
    unittest.main()
