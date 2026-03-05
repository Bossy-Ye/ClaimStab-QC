from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestDistributionPipelineEndToEnd(unittest.TestCase):
    def test_grover_distribution_claim_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            spec_path = td_path / "spec.yml"
            out_dir = td_path / "out"
            spec_path.write_text(
                textwrap.dedent(
                    """
                    spec_version: 1
                    task:
                      kind: grover
                      suite: core
                      params:
                        min_qubits: 6
                        max_qubits: 6
                        instances_per_qubit: 2
                    methods:
                      - name: GroverOracle
                        kind: grover
                      - name: UniformBaseline
                        kind: uniform
                    claims:
                      - type: distribution
                        method: GroverOracle
                        epsilon: 0.06
                        primary_distance: js
                        sanity_distance: tvd
                        reference_shots: max
                        metric_name: objective
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                "-m",
                "claimstab.pipelines.claim_stability_app",
                "--spec",
                str(spec_path),
                "--space-preset",
                "sampling_only",
                "--sampling-mode",
                "random_k",
                "--sample-size",
                "12",
                "--sample-seed",
                "11",
                "--backend-engine",
                "basic",
                "--out-dir",
                str(out_dir),
            ]
            subprocess.run(cmd, check=True)

            payload = json.loads((out_dir / "claim_stability.json").read_text(encoding="utf-8"))
            comparative_rows = payload.get("comparative", {}).get("space_claim_delta", [])
            self.assertTrue(comparative_rows)
            self.assertTrue(all(str(row.get("claim_type")) == "distribution" for row in comparative_rows))

            decisions = {str(row.get("decision")) for row in comparative_rows}
            self.assertNotIn("stable", decisions)
            self.assertTrue(decisions.intersection({"unstable", "inconclusive"}))

            experiments = payload.get("experiments", [])
            self.assertTrue(experiments)
            self.assertIn("distribution", {str(exp.get("claim", {}).get("type")) for exp in experiments})
            first = experiments[0]
            violations = first.get("overall", {}).get("distribution_violations", [])
            self.assertIsInstance(violations, list)
            self.assertGreater(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
