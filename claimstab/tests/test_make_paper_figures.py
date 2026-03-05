from __future__ import annotations

import unittest

from claimstab.scripts.make_paper_figures import _collect_naive_rows


class TestMakePaperFiguresNaiveRows(unittest.TestCase):
    def test_collect_naive_rows_includes_legacy_and_realistic(self) -> None:
        payload = {
            "comparative": {
                "space_claim_delta": [
                    {
                        "space_preset": "sampling_only",
                        "claim_type": "ranking",
                        "naive_baseline": {"comparison": "agree", "naive_policy": "legacy_strict_all"},
                        "naive_baseline_realistic": {
                            "comparison": "naive_overclaim",
                            "naive_policy": "default_researcher_v1",
                        },
                    }
                ]
            }
        }
        df = _collect_naive_rows(payload)
        self.assertEqual(len(df), 2)
        self.assertEqual(set(df["policy"].tolist()), {"legacy_strict_all", "default_researcher_v1"})
        self.assertEqual(set(df["comparison"].tolist()), {"agree", "naive_overclaim"})


if __name__ == "__main__":
    unittest.main()
