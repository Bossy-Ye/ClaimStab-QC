from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def cmd_examples(_: argparse.Namespace) -> int:
    print("Ready-to-run examples:")
    print("  python examples/community/claim_stability_demo.py --suite core --sampling-mode random_k --sample-size 8 --sample-seed 1")
    print("  claimstab run --spec examples/community/custom_task_demo/spec_toy.yml --out-dir output/examples/toy_task_demo --report")
    print("  claimstab run --spec examples/community/qec_pilot_demo/spec_qec_decoder.yml --out-dir output/examples/qec_pilot_demo --report")
    print("  claimstab run --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main --report")
    print("  claimstab validate-spec --spec examples/community/custom_task_demo/spec_toy.yml")
    print("  claimstab validate-evidence --json output/examples/toy_task_demo/claim_stability.json")
    print("  claimstab export-definitions --out docs/generated/definitions.md")
    print("  claimstab publish-result --run-dir output/examples/toy_task_demo --atlas-root atlas --contributor your_name")
    print("  claimstab validate-atlas --atlas-root atlas")
    print("  claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md")
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
