from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from claimstab import cli


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


if __name__ == "__main__":
    unittest.main()
