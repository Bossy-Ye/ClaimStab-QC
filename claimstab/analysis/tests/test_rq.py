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

    def test_rq5_conditional_robustness_collects_examples(self) -> None:
        payload = {
            "meta": {"task": "maxcut"},
            "comparative": {"space_claim_delta": []},
            "experiments": [
                {
                    "experiment_id": "sampling_only:A>B",
                    "claim": {"type": "ranking"},
                    "overall": {
                        "conditional_robustness": {
                            "robust_core_by_delta": {
                                "0.0": [
                                    {
                                        "conditions": {"shots_bucket": "high"},
                                        "n_eval": 120,
                                        "stability_hat": 1.0,
                                        "stability_ci_low": 0.97,
                                        "stability_ci_high": 1.0,
                                        "decision": "stable",
                                    }
                                ]
                            },
                            "failure_frontier_by_delta": {
                                "0.0": [
                                    {
                                        "changed_dimension": "shots_bucket",
                                        "stable_conditions": {"shots_bucket": "high"},
                                        "unstable_conditions": {"shots_bucket": "low"},
                                        "stable_n_eval": 120,
                                        "unstable_n_eval": 120,
                                    }
                                ]
                            },
                            "minimal_lockdown_set_by_delta": {
                                "0.0": {
                                    "best": {
                                        "lock_dimensions": ["shots_bucket"],
                                        "conditions": {"shots_bucket": "high"},
                                        "n_eval": 120,
                                        "stability_hat": 1.0,
                                        "stability_ci_low": 0.97,
                                        "stability_ci_high": 1.0,
                                        "decision": "stable",
                                    }
                                }
                            },
                        }
                    },
                }
            ],
        }
        rq = build_rq_summary(payload)
        rq5 = rq["rq5_conditional_robustness"]
        self.assertEqual(int(rq5["experiments_with_map"]), 1)
        self.assertGreaterEqual(len(rq5["robust_core_examples"]), 1)
        self.assertGreaterEqual(len(rq5["failure_frontier_examples"]), 1)
        self.assertGreaterEqual(len(rq5["minimal_lockdown_examples"]), 1)


if __name__ == "__main__":
    unittest.main()
