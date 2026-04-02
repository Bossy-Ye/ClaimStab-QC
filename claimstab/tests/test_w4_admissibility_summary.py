from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestW4AdmissibilitySummary(unittest.TestCase):
    def test_summary_runs_with_two_raters(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            items = root / "admissibility_items_v1.csv"
            ratings = root / "ratings"
            ratings.mkdir(parents=True, exist_ok=True)
            items.write_text(
                "item_id,perturbation,category,expected_label,trigger_rule,notes\n"
                "P01,transpiler seed,compilation,admissible,,.\n"
                "P02,benchmark graph,benchmark,non_admissible,Q1,.\n",
                encoding="utf-8",
            )
            for idx, rows in enumerate(
                [
                    [("P01", "admissible"), ("P02", "non_admissible")],
                    [("P01", "admissible"), ("P02", "non_admissible")],
                ],
                start=1,
            ):
                with (ratings / f"rater_{idx}.csv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["item_id", "label"])
                    writer.writerows(rows)

            cmd = [
                sys.executable,
                "paper/experiments/scripts/summarize_admissibility_v3.py",
                "--items",
                str(items),
                "--ratings-dir",
                str(ratings),
                "--out-root",
                str(root / "out"),
            ]
            proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], check=False)
            self.assertEqual(proc.returncode, 0)
            summary = json.loads(
                (root / "out" / "derived_paper_evaluation" / "RQ2_semantics" / "admissibility_study_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(summary["status"], "complete")
            self.assertGreaterEqual(summary["pairwise_kappa_mean"], 0.99)


if __name__ == "__main__":
    unittest.main()
