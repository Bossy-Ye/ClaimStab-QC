from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestSmokeDemo(unittest.TestCase):
    def _run_demo(self, *, task: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / task
            cmd = [
                sys.executable,
                "-m",
                "claimstab.pipelines.claim_stability_app",
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
            self.assertTrue((out_dir / "robustness_map.json").exists())
            robustness_payload = json.loads((out_dir / "robustness_map.json").read_text(encoding="utf-8"))
            self.assertIn("cells", robustness_payload)
            return payload

    def test_maxcut_ranking_smoke(self) -> None:
        payload = self._run_demo(task="maxcut")
        self.assertIn("experiments", payload)
        self.assertGreater(len(payload["experiments"]), 0)
        self.assertEqual(payload.get("meta", {}).get("evidence_chain", {}).get("protocol"), "cep_v1")
        self.assertIn("interpretation_defaults", payload.get("meta", {}))
        practicality = payload.get("meta", {}).get("practicality", {})
        self.assertEqual(practicality.get("num_workers"), 1)
        self.assertIn("total_wall_time", practicality)
        self.assertIn("throughput_runs_per_sec", practicality)
        self.assertIn("runner_timing", practicality)
        first = payload.get("experiments", [])[0]
        self.assertIn("interpretation", first)
        self.assertIn("cep", first.get("evidence", {}))
        first_delta = first.get("overall", {}).get("delta_sweep", [])[0]
        self.assertIn("decision_explanation", first_delta)
        self.assertIn("inconclusive_reason", first_delta)
        comparative = payload.get("comparative", {}).get("space_claim_delta", [])
        self.assertTrue(comparative)
        self.assertIn("naive_baseline", comparative[0])
        self.assertIn("naive_baseline_realistic", comparative[0])
        self.assertIn("decision_explanation", comparative[0])
        self.assertIn("inconclusive_reason", comparative[0])

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

    def test_bv_decision_adaptive_sampling_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            spec_path = td_path / "spec.yml"
            out_dir = td_path / "adaptive_bv"
            spec_path.write_text(
                textwrap.dedent(
                    """
                    spec_version: 1
                    task:
                      kind: bv
                      suite: core
                      params:
                        hidden_strings: ["0001", "0011", "0101"]
                    methods:
                      - name: BVOracle
                        kind: bv
                      - name: RandomBaseline
                        kind: random_baseline
                    claims:
                      - type: decision
                        method: BVOracle
                        top_k: 1
                        label_meta_key: target_label
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claimstab.pipelines.claim_stability_app",
                    "--spec",
                    str(spec_path),
                    "--space-preset",
                    "sampling_only",
                    "--sampling-mode",
                    "adaptive_ci",
                    "--target-ci-width",
                    "0.10",
                    "--max-sample-size",
                    "16",
                    "--min-sample-size",
                    "4",
                    "--step-size",
                    "4",
                    "--sample-seed",
                    "7",
                    "--backend-engine",
                    "basic",
                    "--out-dir",
                    str(out_dir),
                ],
                check=True,
            )
            payload = json.loads((out_dir / "claim_stability.json").read_text(encoding="utf-8"))
            decision_experiments = [
                exp for exp in payload.get("experiments", []) if str(exp.get("claim", {}).get("type")) == "decision"
            ]
            self.assertTrue(decision_experiments)
            for exp in decision_experiments:
                sampling = exp.get("sampling", {})
                self.assertEqual(str(sampling.get("mode")), "adaptive_ci")
                adaptive = sampling.get("adaptive_stopping")
                self.assertIsInstance(adaptive, dict)
                self.assertTrue(bool(adaptive.get("enabled")))
                self.assertIsNotNone(adaptive.get("stop_reason"))
                self.assertIn("stop_reason_detail", adaptive)
                self.assertIn("budget_used", adaptive)
                self.assertIn("budget_limit", adaptive)
                eval_profile = exp.get("overall", {}).get("evaluation_profile", {})
                self.assertIn("adaptive_stop_reason_detail", eval_profile)
                self.assertIn("budget_used", eval_profile)
                self.assertIn("budget_limit", eval_profile)

    def test_replay_trace_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            first_dir = Path(td) / "first"
            replay_dir = Path(td) / "replay"
            trace_path = Path(td) / "trace.jsonl"

            cmd_first = [
                sys.executable,
                "-m",
                "claimstab.pipelines.claim_stability_app",
                "--task",
                "maxcut",
                "--suite",
                "core",
                "--space-preset",
                "baseline",
                "--sampling-mode",
                "random_k",
                "--sample-size",
                "3",
                "--sample-seed",
                "1",
                "--backend-engine",
                "basic",
                "--trace-out",
                str(trace_path),
                "--out-dir",
                str(first_dir),
            ]
            subprocess.run(cmd_first, check=True)
            self.assertTrue(trace_path.exists())

            cmd_replay = [
                sys.executable,
                "-m",
                "claimstab.pipelines.claim_stability_app",
                "--task",
                "maxcut",
                "--suite",
                "core",
                "--space-preset",
                "baseline",
                "--replay-trace",
                str(trace_path),
                "--out-dir",
                str(replay_dir),
            ]
            subprocess.run(cmd_replay, check=True)

            first_payload = json.loads((first_dir / "claim_stability.json").read_text(encoding="utf-8"))
            replay_payload = json.loads((replay_dir / "claim_stability.json").read_text(encoding="utf-8"))
            self.assertEqual(len(first_payload.get("experiments", [])), len(replay_payload.get("experiments", [])))
            self.assertEqual(
                len(first_payload.get("comparative", {}).get("space_claim_delta", [])),
                len(replay_payload.get("comparative", {}).get("space_claim_delta", [])),
            )
            self.assertEqual(
                replay_payload.get("meta", {}).get("artifacts", {}).get("replay_trace"),
                str(trace_path),
            )
            replay_runtime = replay_payload.get("meta", {}).get("runtime", {})
            self.assertEqual(replay_runtime.get("dependencies"), {})
            self.assertIsNone(replay_runtime.get("git_commit"))
            self.assertIsNone(replay_runtime.get("git_dirty"))

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claimstab.cli",
                    "validate-evidence",
                    "--json",
                    str(replay_dir / "claim_stability.json"),
                ],
                check=True,
            )


if __name__ == "__main__":
    unittest.main()
