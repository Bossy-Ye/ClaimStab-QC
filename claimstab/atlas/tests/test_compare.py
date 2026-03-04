from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab.atlas.compare import compare_claim_outputs


class TestAtlasCompare(unittest.TestCase):
    def _write_payload(self, path: Path, *, decision: str, flip: float, stability: float, naive: str) -> None:
        payload = {
            "meta": {"task": "maxcut", "suite": "core"},
            "comparative": {
                "space_claim_delta": [
                    {
                        "claim_type": "ranking",
                        "space_preset": "sampling_only",
                        "claim_pair": "QAOA_p2>QAOA_p1",
                        "metric_name": "objective",
                        "delta": 0.0,
                        "decision": decision,
                        "flip_rate_mean": flip,
                        "stability_hat": stability,
                        "naive_baseline": {"comparison": naive},
                    }
                ]
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_compare_detects_decision_and_naive_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left_json = root / "left.json"
            right_json = root / "right.json"
            self._write_payload(left_json, decision="stable", flip=0.1, stability=0.9, naive="agree")
            self._write_payload(right_json, decision="unstable", flip=0.3, stability=0.7, naive="naive_overclaim")

            diff = compare_claim_outputs(left_json, right_json)
            self.assertEqual(diff["paired_rows"], 1)
            self.assertEqual(diff["decision_changed_count"], 1)
            self.assertEqual(diff["naive_comparison_changed_count"], 1)
            self.assertAlmostEqual(float(diff["mean_flip_rate_delta"]), 0.2, places=8)
            self.assertAlmostEqual(float(diff["mean_stability_hat_delta"]), -0.2, places=8)
            self.assertEqual(len(diff["left_only_keys"]), 0)
            self.assertEqual(len(diff["right_only_keys"]), 0)

    def test_compare_accepts_run_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left_dir = root / "left_run"
            right_dir = root / "right_run"
            left_dir.mkdir(parents=True, exist_ok=True)
            right_dir.mkdir(parents=True, exist_ok=True)
            self._write_payload(left_dir / "claim_stability.json", decision="stable", flip=0.1, stability=0.9, naive="agree")
            self._write_payload(right_dir / "claim_stability.json", decision="stable", flip=0.2, stability=0.8, naive="agree")

            diff = compare_claim_outputs(left_dir, right_dir)
            self.assertEqual(diff["paired_rows"], 1)
            self.assertEqual(diff["decision_changed_count"], 0)
            self.assertEqual(diff["naive_comparison_changed_count"], 0)


if __name__ == "__main__":
    unittest.main()
