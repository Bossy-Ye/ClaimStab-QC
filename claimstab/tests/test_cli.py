from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claimstab import cli


class TestCLI(unittest.TestCase):
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

    def test_export_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "definitions.md"
            rc = cli.main(["export-definitions", "--out", str(out_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())

    def test_validate_ecosystem(self) -> None:
        rc = cli.main(["validate-ecosystem", "--root", "ecosystem"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
