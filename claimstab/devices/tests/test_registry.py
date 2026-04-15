import unittest
from unittest.mock import patch

from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile


class TestDeviceRegistry(unittest.TestCase):
    def test_missing_device_profile_defaults_disabled(self) -> None:
        profile = parse_device_profile(None)
        self.assertFalse(profile.enabled)
        self.assertEqual(profile.provider, "none")

    def test_noise_model_default_none(self) -> None:
        self.assertEqual(parse_noise_model_mode(None), "none")
        self.assertEqual(parse_noise_model_mode({}), "none")

    def test_ibm_fake_missing_dependency_raises_clean_error(self) -> None:
        profile = parse_device_profile(
            {
                "enabled": True,
                "provider": "ibm_fake",
                "name": "FakeManilaV2",
                "mode": "transpile_only",
            }
        )
        with patch("claimstab.devices.ibm_fake.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(ImportError) as ctx:
                resolve_device_profile(profile)
        self.assertIn("qiskit-ibm-runtime", str(ctx.exception))

    def test_iqm_fake_provider_is_accepted(self) -> None:
        profile = parse_device_profile(
            {
                "enabled": True,
                "provider": "iqm_fake",
                "name": "IQMFakeAphrodite",
                "mode": "noisy_sim",
            }
        )
        self.assertTrue(profile.enabled)
        self.assertEqual(profile.provider, "iqm_fake")
        self.assertEqual(profile.name, "IQMFakeAphrodite")
        self.assertEqual(profile.mode, "noisy_sim")

    def test_iqm_fake_missing_dependency_raises_clean_error(self) -> None:
        profile = parse_device_profile(
            {
                "enabled": True,
                "provider": "iqm_fake",
                "name": "IQMFakeAphrodite",
                "mode": "noisy_sim",
            }
        )
        with patch("claimstab.devices.iqm_fake.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(ImportError) as ctx:
                resolve_device_profile(profile)
        self.assertIn("iqm-client", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
