from __future__ import annotations

import argparse
from typing import Sequence

from claimstab.commands import (
    cmd_atlas_compare,
    cmd_examples,
    cmd_export_dataset_registry,
    cmd_export_definitions,
    cmd_init_external_task,
    cmd_publish_result,
    cmd_report,
    cmd_run,
    cmd_validate_atlas,
    cmd_validate_evidence,
    cmd_validate_spec,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="claimstab", description="ClaimStab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init-external-task", help="Generate a runnable external task plugin starter")
    init_p.add_argument("--name", required=True, help="Task name (used for class/module/spec naming)")
    init_p.add_argument("--out-dir", default=None, help="Output directory (default: examples/<name>_demo)")
    init_p.add_argument("--class-name", default=None, help="Optional explicit class name")
    init_p.add_argument("--force", action="store_true", help="Allow writing into an existing non-empty directory")
    init_p.set_defaults(func=cmd_init_external_task)

    run_p = sub.add_parser("run", help="Run an experiment from a spec file")
    run_p.add_argument("--spec", required=True, help="Path to YAML/JSON experiment spec")
    run_p.add_argument("--out-dir", required=True, help="Output directory")
    run_p.add_argument("--seed", type=int, default=None, help="Override sampling seed")
    run_p.add_argument("--device", default=None, help="Optional single-device override (e.g., FakeManilaV2)")
    run_p.add_argument("--mode", choices=["all", "transpile_only", "noisy_sim"], default=None)
    run_p.add_argument("--report", action="store_true", help="Generate stability_report.html when claim_stability.json exists")
    run_p.add_argument("--with-plots", action="store_true", help="Use --with-plots for report generation")
    run_p.add_argument("--validate", action="store_true", help="Validate spec against v1 schema before running")
    run_p.add_argument("--cache-db", default=None, help="Optional sqlite cache path for matrix cell reuse")
    run_p.add_argument("--events-out", default=None, help="Optional JSONL output path for execution events")
    run_p.add_argument("--trace-out", default=None, help="Optional JSONL output path for trace records")
    run_p.add_argument("--replay-trace", default=None, help="Replay mode: reuse an existing trace JSONL instead of executing")
    run_p.add_argument(
        "--debug-attribution",
        action="store_true",
        help="Print intermediate RQ2 attribution aggregation diagnostics during run.",
    )
    run_p.add_argument("--dry-run", action="store_true", help="Print resolved command without executing")
    run_p.set_defaults(func=cmd_run)

    report_p = sub.add_parser("report", help="Generate an HTML report from JSON output")
    report_p.add_argument("--json", required=True, help="Path to claim_stability.json")
    report_p.add_argument("--out", required=True, help="Output HTML path")
    report_p.add_argument("--with-plots", action="store_true")
    report_p.set_defaults(func=cmd_report)

    validate_p = sub.add_parser("validate-spec", help="Validate a spec file against schema v1")
    validate_p.add_argument("--spec", required=True, help="Path to YAML/JSON spec")
    validate_p.set_defaults(func=cmd_validate_spec)

    validate_evidence_p = sub.add_parser("validate-evidence", help="Validate Claim Evidence Protocol links in output JSON")
    validate_evidence_p.add_argument("--json", required=True, help="Path to claim_stability.json or batch summary JSON")
    validate_evidence_p.add_argument(
        "--base-dir",
        default=None,
        help="Base directory for resolving relative artifact paths (default: JSON parent directory)",
    )
    validate_evidence_p.add_argument(
        "--trace-jsonl",
        default=None,
        help="Optional explicit trace JSONL path override",
    )
    validate_evidence_p.add_argument(
        "--no-trace-check",
        action="store_true",
        help="Skip trace-file loading and query-match checks",
    )
    validate_evidence_p.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings as failure",
    )
    validate_evidence_p.add_argument(
        "--allow-schema-skip",
        action="store_true",
        help="Allow pass when JSON schema validation is unavailable (not recommended).",
    )
    validate_evidence_p.set_defaults(func=cmd_validate_evidence)

    ex_p = sub.add_parser("examples", help="Print ready-to-run example commands")
    ex_p.set_defaults(func=cmd_examples)

    export_p = sub.add_parser("export-definitions", help="Export formal definitions scaffold markdown")
    export_p.add_argument("--out", required=True, help="Output markdown path")
    export_p.set_defaults(func=cmd_export_definitions)

    publish_p = sub.add_parser("publish-result", help="Publish a run directory into the ClaimAtlas dataset")
    publish_p.add_argument("--run-dir", required=True, help="Directory containing claim_stability.json")
    publish_p.add_argument("--atlas-root", default="atlas", help="Atlas dataset root directory")
    publish_p.add_argument("--contributor", default="anonymous", help="Contributor identifier")
    publish_p.add_argument("--title", default=None, help="Optional submission title")
    publish_p.add_argument("--submission-id", default=None, help="Optional stable submission id")
    publish_p.set_defaults(func=cmd_publish_result)

    val_atlas_p = sub.add_parser("validate-atlas", help="Validate ClaimAtlas index and artifact references")
    val_atlas_p.add_argument("--atlas-root", default="atlas", help="Atlas dataset root directory")
    val_atlas_p.set_defaults(func=cmd_validate_atlas)

    exp_data_p = sub.add_parser("export-dataset-registry", help="Generate docs markdown page from atlas submissions")
    exp_data_p.add_argument("--atlas-root", default="atlas", help="Atlas dataset root directory")
    exp_data_p.add_argument("--out", default="docs/dataset_registry.md", help="Output markdown path")
    exp_data_p.add_argument(
        "--repo-url",
        default="https://github.com/Bossy-Ye/ClaimStab-QC",
        help="Repository URL used for artifact links",
    )
    exp_data_p.set_defaults(func=cmd_export_dataset_registry)

    compare_p = sub.add_parser("atlas-compare", help="Compare two claim_stability outputs or run directories")
    compare_p.add_argument("--left", required=True, help="Left run directory or claim_stability.json")
    compare_p.add_argument("--right", required=True, help="Right run directory or claim_stability.json")
    compare_p.add_argument("--out", default=None, help="Optional JSON output path for full diff payload")
    compare_p.set_defaults(func=cmd_atlas_compare)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
