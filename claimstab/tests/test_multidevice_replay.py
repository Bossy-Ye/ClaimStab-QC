from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("qiskit_ibm_runtime") is not None, "qiskit_ibm_runtime is required")
class TestMultideviceReplaySmoke(unittest.TestCase):
    def test_transpile_only_replay_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            first_dir = td_path / "first"
            replay_dir = td_path / "replay"
            trace_path = td_path / "trace.jsonl"

            cmd_first = [
                sys.executable,
                "-m",
                "claimstab.pipelines.multidevice_app",
                "--run",
                "transpile_only",
                "--suite",
                "core",
                "--sampling-mode",
                "random_k",
                "--sample-size",
                "2",
                "--sample-seed",
                "1",
                "--backend-engine",
                "basic",
                "--transpile-devices",
                "FakeManilaV2",
                "--transpile-claim-pairs",
                "QAOA_p1>QAOA_p2",
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
                "claimstab.pipelines.multidevice_app",
                "--run",
                "transpile_only",
                "--suite",
                "core",
                "--backend-engine",
                "basic",
                "--transpile-devices",
                "FakeManilaV2",
                "--transpile-claim-pairs",
                "QAOA_p1>QAOA_p2",
                "--replay-trace",
                str(trace_path),
                "--out-dir",
                str(replay_dir),
            ]
            subprocess.run(cmd_replay, check=True)

            first_summary = json.loads((first_dir / "combined_summary.json").read_text(encoding="utf-8"))
            replay_summary = json.loads((replay_dir / "combined_summary.json").read_text(encoding="utf-8"))
            self.assertGreater(len(first_summary.get("device_summary", [])), 0)
            self.assertEqual(
                len(first_summary.get("device_summary", [])),
                len(replay_summary.get("device_summary", [])),
            )
            self.assertEqual(
                replay_summary.get("meta", {}).get("artifacts", {}).get("replay_trace"),
                str(trace_path),
            )
            practicality = replay_summary.get("meta", {}).get("practicality", {})
            self.assertEqual(practicality.get("num_workers"), 1)
            self.assertIn("total_wall_time", practicality)
            self.assertIn("throughput_runs_per_sec", practicality)
            self.assertIn("by_batch", practicality)

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claimstab.cli",
                    "validate-evidence",
                    "--json",
                    str(replay_dir / "combined_summary.json"),
                    "--no-trace-check",
                ],
                check=True,
            )


if __name__ == "__main__":
    unittest.main()
