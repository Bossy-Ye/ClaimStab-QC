from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Set up and execute evaluation_v3 additions (W3 + W5).")
    ap.add_argument("--out-root", default="output/paper/evaluation_v3")
    ap.add_argument("--source-root", default="output/paper/evaluation_v2")
    ap.add_argument("--layout-only", action="store_true")
    ap.add_argument("--skip-w5-run", action="store_true")
    ap.add_argument("--skip-derivations", action="store_true")
    ap.add_argument("--skip-rq4-derivations", action="store_true")
    ap.add_argument("--skip-figures", action="store_true")
    return ap.parse_args()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_readme(root: Path) -> None:
    content = """# evaluation_v3

This directory contains the post-evaluation additions for:

- W3: stronger metric-centric baselines
- W5: near-boundary policy comparison

## Layout

- `runs/W5_near_boundary_policy/`: new near-boundary RQ4 run pack
- `derived_paper_evaluation/RQ1_necessity/`: W3 metric-baseline derivations
- `derived_paper_evaluation/RQ4_practicality/`: W5 derived summaries
- `pack/figures/main/`: evaluation_v3 figures
- `manifests/`: run status and output pointers
"""
    (root / "README.md").write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = Path(args.out_root)
    for path in [
        root / "runs",
        root / "runs" / "W5_near_boundary_policy",
        root / "derived_paper_evaluation" / "RQ1_necessity",
        root / "derived_paper_evaluation" / "RQ4_practicality",
        root / "pack" / "figures" / "main",
        root / "pack" / "tables",
        root / "manifests",
    ]:
        _mkdir(path)
    _write_readme(root)

    plan = {
        "schema_version": "evaluation_v3_plan_v1",
        "out_root": str(root.resolve()),
        "source_root": str(Path(args.source_root).resolve()),
        "components": ["W3_option1", "W3_option2", "W5_near_boundary"],
    }
    _write_json(root / "manifests" / "evaluation_plan.json", plan)

    if not args.layout_only and not args.skip_derivations:
        _run(
            [
                sys.executable,
                "paper/experiments/scripts/derive_rq1_metric_baselines_v3.py",
                "--source-root",
                str(args.source_root),
                "--out-root",
                str(root),
            ]
        )

    if not args.layout_only and not args.skip_w5_run:
        _run(
            [
                sys.executable,
                "paper/experiments/scripts/exp_rq4_near_boundary_v3.py",
                "--out",
                str(root / "runs" / "W5_near_boundary_policy"),
            ]
        )

    if not args.layout_only and not args.skip_rq4_derivations:
        _run(
            [
                sys.executable,
                "paper/experiments/scripts/derive_rq4_near_boundary_v3.py",
                "--root",
                str(root),
                "--source-e5",
                str(Path(args.source_root) / "runs" / "E5_policy_comparison" / "rq4_policy_summary.json"),
            ]
        )

    if not args.layout_only and not args.skip_figures:
        _run(
            [
                sys.executable,
                "paper/experiments/scripts/generate_eval_v3_figures.py",
                "--root",
                str(root),
                "--source-e5-summary",
                str(Path(args.source_root) / "runs" / "E5_policy_comparison" / "rq4_policy_summary.json"),
            ]
        )

    status = {
        "schema_version": "evaluation_v3_status_v1",
        "out_root": str(root.resolve()),
        "w3_outputs_ready": (root / "derived_paper_evaluation" / "RQ1_necessity" / "manifest_rq1_metric_baselines.json").exists(),
        "w5_outputs_ready": (root / "runs" / "W5_near_boundary_policy" / "rq4_near_boundary_summary.json").exists(),
        "figures_ready": (root / "pack" / "figures" / "manifest.json").exists(),
    }
    _write_json(root / "manifests" / "evaluation_status.json", status)
    print("Prepared evaluation_v3 at:", root.resolve())


if __name__ == "__main__":
    main()
