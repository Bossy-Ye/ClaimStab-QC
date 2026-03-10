from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claimstab.atlas.catalog import build_dataset_registry_markdown


class TestAtlasCatalog(unittest.TestCase):
    def test_build_dataset_registry_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "atlas"
            sub = root / "submissions" / "s1"
            sub.mkdir(parents=True, exist_ok=True)
            (sub / "claim_stability.json").write_text(
                json.dumps(
                    {
                        "meta": {"methods_available": ["M1", "M2"]},
                        "experiments": [
                            {
                                "claim": {"type": "ranking", "method_a": "M1", "method_b": "M2", "deltas": [0.0]},
                                "sampling": {
                                    "space_preset": "sampling_only",
                                    "mode": "random_k",
                                    "sample_size": 5,
                                    "seed": 1,
                                    "sampled_configurations_with_baseline": 6,
                                    "perturbation_space_size": 100,
                                },
                                "baseline": {"seed_transpiler": 0},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "index.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "submissions": [
                            {
                                "submission_id": "s1",
                                "title": "t1",
                                "contributor": "u1",
                                "task": "toy",
                                "suite": "core",
                                "claim_types": ["ranking"],
                                "created_at_utc": "2026-03-03T00:00:00+00:00",
                                "artifacts": {
                                    "claim_stability.json": "submissions/s1/claim_stability.json"
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            md = build_dataset_registry_markdown(root, repo_url="https://example.com/repo")
            self.assertIn("# Dataset Registry", md)
            self.assertIn("<code>s1</code>", md)
            self.assertIn(">toy<", md)
            self.assertIn('data-href="#submission-s1"', md)
            self.assertIn("ranking: M1 &gt; M2", md)
            self.assertIn("sampling_only", md)


if __name__ == "__main__":
    unittest.main()
