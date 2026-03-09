from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from claimstab.tests.helpers_characterization import normalize_payload, run_main_smoke, run_multidevice_smoke


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "characterization"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class TestPipelineCharacterization(unittest.TestCase):
    def test_main_maxcut_randomk(self) -> None:
        payload = run_main_smoke(repo_root=REPO_ROOT, task="maxcut")
        normalized = normalize_payload(payload, kind="main")
        expected = _load_fixture("main_maxcut_randomk.json")
        self.assertEqual(normalized, expected)

    def test_main_bv_adaptive(self) -> None:
        payload = run_main_smoke(
            repo_root=REPO_ROOT,
            task="bv",
            extra_args=[
                "--sampling-mode",
                "adaptive_ci",
                "--target-ci-width",
                "0.10",
                "--max-sample-size",
                "16",
                "--min-sample-size",
                "4",
                "--step-size",
                "4",
            ],
        )
        normalized = normalize_payload(payload, kind="main")
        expected = _load_fixture("main_bv_adaptive.json")
        self.assertEqual(normalized, expected)

    @unittest.skipUnless(importlib.util.find_spec("qiskit_ibm_runtime") is not None, "qiskit_ibm_runtime is required")
    def test_multidevice_transpile_only(self) -> None:
        payload = run_multidevice_smoke(repo_root=REPO_ROOT)
        normalized = normalize_payload(payload, kind="multidevice")
        expected = _load_fixture("multidevice_transpile_only.json")
        self.assertEqual(normalized, expected)


if __name__ == "__main__":
    unittest.main()
