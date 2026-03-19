from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestQECPilotPlotScript(unittest.TestCase):
    def test_cli_writes_publication_figure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            json_path = root / "claim_stability.json"
            spec_path = root / "spec.yml"
            out_base = root / "qec_pilot_summary"

            json_path.write_text(
                json.dumps(
                    {
                        "experiments": [
                            {
                                "claim": {
                                    "type": "ranking",
                                    "method_a": "GlobalMajority",
                                    "method_b": "SingleReadout",
                                    "metric_name": "logical_error_rate",
                                    "higher_is_better": False,
                                },
                                "sampling": {
                                    "space_preset": "sampling_only",
                                    "sampled_configurations_with_baseline": 17,
                                },
                                "overall": {
                                    "delta_sweep": [
                                        {
                                            "delta": 0.0,
                                            "decision": "stable",
                                            "stability_hat": 1.0,
                                            "stability_ci_low": 0.97,
                                            "stability_ci_high": 1.0,
                                            "holds_rate_mean": 1.0,
                                            "n_claim_evals": 128,
                                            "decision_explanation": {"threshold": 0.95},
                                        },
                                        {
                                            "delta": 0.05,
                                            "decision": "unstable",
                                            "stability_hat": 0.53,
                                            "stability_ci_low": 0.44,
                                            "stability_ci_high": 0.62,
                                            "holds_rate_mean": 0.88,
                                            "n_claim_evals": 128,
                                            "decision_explanation": {"threshold": 0.95},
                                        },
                                    ]
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            spec_path.write_text(
                textwrap.dedent(
                    """
                    spec_version: 1
                    task:
                      kind: external
                      params:
                        distance: 5
                        physical_error_rate: 0.15
                        num_instances: 8
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claimstab.scripts.plot_qec_pilot",
                    "--json",
                    str(json_path),
                    "--spec",
                    str(spec_path),
                    "--out",
                    str(out_base),
                ],
                check=True,
            )

            self.assertTrue(out_base.with_suffix(".pdf").exists())
            self.assertTrue(out_base.with_suffix(".svg").exists())
            self.assertTrue(out_base.with_suffix(".png").exists())


if __name__ == "__main__":
    unittest.main()
