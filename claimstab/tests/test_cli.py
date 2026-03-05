from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import json
from pathlib import Path

from claimstab import cli
from claimstab.evidence import build_cep_protocol_meta, build_experiment_cep_record


class TestCLI(unittest.TestCase):
    def test_init_external_task_starter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "starter"
            rc = cli.main(
                [
                    "init-external-task",
                    "--name",
                    "my_problem",
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "my_problem_task.py").exists())
            spec_path = out_dir / "spec_my_problem.yml"
            self.assertTrue(spec_path.exists())
            content = spec_path.read_text(encoding="utf-8")
            self.assertIn("task:", content)
            self.assertIn("kind: external", content)
            self.assertIn("entrypoint:", content)

    def test_examples_subcommand(self) -> None:
        rc = cli.main(["examples"])
        self.assertEqual(rc, 0)

    def test_validate_spec_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                suite: core
                sampling:
                  mode: full_factorial
                decision_rule:
                  threshold: 0.95
                  confidence_level: 0.95
                """,
                encoding="utf-8",
            )
            rc = cli.main(["validate-spec", "--spec", str(spec_path)])
            self.assertEqual(rc, 0)

    def test_validate_evidence_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            trace_path = td_path / "trace.jsonl"
            trace_row = {
                "suite": "core",
                "space_preset": "sampling_only",
                "instance_id": "g0",
                "method": "A",
                "metric_name": "objective",
                "seed_transpiler": 0,
                "optimization_level": 1,
                "layout_method": "sabre",
                "seed_simulator": 0,
                "shots": 1024,
                "score": 1.0,
                "transpiled_depth": 12,
                "transpiled_size": 18,
            }
            trace_path.write_text(json.dumps(trace_row) + "\n", encoding="utf-8")

            evidence = {
                "trace_query": {
                    "suite": "core",
                    "space_preset": "sampling_only",
                    "metric_name": "objective",
                    "methods": ["A", "B"],
                },
                "artifacts": {"trace_jsonl": str(trace_path), "events_jsonl": None, "cache_db": None},
                "lookup_fields": [
                    "suite",
                    "space_preset",
                    "instance_id",
                    "method",
                    "metric_name",
                    "seed_transpiler",
                    "optimization_level",
                    "layout_method",
                    "shots",
                    "seed_simulator",
                ],
            }
            exp = {
                "experiment_id": "sampling_only:A>B",
                "claim": {"type": "ranking", "method_a": "A", "method_b": "B", "deltas": [0.0]},
                "sampling": {
                    "suite": "core",
                    "space_preset": "sampling_only",
                    "mode": "random_k",
                    "sample_size": 16,
                    "seed": 7,
                    "perturbation_space_size": 100,
                },
                "stability_rule": {"threshold": 0.95, "confidence_level": 0.95},
                "backend": {"engine": "basic", "noise_model": "none"},
                "device_profile": {"enabled": False, "provider": "none", "name": None, "mode": "transpile_only"},
                "baseline": {
                    "seed_transpiler": 0,
                    "optimization_level": 1,
                    "layout_method": "sabre",
                    "shots": 16,
                    "seed_simulator": 0,
                },
                "evidence": evidence,
            }
            evidence["cep"] = build_experiment_cep_record(
                experiment=exp,
                runtime_meta={"git_commit": "abc123", "git_dirty": False, "dependencies": {"qiskit": "2.2.3"}},
                evidence=evidence,
            )

            payload = {
                "meta": {
                    "artifacts": {
                        "trace_jsonl": str(trace_path),
                        "events_jsonl": None,
                        "cache_db": None,
                        "replay_trace": None,
                    },
                    "evidence_chain": build_cep_protocol_meta(
                        lookup_fields=evidence["lookup_fields"],
                        decision_provenance=(
                            "each experiment includes evidence.trace_query + evidence.cep blocks "
                            "that can be matched against trace records for reproducible decision provenance"
                        ),
                    ),
                },
                "experiments": [exp],
            }
            json_path = td_path / "claim_stability.json"
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            rc = cli.main(["validate-evidence", "--json", str(json_path)])
            self.assertEqual(rc, 0)

    def test_run_dry_run_main(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                pipeline: main
                suite: core
                claims:
                  - type: ranking
                    method_a: QAOA_p2
                    method_b: RandomBaseline
                    deltas: [0.0]
                perturbations:
                  preset: baseline
                sampling:
                  mode: random_k
                  sample_size: 4
                  seed: 1
                """,
                encoding="utf-8",
            )
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(Path(td) / "out"),
                    "--dry-run",
                ]
            )
            self.assertEqual(rc, 0)

    def test_run_dry_run_main_with_debug_attribution_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                pipeline: main
                suite: core
                claims:
                  - type: ranking
                    method_a: QAOA_p2
                    method_b: RandomBaseline
                    deltas: [0.0]
                perturbations:
                  preset: baseline
                sampling:
                  mode: random_k
                  sample_size: 4
                  seed: 1
                """,
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli.main(
                    [
                        "run",
                        "--spec",
                        str(spec_path),
                        "--out-dir",
                        str(Path(td) / "out"),
                        "--debug-attribution",
                        "--dry-run",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("--debug-attribution", buf.getvalue())

    def test_run_dry_run_main_with_trace_cache_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                pipeline: main
                suite: core
                claims:
                  - type: ranking
                    method_a: QAOA_p2
                    method_b: RandomBaseline
                    deltas: [0.0]
                perturbations:
                  preset: baseline
                sampling:
                  mode: random_k
                  sample_size: 4
                  seed: 1
                """,
                encoding="utf-8",
            )
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(Path(td) / "out"),
                    "--cache-db",
                    str(Path(td) / "cache.sqlite"),
                    "--trace-out",
                    str(Path(td) / "trace.jsonl"),
                    "--events-out",
                    str(Path(td) / "events.jsonl"),
                    "--replay-trace",
                    str(Path(td) / "trace_existing.jsonl"),
                    "--dry-run",
                ]
            )
            self.assertEqual(rc, 0)

    def test_run_dry_run_external_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                pipeline: main
                task:
                  kind: external
                  entrypoint: examples.custom_task_demo.toy_task:ToyTask
                  suite: toy
                  params:
                    num_qubits: 4
                    num_instances: 2
                methods:
                  - name: HadamardAll
                    kind: hadamard
                  - name: ZeroState
                    kind: zero
                claims:
                  - type: ranking
                    method_a: HadamardAll
                    method_b: ZeroState
                    deltas: [0.0]
                perturbations:
                  preset: sampling_only
                sampling:
                  mode: random_k
                  sample_size: 6
                  seed: 3
                """,
                encoding="utf-8",
            )
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(Path(td) / "out"),
                    "--dry-run",
                    "--validate",
                ]
            )
            self.assertEqual(rc, 0)

    def test_run_dry_run_multidevice_with_trace_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                pipeline: multidevice
                suite: core
                perturbations:
                  transpile_space: baseline
                  noisy_space: sampling_only
                sampling:
                  mode: random_k
                  sample_size: 2
                  seed: 1
                multidevice:
                  run: transpile_only
                  transpile_devices: [FakeManilaV2]
                  transpile_claim_pairs: [QAOA_p1>QAOA_p2]
                """,
                encoding="utf-8",
            )
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(Path(td) / "out"),
                    "--cache-db",
                    str(Path(td) / "cache.sqlite"),
                    "--trace-out",
                    str(Path(td) / "trace.jsonl"),
                    "--events-out",
                    str(Path(td) / "events.jsonl"),
                    "--replay-trace",
                    str(Path(td) / "trace_existing.jsonl"),
                    "--dry-run",
                ]
            )
            self.assertEqual(rc, 0)

    def test_run_dry_run_bv_decision_only_no_ranking_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            spec_path = Path(td) / "spec.yml"
            spec_path.write_text(
                """
                spec_version: 1
                pipeline: main
                task:
                  kind: bv
                  suite: core
                methods:
                  - name: BVOracle
                    kind: bv
                  - name: RandomBaseline
                    kind: random_baseline
                claims:
                  - type: decision
                    method: BVOracle
                    top_k: 1
                    label_meta_key: target_label
                perturbations:
                  preset: sampling_only
                sampling:
                  mode: random_k
                  sample_size: 6
                  seed: 3
                """,
                encoding="utf-8",
            )
            rc = cli.main(
                [
                    "run",
                    "--spec",
                    str(spec_path),
                    "--out-dir",
                    str(Path(td) / "out"),
                    "--dry-run",
                    "--validate",
                ]
            )
            self.assertEqual(rc, 0)

    def test_export_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "definitions.md"
            rc = cli.main(["export-definitions", "--out", str(out_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())

    def test_publish_result_and_validate_atlas(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "claim_stability.json").write_text(
                json.dumps(
                    {
                        "meta": {"task": "toy_task", "suite": "toy_suite"},
                        "experiments": [{"claim": {"type": "ranking"}}],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "scores.csv").write_text("x,y\n1,2\n", encoding="utf-8")
            atlas_root = Path(td) / "atlas"

            rc_publish = cli.main(
                [
                    "publish-result",
                    "--run-dir",
                    str(run_dir),
                    "--atlas-root",
                    str(atlas_root),
                    "--contributor",
                    "tester",
                    "--submission-id",
                    "toy_001",
                ]
            )
            self.assertEqual(rc_publish, 0)

            rc_validate = cli.main(["validate-atlas", "--atlas-root", str(atlas_root)])
            self.assertEqual(rc_validate, 0)

    def test_export_dataset_registry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            atlas_root = Path(td) / "atlas"
            submission = atlas_root / "submissions" / "s1"
            submission.mkdir(parents=True, exist_ok=True)
            (submission / "claim_stability.json").write_text(
                json.dumps(
                    {
                        "meta": {"methods_available": ["M1"]},
                        "experiments": [
                            {
                                "claim": {"type": "decision", "method": "M1", "top_k": 1},
                                "sampling": {"space_preset": "sampling_only", "mode": "random_k", "sample_size": 5, "seed": 0},
                                "baseline": {"seed_transpiler": 0},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (atlas_root / "index.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "submissions": [
                            {
                                "submission_id": "s1",
                                "title": "demo",
                                "contributor": "u",
                                "task": "toy",
                                "suite": "core",
                                "claim_types": ["decision"],
                                "created_at_utc": "2026-03-03T00:00:00+00:00",
                                "artifacts": {"claim_stability.json": "submissions/s1/claim_stability.json"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            out_path = Path(td) / "dataset_registry.md"
            rc = cli.main(
                [
                    "export-dataset-registry",
                    "--atlas-root",
                    str(atlas_root),
                    "--out",
                    str(out_path),
                    "--repo-url",
                    "https://example.com/repo",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())
            self.assertIn("Dataset Registry", out_path.read_text(encoding="utf-8"))

    def test_atlas_compare_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left = root / "left.json"
            right = root / "right.json"
            out = root / "diff.json"
            left.write_text(
                json.dumps(
                    {
                        "meta": {"task": "maxcut", "suite": "core"},
                        "comparative": {
                            "space_claim_delta": [
                                {
                                    "claim_type": "ranking",
                                    "space_preset": "sampling_only",
                                    "claim_pair": "A>B",
                                    "metric_name": "objective",
                                    "delta": 0.0,
                                    "decision": "stable",
                                    "flip_rate_mean": 0.1,
                                    "stability_hat": 0.9,
                                    "naive_baseline": {"comparison": "agree"},
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            right.write_text(
                json.dumps(
                    {
                        "meta": {"task": "maxcut", "suite": "core"},
                        "comparative": {
                            "space_claim_delta": [
                                {
                                    "claim_type": "ranking",
                                    "space_preset": "sampling_only",
                                    "claim_pair": "A>B",
                                    "metric_name": "objective",
                                    "delta": 0.0,
                                    "decision": "unstable",
                                    "flip_rate_mean": 0.2,
                                    "stability_hat": 0.8,
                                    "naive_baseline": {"comparison": "naive_overclaim"},
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            rc = cli.main(
                [
                    "atlas-compare",
                    "--left",
                    str(left),
                    "--right",
                    str(right),
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("paired_rows"), 1)
            self.assertEqual(payload.get("decision_changed_count"), 1)


if __name__ == "__main__":
    unittest.main()
