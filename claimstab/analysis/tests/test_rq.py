from __future__ import annotations

import unittest

from claimstab.analysis.rq import build_rq_summary


class TestRQDrivers(unittest.TestCase):
    def test_rq2_driver_score_uses_value_contrast(self) -> None:
        payload = {
            "meta": {"task": "maxcut"},
            "comparative": {"space_claim_delta": []},
            "experiments": [
                {
                    "overall": {
                        "diagnostics": {
                            "by_delta_dimension": {
                                "0.0": {
                                    "shots": {
                                        "64": {"flips": 40, "total": 100, "flip_rate": 0.4},
                                        "1024": {"flips": 10, "total": 100, "flip_rate": 0.1},
                                    },
                                    "layout_method": {
                                        "trivial": {"flips": 24, "total": 100, "flip_rate": 0.24},
                                        "sabre": {"flips": 26, "total": 100, "flip_rate": 0.26},
                                    },
                                }
                            }
                        }
                    }
                }
            ],
        }
        rq = build_rq_summary(payload)
        top = rq["rq2_drivers"]["top_dimensions"]
        self.assertGreaterEqual(len(top), 2)
        self.assertEqual(top[0]["dimension"], "shots")
        self.assertGreater(float(top[0]["driver_score"]), float(top[1]["driver_score"]))


if __name__ == "__main__":
    unittest.main()
