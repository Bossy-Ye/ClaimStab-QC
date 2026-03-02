import unittest
import sys

from qiskit import QuantumCircuit

from claimstab.devices.registry import parse_device_profile, resolve_device_profile
from claimstab.runners.qiskit_aer import AerRunConfig, AerSimulator, QiskitAerRunner


class TestQiskitAerRunner(unittest.TestCase):
    @staticmethod
    def _toy_circuit() -> QuantumCircuit:
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()
        return qc

    def test_spot_check_noise_requires_aer_engine(self) -> None:
        with self.assertRaises(ValueError):
            QiskitAerRunner(engine="basic", spot_check_noise=True)

    def test_aer_requested_without_package_raises(self) -> None:
        if AerSimulator is None:
            with self.assertRaises(ImportError):
                QiskitAerRunner(engine="aer")

    def test_spot_check_noise_initializes_when_aer_available(self) -> None:
        if AerSimulator is None:
            self.skipTest("qiskit-aer not available")
        runner = QiskitAerRunner(engine="aer", spot_check_noise=True)
        self.assertIsNotNone(runner.noise_model)

    def test_default_run_has_no_device_metadata(self) -> None:
        runner = QiskitAerRunner(engine="basic")
        qc = self._toy_circuit()
        res = runner.run_counts(qc, cfg=AerRunConfig(shots=64))
        self.assertIsNotNone(res.counts)
        self.assertIsNone(res.device_provider)
        self.assertIsNone(res.device_name)
        self.assertIsNone(res.device_mode)

    def test_transpile_only_returns_structural_stats(self) -> None:
        profile = parse_device_profile(
            {
                "enabled": True,
                "provider": "ibm_fake",
                "name": "FakeManilaV2",
                "mode": "transpile_only",
            }
        )
        try:
            resolved = resolve_device_profile(profile)
        except Exception as exc:
            self.skipTest(f"IBM fake backend unavailable: {exc}")

        runner = QiskitAerRunner(engine="basic")
        qc = self._toy_circuit()

        res = runner.run_counts(
            qc,
            cfg=AerRunConfig(shots=64, optimization_level=1, seed_transpiler=0, seed_simulator=0),
            device_profile=resolved.profile,
            device_backend=resolved.backend,
            noise_model_mode="none",
            device_snapshot_fingerprint=resolved.snapshot_fingerprint,
            device_snapshot_summary=resolved.snapshot,
        )
        self.assertIsNone(res.counts)
        self.assertGreaterEqual(res.transpiled_depth, 1)
        self.assertGreaterEqual(res.two_qubit_count, 1)
        self.assertEqual(res.device_mode, "transpile_only")
        self.assertEqual(res.device_snapshot_fingerprint, resolved.snapshot_fingerprint)

    def test_noisy_sim_produces_counts_when_available(self) -> None:
        if sys.version_info >= (3, 13):
            self.skipTest("qiskit-aer noisy fake-backend simulation is unstable on Python 3.13 in this environment")
        if AerSimulator is None:
            self.skipTest("qiskit-aer not available")
        profile = parse_device_profile(
            {
                "enabled": True,
                "provider": "ibm_fake",
                "name": "FakeManilaV2",
                "mode": "noisy_sim",
            }
        )
        try:
            resolved = resolve_device_profile(profile)
        except Exception as exc:
            self.skipTest(f"IBM fake backend unavailable: {exc}")

        runner = QiskitAerRunner(engine="aer")
        qc = self._toy_circuit()

        try:
            res = runner.run_counts(
                qc,
                cfg=AerRunConfig(shots=64, optimization_level=1, seed_transpiler=0, seed_simulator=0),
                device_profile=resolved.profile,
                device_backend=resolved.backend,
                noise_model_mode="from_device_profile",
                device_snapshot_fingerprint=resolved.snapshot_fingerprint,
                device_snapshot_summary=resolved.snapshot,
            )
        except Exception as exc:
            self.skipTest(f"Noisy simulation runtime unavailable: {exc}")
        self.assertIsNotNone(res.counts)
        self.assertGreater(sum(res.counts.values()), 0)
        self.assertEqual(res.device_mode, "noisy_sim")
        self.assertEqual(res.device_snapshot_fingerprint, resolved.snapshot_fingerprint)


if __name__ == "__main__":
    unittest.main()
