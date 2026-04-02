from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab import cli


class TestVQEPilotDemo(unittest.TestCase):
    def test_vqe_pilot_spec_runs_end_to_end(self) -> None:
        spec_path = Path("examples/community/vqe_pilot_demo/spec_vqe_h2.yml")
        self.assertTrue(spec_path.exists())

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "vqe_pilot"
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(out_dir),
                    "--validate",
                ]
            )
            self.assertEqual(rc, 0)

            payload = json.loads((out_dir / "claim_stability.json").read_text(encoding="utf-8"))
            self.assertEqual(payload.get("meta", {}).get("task"), "vqe_h2_pilot")
            experiments = payload.get("experiments", [])
            self.assertEqual(len(experiments), 6)
            for experiment in experiments:
                claim = experiment.get("claim", {})
                self.assertEqual(claim.get("metric_name"), "energy_error")
                self.assertFalse(bool(claim.get("higher_is_better", True)))
                delta_sweep = experiment.get("overall", {}).get("delta_sweep", [])
                self.assertEqual(len(delta_sweep), 3)


if __name__ == "__main__":
    unittest.main()
