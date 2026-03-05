from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def cmd_examples(_: argparse.Namespace) -> int:
    print("Ready-to-run examples:")
    print("  claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo")
    print("  claimstab run --spec specs/paper_main.yml --out-dir output/paper_main --report")
    print("  claimstab run --spec specs/paper_structural.yml --out-dir output/paper_structural --report")
    print("  claimstab run --spec specs/paper_device.yml --out-dir output/paper_device")
    print("  claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy")
    print("  claimstab run --spec specs/atlas_bv_demo.yml --out-dir output/atlas_bv_demo --report")
    print("  PYTHONPATH=. ./venv/bin/python examples/atlas_bv_workflow.py --contributor your_name")
    print("  claimstab report --json output/paper_main/claim_stability.json --out output/paper_main/stability_report.html")
    print("  claimstab validate-spec --spec specs/paper_main.yml")
    print("  claimstab validate-evidence --json output/paper_main/claim_stability.json")
    print("  claimstab export-definitions --out docs/generated/definitions.md")
    print("  claimstab publish-result --run-dir output/paper_main --atlas-root atlas --contributor your_name")
    print("  claimstab validate-atlas --atlas-root atlas")
    print("  claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md")
    print("  make reproduce-paper")
    return 0


def cmd_export_definitions(args: argparse.Namespace) -> int:
    src = Path("docs/concepts/formal_definitions.md")
    out = Path(args.out)
    if not src.exists():
        print(f"Definitions template not found: {src}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    print(f"Exported definitions to: {out}")
    return 0
