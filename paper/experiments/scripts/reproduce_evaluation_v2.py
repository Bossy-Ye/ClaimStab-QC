from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _mkdirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _experiment_specs(root: Path, *, include_experimental_s1: bool) -> list[dict[str, Any]]:
    runs_root = root / "runs"
    specs_root = Path("paper/experiments/specs/evaluation_v2")
    items: list[dict[str, Any]] = [
        {
            "id": "E1",
            "name": "E1_maxcut_main",
            "role": "RQ1 main empirical battleground; RQ2 heterogeneity source",
            "status": "runnable",
            "spec": specs_root / "e1_maxcut_main.yml",
            "out_dir": runs_root / "E1_maxcut_main",
            "cmd": [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(specs_root / "e1_maxcut_main.yml"),
                "--out-dir",
                str(runs_root / "E1_maxcut_main"),
                "--report",
            ],
        },
        {
            "id": "E2",
            "name": "E2_ghz_structural",
            "role": "RQ2 stable-control calibration for ranking claims",
            "status": "runnable",
            "spec": specs_root / "e2_ghz_structural.yml",
            "out_dir": runs_root / "E2_ghz_structural",
            "cmd": [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(specs_root / "e2_ghz_structural.yml"),
                "--out-dir",
                str(runs_root / "E2_ghz_structural"),
                "--report",
            ],
        },
        {
            "id": "E3",
            "name": "E3_bv_decision",
            "role": "RQ2 stable-control calibration for decision claims",
            "status": "runnable",
            "spec": specs_root / "e3_bv_decision.yml",
            "out_dir": runs_root / "E3_bv_decision",
            "cmd": [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(specs_root / "e3_bv_decision.yml"),
                "--out-dir",
                str(runs_root / "E3_bv_decision"),
                "--report",
            ],
        },
        {
            "id": "E4",
            "name": "E4_grover_distribution",
            "role": "RQ2/RQ3 fragile distribution calibration",
            "status": "runnable",
            "spec": specs_root / "e4_grover_distribution.yml",
            "out_dir": runs_root / "E4_grover_distribution",
            "cmd": [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(specs_root / "e4_grover_distribution.yml"),
                "--out-dir",
                str(runs_root / "E4_grover_distribution"),
                "--report",
            ],
        },
        {
            "id": "S2",
            "name": "S2_boundary",
            "role": "RQ2/RQ3 boundary-sensitive challenge",
            "status": "runnable",
            "spec": specs_root / "s2_boundary.yml",
            "out_dir": runs_root / "S2_boundary",
            "cmd": [
                sys.executable,
                "paper/experiments/scripts/exp_boundary_challenge.py",
                "--spec",
                str(specs_root / "s2_boundary.yml"),
                "--out",
                str(runs_root / "S2_boundary"),
            ],
        },
        {
            "id": "QEC",
            "name": "QEC_portability",
            "role": "RQ2 supporting portability illustration only",
            "status": "runnable",
            "spec": specs_root / "qec_portability.yml",
            "out_dir": runs_root / "QEC_portability",
            "cmd": [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(specs_root / "qec_portability.yml"),
                "--out-dir",
                str(runs_root / "QEC_portability"),
                "--report",
            ],
        },
        {
            "id": "E5",
            "name": "E5_policy_comparison",
            "role": "RQ4 multi-claim policy comparison over 15 post hoc selected claims",
            "status": "pending_design_alignment",
            "notes": [
                "Current repository only materializes a one-claim adaptive study.",
                "The 15-claim stratified selection logic must be finalized before rerun.",
            ],
            "out_dir": runs_root / "E5_policy_comparison",
        },
        {
            "id": "S1",
            "name": "S1_multidevice_portability",
            "role": "RQ4 backend-conditioned portability",
            "status": "experimental" if include_experimental_s1 else "pending_pipeline_alignment",
            "spec": specs_root / "s1_multidevice_portability.yml",
            "notes": [
                "Current multidevice pipeline is still oriented around structural transpile metrics.",
                "This spec is staged for alignment work; do not cite as final evidence until rerun is reviewed.",
            ],
            "out_dir": runs_root / "S1_multidevice_portability",
            "cmd": [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(specs_root / "s1_multidevice_portability.yml"),
                "--out-dir",
                str(runs_root / "S1_multidevice_portability"),
            ],
        },
    ]
    return items


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _directory_layout(root: Path) -> dict[str, str]:
    derived_root = root / "derived_paper_evaluation"
    return {
        "runs": str((root / "runs").resolve()),
        "derived_root": str(derived_root.resolve()),
        "derived_rq1": str((derived_root / "RQ1_necessity").resolve()),
        "derived_rq2": str((derived_root / "RQ2_semantics").resolve()),
        "derived_rq3": str((derived_root / "RQ3_diagnostics").resolve()),
        "derived_rq4": str((derived_root / "RQ4_practicality").resolve()),
        "pack_tables": str((root / "pack" / "tables").resolve()),
        "pack_figures": str((root / "pack" / "figures").resolve()),
        "manifests": str((root / "manifests").resolve()),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Set up and optionally execute the evaluation_v2 experiment layout."
    )
    ap.add_argument("--out-root", default="output/paper/evaluation_v2")
    ap.add_argument("--layout-only", action="store_true", help="Create the evaluation_v2 directory layout and manifests only.")
    ap.add_argument(
        "--include-experimental-s1",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Also run the staged multidevice spec even though pipeline alignment is still under review.",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.out_root)
    layout = _directory_layout(root)
    _mkdirs([Path(path) for path in layout.values()])

    specs = _experiment_specs(root, include_experimental_s1=bool(args.include_experimental_s1))

    plan_manifest = {
        "schema_version": "evaluation_v2_plan_v1",
        "out_root": str(root.resolve()),
        "layout": layout,
        "experiments": [
            {
                "id": item["id"],
                "name": item["name"],
                "role": item["role"],
                "status": item["status"],
                "spec": str(Path(item["spec"]).resolve()) if item.get("spec") else None,
                "out_dir": str(Path(item["out_dir"]).resolve()),
                "cmd": " ".join(item["cmd"]) if item.get("cmd") else None,
                "notes": item.get("notes", []),
            }
            for item in specs
        ],
    }
    _write_json(root / "manifests" / "evaluation_plan.json", plan_manifest)

    if args.layout_only:
        status_manifest = {
            "schema_version": "evaluation_v2_status_v1",
            "layout_only": True,
            "completed": [],
            "pending": [item["id"] for item in specs],
        }
        _write_json(root / "manifests" / "evaluation_status.json", status_manifest)
        print(f"Prepared evaluation_v2 layout under: {root.resolve()}")
        print(f"Wrote manifest: {(root / 'manifests' / 'evaluation_plan.json').resolve()}")
        return

    completed: list[str] = []
    pending: list[dict[str, Any]] = []
    for item in specs:
        status = str(item.get("status"))
        if status not in {"runnable", "experimental"}:
            pending.append(
                {
                    "id": item["id"],
                    "status": status,
                    "notes": item.get("notes", []),
                }
            )
            continue
        cmd = item.get("cmd")
        if not isinstance(cmd, list):
            continue
        _run(cmd)
        completed.append(str(item["id"]))

    status_manifest = {
        "schema_version": "evaluation_v2_status_v1",
        "layout_only": False,
        "completed": completed,
        "pending": pending,
    }
    _write_json(root / "manifests" / "evaluation_status.json", status_manifest)
    print(f"Prepared evaluation_v2 layout under: {root.resolve()}")
    print(f"Wrote manifests under: {(root / 'manifests').resolve()}")


if __name__ == "__main__":
    main()
