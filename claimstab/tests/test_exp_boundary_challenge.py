from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestBoundaryChallengeScript(unittest.TestCase):
    def _write_payload(self, root: Path, *, decisions: list[str]) -> Path:
        run_dir = root / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for idx, decision in enumerate(decisions):
            rows.append(
                {
                    "space_preset": "sampling_only" if idx % 2 == 0 else "combined_light",
                    "claim_type": "ranking",
                    "claim_pair": "QAOA_p2>QAOA_p1",
                    "metric_name": "objective",
                    "delta": 0.01 if idx % 2 == 0 else 0.05,
                    "decision": decision,
                }
            )
        payload = {"comparative": {"space_claim_delta": rows}}
        out_json = run_dir / "claim_stability.json"
        out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out_json

    def test_boundary_signal_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_payload(root, decisions=["stable", "inconclusive"])
            cmd = [
                sys.executable,
                "paper/experiments/scripts/exp_boundary_challenge.py",
                "--out",
                str(root),
                "--skip-run",
                "--require-boundary-signal",
            ]
            proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], check=False)
            self.assertEqual(proc.returncode, 0)
            summary = json.loads((root / "boundary_summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["boundary_signal_detected"])

    def test_require_boundary_signal_fails_without_signal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_payload(root, decisions=["stable", "stable"])
            cmd = [
                sys.executable,
                "paper/experiments/scripts/exp_boundary_challenge.py",
                "--out",
                str(root),
                "--skip-run",
                "--require-boundary-signal",
            ]
            proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], check=False)
            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
