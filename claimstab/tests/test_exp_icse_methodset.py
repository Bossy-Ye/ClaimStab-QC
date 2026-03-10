from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestICSEMethodsetScript(unittest.TestCase):
    def test_skip_run_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "methodset"
            cmd = [
                sys.executable,
                "examples/exp_icse_methodset.py",
                "--out",
                str(out_root),
                "--skip-run",
            ]
            proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], check=False)
            self.assertEqual(proc.returncode, 0)
            summary_path = out_root / "methodset_summary.json"
            self.assertTrue(summary_path.exists())
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema_version"), "icse_methodset_v1")
            self.assertEqual(int(payload.get("total_tracks", -1)), 0)


if __name__ == "__main__":
    unittest.main()
