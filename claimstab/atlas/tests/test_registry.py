from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab.atlas import publish_result, validate_atlas


class TestAtlasRegistry(unittest.TestCase):
    def _write_min_run(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {"task": "maxcut", "suite": "core"},
            "experiments": [{"claim": {"type": "ranking"}}],
        }
        (out_dir / "claim_stability.json").write_text(json.dumps(payload), encoding="utf-8")
        (out_dir / "scores.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    def test_publish_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            atlas_root = root / "atlas"
            self._write_min_run(run_dir)

            record = publish_result(
                run_dir,
                atlas_root=atlas_root,
                contributor="tester",
                title="smoke",
                submission_id="smoke_001",
            )

            self.assertEqual(record["submission_id"], "smoke_001")
            self.assertTrue((atlas_root / "index.json").exists())
            self.assertTrue((atlas_root / "submissions" / "smoke_001" / "claim_stability.json").exists())
            self.assertTrue((atlas_root / "submissions" / "smoke_001" / "metadata.json").exists())

            result = validate_atlas(atlas_root)
            self.assertEqual(result.submission_count, 1)
            self.assertEqual(result.warnings, [])

    def test_publish_requires_claim_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(ValueError):
                publish_result(run_dir, atlas_root=Path(td) / "atlas")


if __name__ == "__main__":
    unittest.main()
