from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestReportSections(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "meta": {
                "reproduce_command": "demo",
                "artifacts": {
                    "trace_jsonl": "/tmp/trace.jsonl",
                    "events_jsonl": None,
                    "cache_db": None,
                    "replay_trace": None,
                },
                "evidence_chain": {
                    "protocol": "cep_v1",
                    "schema_id": "claimstab/evidence/schema_cep_v1.json",
                    "trace_source": "trace_jsonl",
                    "lookup_fields": ["suite"],
                    "decision_provenance": "test",
                    "required_evidence_fields": ["config_fingerprint"],
                },
            },
            "experiments": [
                {
                    "experiment_id": "exp:1",
                    "claim": {"type": "ranking", "method_a": "A", "method_b": "B", "deltas": [0.0]},
                    "sampling": {"mode": "random_k", "sample_size": 4, "seed": 1},
                    "stability_rule": {"threshold": 0.95, "confidence_level": 0.95},
                    "backend": {"engine": "basic"},
                    "per_graph": {},
                    "overall": {
                        "delta_sweep": [
                            {
                                "delta": 0.0,
                                "flip_rate_mean": 0.1,
                                "flip_rate_max": 0.1,
                                "flip_rate_min": 0.1,
                                "holds_rate_mean": 0.9,
                                "holds_rate_ci_low": 0.8,
                                "holds_rate_ci_high": 0.95,
                                "stability_hat": 0.9,
                                "stability_ci_low": 0.8,
                                "stability_ci_high": 0.95,
                                "decision": "inconclusive",
                                "clustered_stability_mean": 0.9,
                                "clustered_stability_ci_low": 0.75,
                                "clustered_stability_ci_high": 0.98,
                                "clustered_decision": "inconclusive",
                                "n_instances": 1,
                                "n_claim_evals": 10,
                                "decision_counts": {"stable": 0, "unstable": 0, "inconclusive": 1},
                            }
                        ],
                        "diagnostics": {
                            "by_delta_dimension": {},
                            "top_unstable_configs_by_delta": {},
                            "top_lockdown_recommendations_by_delta": {},
                        },
                        "stability_vs_cost": {
                            "by_delta": {
                                "0.0": [
                                    {
                                        "shots": 256,
                                        "n_eval": 10,
                                        "flip_rate": 0.1,
                                        "stability_hat": 0.9,
                                        "stability_ci_low": 0.8,
                                        "stability_ci_high": 0.95,
                                        "ci_width": 0.15,
                                        "decision": "inconclusive",
                                    }
                                ]
                            },
                            "minimum_shots_for_stable": {"0.0": None},
                        },
                    },
                    "auxiliary_claims": {},
                    "evidence": {
                        "trace_query": {
                            "suite": "core",
                            "space_preset": "sampling_only",
                            "metric_name": "objective",
                            "methods": ["A", "B"],
                        },
                        "artifacts": {"trace_jsonl": "/tmp/trace.jsonl"},
                        "lookup_fields": ["suite"],
                        "cep": {"config_fingerprint": {"hash": "abcdef1234567890"}},
                    },
                }
            ],
            "comparative": {
                "space_claim_delta": [
                    {
                        "space_preset": "sampling_only",
                        "claim_pair": "A>B",
                        "delta": 0.0,
                        "flip_rate_mean": 0.1,
                        "holds_rate_mean": 0.9,
                        "holds_rate_ci_low": 0.8,
                        "holds_rate_ci_high": 0.95,
                        "stability_hat": 0.9,
                        "stability_ci_low": 0.8,
                        "stability_ci_high": 0.95,
                        "decision": "inconclusive",
                        "clustered_stability_mean": 0.9,
                        "clustered_stability_ci_low": 0.75,
                        "clustered_stability_ci_high": 0.98,
                        "clustered_decision": "inconclusive",
                        "decision_counts": {"stable": 0, "unstable": 0, "inconclusive": 1},
                        "naive_baseline": {"comparison": "agree"},
                    }
                ]
            },
            "rq_summary": {
                "rq1_prevalence": {"by_space_and_claim_type": {}},
                "rq2_drivers": {"top_dimensions": []},
                "rq3_cost_tradeoff": {"stability_vs_cost_rows": []},
                "rq4_adaptive_sampling": {"adaptive_sampling": []},
                "rq5_conditional_robustness": {
                    "experiments_with_map": 1,
                    "minimal_lockdown_examples": [{}],
                },
                "rq6_stratified_stability": {
                    "experiments_with_strata": 1,
                    "decision_counts": {"stable": 1, "unstable": 0, "inconclusive": 0},
                },
                "rq7_effect_diagnostics": {
                    "experiments_with_effect_diagnostics": 1,
                    "top_interactions": [{}],
                },
            },
        }

    def _run_report(self, payload: dict, extra_args: list[str] | None = None) -> str:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            json_path = td_path / "claim_stability.json"
            out_path = td_path / "report.html"
            json_path.write_text(json.dumps(payload), encoding="utf-8")
            cmd = [
                sys.executable,
                "-m",
                "claimstab.scripts.generate_stability_report",
                "--json",
                str(json_path),
                "--out",
                str(out_path),
            ]
            if extra_args:
                cmd.extend(extra_args)
            subprocess.run(cmd, check=True)
            return out_path.read_text(encoding="utf-8")

    def test_default_includes_naive_and_delta_sections(self) -> None:
        html = self._run_report(self._payload())
        self.assertIn("Naive Baseline vs ClaimStab", html)
        self.assertIn("Delta Sweep Summary", html)
        self.assertIn("Stability vs Cost (Shots)", html)
        self.assertIn("RQ6 stratified runs", html)
        self.assertIn("RQ7 effect diagnostics", html)
        self.assertIn("Conditional Robustness Map (RQ5-RQ7)", html)
        self.assertIn("CEP protocol", html)

    def test_custom_sections_can_hide_naive(self) -> None:
        html = self._run_report(
            self._payload(),
            extra_args=["--sections", "summary,claim_table,experiment_summary,delta_sweep,cost_curve,diagnostics,auxiliary_claims"],
        )
        self.assertNotIn("Naive Baseline vs ClaimStab", html)
        self.assertIn("Delta Sweep Summary", html)
        self.assertNotIn("Conditional Robustness Map (RQ5-RQ7)", html)


if __name__ == "__main__":
    unittest.main()
