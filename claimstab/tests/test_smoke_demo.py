from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestSmokeDemo(unittest.TestCase):
    def _run_demo(self, *, task: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / task
            cmd = [
                sys.executable,
                "examples/claim_stability_demo.py",
                "--task",
                task,
                "--suite",
                "core",
                "--space-preset",
                "baseline",
                "--sampling-mode",
                "random_k",
                "--sample-size",
                "4",
                "--sample-seed",
                "1",
                "--backend-engine",
                "basic",
                "--out-dir",
                str(out_dir),
            ]
            subprocess.run(cmd, check=True)
            payload = json.loads((out_dir / "claim_stability.json").read_text(encoding="utf-8"))
            self.assertTrue((out_dir / "rq_summary.json").exists())
            return payload

    def test_maxcut_ranking_smoke(self) -> None:
        payload = self._run_demo(task="maxcut")
        self.assertIn("experiments", payload)
        self.assertGreater(len(payload["experiments"]), 0)

    def test_bv_decision_smoke(self) -> None:
        payload = self._run_demo(task="bv")
        claim_types = {str(exp.get("claim", {}).get("type")) for exp in payload.get("experiments", [])}
        self.assertIn("decision", claim_types)
        top_ks = sorted(
            {
                int(exp.get("claim", {}).get("top_k"))
                for exp in payload.get("experiments", [])
                if exp.get("claim", {}).get("type") == "decision"
            }
        )
        self.assertEqual(top_ks, [1, 3])


if __name__ == "__main__":
    unittest.main()
