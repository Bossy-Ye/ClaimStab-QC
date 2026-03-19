from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestMutationSanityScript(unittest.TestCase):
    def _write_run_dir(self, root: Path) -> None:
        claim_payload = {
            "experiments": [
                {
                    "experiment_id": "sampling_only:MethodA>MethodB",
                    "claim": {
                        "type": "ranking",
                        "method_a": "MethodA",
                        "method_b": "MethodB",
                        "deltas": [0.0, 0.1],
                        "metric_name": "objective",
                        "higher_is_better": True,
                    },
                    "baseline": {
                        "seed_transpiler": 0,
                        "optimization_level": 1,
                        "layout_method": "trivial",
                        "shots": 1024,
                        "seed_simulator": 0,
                    },
                    "stability_rule": {
                        "threshold": 0.95,
                        "confidence_level": 0.95,
                    },
                    "sampling": {
                        "space_preset": "sampling_only",
                    },
                }
            ]
        }
        (root / "claim_stability.json").write_text(json.dumps(claim_payload, indent=2), encoding="utf-8")

        with (root / "scores.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "suite",
                    "space_preset",
                    "instance_id",
                    "seed_transpiler",
                    "optimization_level",
                    "layout_method",
                    "seed_simulator",
                    "shots",
                    "method",
                    "metric_name",
                    "score",
                    "transpiled_depth",
                    "transpiled_size",
                    "device_provider",
                    "device_name",
                    "device_mode",
                    "device_snapshot_fingerprint",
                    "circuit_depth",
                    "two_qubit_count",
                    "swap_count",
                    "transpile_time_ms",
                    "execute_time_ms",
                    "wall_time_ms",
                ]
            )
            for seed_transpiler, score_a, score_b in [
                (0, 0.90, 0.50),
                (1, 0.88, 0.52),
                (2, 0.86, 0.51),
            ]:
                for method, score in [("MethodA", score_a), ("MethodB", score_b)]:
                    writer.writerow(
                        [
                            "core",
                            "sampling_only",
                            "g1",
                            seed_transpiler,
                            1,
                            "trivial",
                            0,
                            1024,
                            method,
                            "objective",
                            score,
                            8,
                            8,
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )

    def test_script_detects_fragility_signal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            self._write_run_dir(run_dir)
            out_path = Path(td) / "mutation_sanity_summary.json"

            cmd = [
                sys.executable,
                "paper/experiments/scripts/exp_mutation_sanity.py",
                "--run-dir",
                str(run_dir),
                "--out",
                str(out_path),
                "--require-fragility-signal",
            ]
            proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], check=False)
            self.assertEqual(proc.returncode, 0)

            summary = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertTrue(summary["fragility_signal_detected"])
            self.assertEqual(summary["case_count"], 1)
            case = summary["cases"][0]
            self.assertEqual(case["mutation"]["kind"], "baseline_relation_flip")
            self.assertTrue(case["fragility_signal_detected"])


if __name__ == "__main__":
    unittest.main()
