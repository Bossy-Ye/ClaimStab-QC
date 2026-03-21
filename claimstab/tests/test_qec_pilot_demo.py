from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab import cli


class TestQECPilotDemo(unittest.TestCase):
    def test_qec_pilot_spec_runs_end_to_end(self) -> None:
        spec_path = Path("examples/community/qec_pilot_demo/spec_qec_decoder.yml")
        self.assertTrue(spec_path.exists())

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "qec_pilot"
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
            self.assertIn("experiments", payload)
            self.assertEqual(payload.get("meta", {}).get("task"), "qec_decoder_pilot")
            experiments = payload.get("experiments", [])
            self.assertEqual(len(experiments), 2)
            spaces = {str(exp.get("sampling", {}).get("space_preset")) for exp in experiments}
            self.assertEqual(spaces, {"sampling_only", "combined_light"})

            for experiment in experiments:
                claim = experiment.get("claim", {})
                self.assertEqual(claim.get("type"), "ranking")
                self.assertEqual(claim.get("metric_name"), "logical_error_rate")
                self.assertFalse(bool(claim.get("higher_is_better", True)))

                delta_sweep = experiment.get("overall", {}).get("delta_sweep", [])
                self.assertEqual(len(delta_sweep), 2)
                decisions = {str(row.get("decision")) for row in delta_sweep}
                self.assertTrue(decisions.issubset({"stable", "unstable", "inconclusive"}))
                self.assertIn("decision_explanation", delta_sweep[0])
                self.assertIn("interpretation", experiment)


if __name__ == "__main__":
    unittest.main()
