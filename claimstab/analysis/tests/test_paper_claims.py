from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab.analysis.paper_claims import generate_paper_claims_outputs, resolve_paper_claims


class TestPaperClaims(unittest.TestCase):
    def test_resolve_paper_claims_maps_and_marks_missing(self) -> None:
        claims = [
            {
                "id": "C1",
                "text": "A",
                "mapping": {
                    "type": "ranking",
                    "claim_pair": "QAOA_p2>RandomBaseline",
                    "space": "sampling_only",
                    "delta": 0.01,
                },
            },
            {
                "id": "C2",
                "text": "B",
                "mapping": {
                    "type": "ranking",
                    "claim_pair": "QAOA_p2>QAOA_p1",
                    "space": "sampling_only",
                    "delta": 0.01,
                },
            },
        ]
        payload = {
            "comparative": {
                "space_claim_delta": [
                    {
                        "claim_type": "ranking",
                        "claim_pair": "QAOA_p2>RandomBaseline",
                        "space_preset": "sampling_only",
                        "delta": 0.01,
                        "decision": "stable",
                        "stability_hat": 0.97,
                        "stability_ci_low": 0.95,
                        "stability_ci_high": 0.99,
                        "n_claim_evals": 1200,
                    }
                ]
            }
        }
        rows = resolve_paper_claims(claims=claims, claim_payload=payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["claim_id"], "C1")
        self.assertTrue(rows[0]["mapped"])
        self.assertEqual(rows[0]["decision"], "stable")
        self.assertEqual(rows[1]["claim_id"], "C2")
        self.assertFalse(rows[1]["mapped"])
        self.assertEqual(rows[1]["decision"], "missing")

    def test_generate_outputs_writes_csv_and_figures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            claims_yaml = root / "paper_claims.yaml"
            input_json = root / "claim_stability.json"
            out_root = root / "paper_pack"
            claims_yaml.write_text(
                """
paper_claims:
  - id: C1
    text: "Claim one"
    mapping:
      type: ranking
      claim_pair: QAOA_p2>RandomBaseline
      space: sampling_only
      delta: 0.0
""",
                encoding="utf-8",
            )
            input_json.write_text(
                json.dumps(
                    {
                        "comparative": {
                            "space_claim_delta": [
                                {
                                    "claim_type": "ranking",
                                    "claim_pair": "QAOA_p2>RandomBaseline",
                                    "space_preset": "sampling_only",
                                    "delta": 0.0,
                                    "decision": "inconclusive",
                                    "stability_hat": 0.90,
                                    "stability_ci_low": 0.80,
                                    "stability_ci_high": 0.96,
                                    "n_claim_evals": 300,
                                }
                            ]
                        }
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            summary = generate_paper_claims_outputs(
                claims_path=claims_yaml,
                input_json=input_json,
                out_root=out_root,
            )
            self.assertEqual(int(summary["rows"]), 1)
            csv_path = Path(str(summary["csv"]))
            self.assertTrue(csv_path.exists())
            prevalence_csv_path = Path(str(summary["prevalence_csv"]))
            self.assertTrue(prevalence_csv_path.exists())
            prevalence = summary.get("prevalence", [])
            self.assertTrue(prevalence)
            self.assertEqual(prevalence[0].get("decision"), "inconclusive")
            figs = summary.get("figures", {})
            self.assertTrue(Path(str(figs.get("pdf"))).exists())
            self.assertTrue(Path(str(figs.get("png"))).exists())


if __name__ == "__main__":
    unittest.main()
