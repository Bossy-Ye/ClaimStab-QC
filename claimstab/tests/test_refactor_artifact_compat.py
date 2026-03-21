from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from claimstab.scripts.check_refactor_compat import compare_normalized_artifacts
from claimstab.tests.helpers_characterization import normalize_payload, run_main_smoke, run_multidevice_smoke


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "characterization"
REPO_ROOT = Path(__file__).resolve().parents[2]
RQ_KEYS = [
    "rq1_prevalence",
    "rq2_drivers",
    "rq3_cost_tradeoff",
    "rq4_adaptive_sampling",
    "rq5_conditional_robustness",
    "rq6_stratified_stability",
    "rq7_effect_diagnostics",
]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class TestRefactorArtifactCompat(unittest.TestCase):
    def test_main_artifact_diff_and_semantic_contract(self) -> None:
        payload = run_main_smoke(repo_root=REPO_ROOT, task="maxcut")
        normalized = normalize_payload(payload, kind="main")
        expected = _load_fixture("main_maxcut_randomk.json")
        diff = compare_normalized_artifacts(normalized, expected, mode="main_maxcut")
        self.assertTrue(diff.equal, msg=diff.summary())

        comparative_rows = payload.get("comparative", {}).get("space_claim_delta", [])
        self.assertGreater(len(comparative_rows), 0)
        for row in comparative_rows:
            self.assertIn("naive_baseline", row)
            self.assertIn("naive_baseline_realistic", row)

        experiments = payload.get("experiments", [])
        self.assertGreater(len(experiments), 0)
        self.assertIn("interpretation_defaults", payload.get("meta", {}))
        for exp in experiments:
            self.assertIn("interpretation", exp)
            evidence = exp.get("evidence", {})
            self.assertIn("cep", evidence)
            cep = evidence.get("cep", {})
            self.assertIn("config_fingerprint", cep)
            self.assertIn("observation", cep)
            delta_rows = exp.get("overall", {}).get("delta_sweep", [])
            self.assertTrue(delta_rows)
            self.assertIn("decision_explanation", delta_rows[0])
            self.assertIn("inconclusive_reason", delta_rows[0])

        rq_summary = payload.get("rq_summary", {})
        for key in RQ_KEYS:
            self.assertIn(key, rq_summary)

    @unittest.skipUnless(importlib.util.find_spec("qiskit_ibm_runtime") is not None, "qiskit_ibm_runtime is required")
    def test_multidevice_artifact_diff(self) -> None:
        payload = run_multidevice_smoke(repo_root=REPO_ROOT)
        normalized = normalize_payload(payload, kind="multidevice")
        expected = _load_fixture("multidevice_transpile_only.json")
        diff = compare_normalized_artifacts(normalized, expected, mode="multidevice")
        self.assertTrue(diff.equal, msg=diff.summary())

        rows = payload.get("device_summary", [])
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows, payload.get("comparative", {}).get("space_claim_delta", []))

    def test_check_refactor_compat_script_smoke(self) -> None:
        cmd = [
            sys.executable,
            "-m",
            "claimstab.scripts.check_refactor_compat",
            "--repo-root",
            str(REPO_ROOT),
            "--mode",
            "main_maxcut",
        ]
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertIn("[main_maxcut] PASS", proc.stdout)


if __name__ == "__main__":
    unittest.main()
