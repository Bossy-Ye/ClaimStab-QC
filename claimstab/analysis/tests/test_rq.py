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

    def test_rq6_stratified_stability_collects_and_ranks_examples(self) -> None:
        payload = {
            "meta": {"task": "maxcut"},
            "comparative": {"space_claim_delta": []},
            "experiments": [
                {
                    "experiment_id": "combined_light:A>B",
                    "claim": {"type": "ranking"},
                    "overall": {
                        "stratified_stability": {
                            "strata_dimensions": ["instance_family", "graph_size_bucket"],
                            "by_delta": {
                                "0.0": [
                                    {
                                        "conditions": {"instance_family": "ring", "graph_size_bucket": "small"},
                                        "n_instances": 8,
                                        "n_eval": 160,
                                        "flip_rate": 0.01,
                                        "stability_hat": 0.99,
                                        "stability_ci_low": 0.96,
                                        "stability_ci_high": 1.0,
                                        "decision": "stable",
                                    },
                                    {
                                        "conditions": {"instance_family": "erdos_renyi", "graph_size_bucket": "large"},
                                        "n_instances": 8,
                                        "n_eval": 160,
                                        "flip_rate": 0.62,
                                        "stability_hat": 0.38,
                                        "stability_ci_low": 0.30,
                                        "stability_ci_high": 0.46,
                                        "decision": "unstable",
                                    },
                                ]
                            },
                        }
                    },
                }
            ],
        }

        rq = build_rq_summary(payload)
        rq6 = rq["rq6_stratified_stability"]
        self.assertEqual(int(rq6["experiments_with_strata"]), 1)
        self.assertIn("instance_family", rq6["strata_dimensions"])
        self.assertEqual(int(rq6["decision_counts"]["stable"]), 1)
        self.assertEqual(int(rq6["decision_counts"]["unstable"]), 1)
        self.assertGreaterEqual(len(rq6["unstable_examples"]), 1)
        self.assertEqual(rq6["unstable_examples"][0]["conditions"]["instance_family"], "erdos_renyi")

    def test_rq7_effect_diagnostics_collects_main_and_interactions(self) -> None:
        payload = {
            "meta": {"task": "maxcut"},
            "comparative": {"space_claim_delta": []},
            "experiments": [
                {
                    "experiment_id": "sampling_only:A>B",
                    "claim": {"type": "ranking"},
                    "overall": {
                        "effect_diagnostics": {
                            "dimensions": ["shots_bucket", "seed_simulator", "layout_method"],
                            "context_conditions": {"space_preset": "sampling_only"},
                            "by_delta": {
                                "0.0": {
                                    "main_effects": [
                                        {
                                            "dimension": "shots_bucket",
                                            "effect_score": 0.80,
                                            "n_levels": 2,
                                            "n_eval": 200,
                                            "by_value": [
                                                {"value": "low", "n_eval": 100, "flip_rate": 0.9},
                                                {"value": "high", "n_eval": 100, "flip_rate": 0.1},
                                            ],
                                        },
                                        {
                                            "dimension": "seed_simulator",
                                            "effect_score": 0.05,
                                            "n_levels": 2,
                                            "n_eval": 200,
                                            "by_value": [
                                                {"value": 0, "n_eval": 100, "flip_rate": 0.55},
                                                {"value": 1, "n_eval": 100, "flip_rate": 0.50},
                                            ],
                                        },
                                    ],
                                    "interaction_effects": [
                                        {
                                            "dimensions": ["shots_bucket", "layout_method"],
                                            "interaction_score": 0.35,
                                            "joint_spread": 0.95,
                                            "reference_main_effect": 0.60,
                                            "n_cells": 4,
                                            "n_eval": 200,
                                        }
                                    ],
                                }
                            },
                        }
                    },
                }
            ],
        }

        rq = build_rq_summary(payload)
        rq7 = rq["rq7_effect_diagnostics"]
        self.assertEqual(int(rq7["experiments_with_effect_diagnostics"]), 1)
        self.assertIn("shots_bucket", rq7["dimensions"])
        self.assertGreaterEqual(len(rq7["top_main_effects"]), 1)
        self.assertEqual(rq7["top_main_effects"][0]["dimension"], "shots_bucket")
        self.assertGreaterEqual(len(rq7["top_interactions"]), 1)
        self.assertEqual(rq7["top_interactions"][0]["dimensions"], ["shots_bucket", "layout_method"])

    def test_naive_comparison_tracks_legacy_and_realistic(self) -> None:
        payload = {
            "meta": {"task": "maxcut"},
            "experiments": [],
            "comparative": {
                "space_claim_delta": [
                    {
                        "space_preset": "sampling_only",
                        "claim_type": "ranking",
                        "claim_pair": "A>B",
                        "metric_name": "objective",
                        "delta": 0.0,
                        "decision": "inconclusive",
                        "naive_baseline": {"comparison": "naive_overclaim", "naive_policy": "legacy_strict_all"},
                        "naive_baseline_realistic": {
                            "comparison": "agree",
                            "naive_policy": "default_researcher_v1",
                        },
                    },
                    {
                        "space_preset": "sampling_only",
                        "claim_type": "ranking",
                        "claim_pair": "C>D",
                        "metric_name": "objective",
                        "delta": 0.01,
                        "decision": "stable",
                        "naive_baseline": {"comparison": "agree", "naive_policy": "legacy_strict_all"},
                        "naive_baseline_realistic": {
                            "comparison": "naive_underclaim",
                            "naive_policy": "default_researcher_v1",
                        },
                    },
                ]
            },
        }
        rq = build_rq_summary(payload)
        legacy = rq["naive_baseline_comparison"]
        realistic = rq["naive_baseline_realistic_comparison"]
        self.assertEqual(legacy["policy"], "legacy_strict_all")
        self.assertEqual(realistic["policy"], "default_researcher_v1")
        self.assertEqual(int(legacy["counts"]["naive_overclaim"]), 1)
        self.assertEqual(int(legacy["counts"]["agree"]), 1)
        self.assertEqual(int(realistic["counts"]["agree"]), 1)
        self.assertEqual(int(realistic["counts"]["naive_underclaim"]), 1)


if __name__ == "__main__":
    unittest.main()
