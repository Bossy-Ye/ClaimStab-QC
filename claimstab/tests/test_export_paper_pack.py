from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestExportPaperPack(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def test_export_paper_pack_tables_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            input_root = td_path / "input"
            out_dir = td_path / "paper_pack"

            maxcut_dir = input_root / "large" / "maxcut_ranking"
            bv_dir = input_root / "large" / "bv_decision"

            self._write_json(
                maxcut_dir / "claim_stability.json",
                {
                    "experiments": [{"experiment_id": "e1"}, {"experiment_id": "e2"}],
                    "comparative": {
                        "space_claim_delta": [
                            {
                                "space_preset": "compilation_only",
                                "claim_pair": "QAOA_p2>RandomBaseline",
                                "delta": 0.0,
                                "decision": "stable",
                                "naive_baseline": {"comparison": "agree", "naive_policy": "legacy_strict_all"},
                                "naive_baseline_realistic": {
                                    "comparison": "naive_underclaim",
                                    "naive_policy": "default_researcher_v1",
                                },
                            },
                            {
                                "space_preset": "sampling_only",
                                "claim_pair": "QAOA_p2>RandomBaseline",
                                "delta": 0.01,
                                "decision": "inconclusive",
                                "naive_baseline": {"comparison": "naive_overclaim", "naive_policy": "legacy_strict_all"},
                                "naive_baseline_realistic": {
                                    "comparison": "agree",
                                    "naive_policy": "default_researcher_v1",
                                },
                            },
                        ]
                    },
                },
            )
            self._write_json(
                maxcut_dir / "rq_summary.json",
                {
                    "rq1_overall_stability": {"claims_checked": 2, "stable_rate": 0.5},
                    "rq4_adaptive_sampling": {"adaptive_sampling": []},
                },
            )

            self._write_json(
                bv_dir / "claim_stability.json",
                {
                    "experiments": [{"experiment_id": "e3"}],
                    "comparative": {
                        "space_claim_delta": [
                            {
                                "space_preset": "sampling_only",
                                "claim_pair": "BVOracle>RandomBaseline",
                                "delta": 0.0,
                                "decision": "stable",
                            }
                        ]
                    },
                },
            )
            self._write_json(
                bv_dir / "rq_summary.json",
                {"rq1_overall_stability": {"claims_checked": 1, "stable_rate": 1.0}},
            )

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claimstab.scripts.export_paper_pack",
                    "--input-root",
                    str(input_root),
                    "--out",
                    str(out_dir),
                    "--which",
                    "large",
                    "--skip-figures",
                ],
                check=True,
            )

            space_csv = out_dir / "tables" / "space_claim_delta.csv"
            rq_csv = out_dir / "tables" / "rq_summary.csv"
            naive_snapshot_csv = out_dir / "tables" / "naive_policy_delta_snapshot.csv"
            eval_profile_csv = out_dir / "tables" / "evaluation_profile_snapshot.csv"
            rq2_by_space_csv = out_dir / "tables" / "rq2_top_dimensions_by_space.csv"
            rq7_main_by_space_csv = out_dir / "tables" / "rq7_top_main_effects_by_space.csv"
            rq7_interaction_by_space_csv = out_dir / "tables" / "rq7_top_interactions_by_space.csv"
            manifest_path = out_dir / "paper_pack_manifest.json"
            self.assertTrue(space_csv.exists())
            self.assertTrue(rq_csv.exists())
            self.assertTrue(naive_snapshot_csv.exists())
            self.assertTrue(eval_profile_csv.exists())
            self.assertTrue(rq2_by_space_csv.exists())
            self.assertTrue(rq7_main_by_space_csv.exists())
            self.assertTrue(rq7_interaction_by_space_csv.exists())
            self.assertTrue(manifest_path.exists())

            with space_csv.open("r", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row.get("source_run") == "maxcut_ranking" for row in rows))

            with rq_csv.open("r", encoding="utf-8") as fh:
                rq_rows = list(csv.DictReader(fh))
            self.assertEqual(len(rq_rows), 2)
            with naive_snapshot_csv.open("r", encoding="utf-8") as fh:
                naive_rows = list(csv.DictReader(fh))
            self.assertGreaterEqual(len(naive_rows), 2)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest.get("schema_version"), "paper_pack_v1")
            self.assertIn("git_commit", manifest)
            self.assertEqual(manifest.get("outputs", {}).get("tables", {}).get("space_claim_delta_rows"), 2)
            self.assertEqual(manifest.get("outputs", {}).get("tables", {}).get("evaluation_profile_snapshot_rows"), 2)
            self.assertGreaterEqual(
                int(manifest.get("outputs", {}).get("tables", {}).get("naive_policy_delta_snapshot_rows", 0)),
                2,
            )
            self.assertEqual(manifest.get("outputs", {}).get("figures", {}).get("skipped"), True)
            primary = manifest.get("source", {}).get("primary_space_claim_source")
            self.assertIsInstance(primary, str)
            self.assertIn("maxcut_ranking", primary)
            inputs = manifest.get("inputs", [])
            self.assertGreaterEqual(len(inputs), 4)
            self.assertTrue(all("sha256" in row for row in inputs if isinstance(row, dict)))


if __name__ == "__main__":
    unittest.main()
