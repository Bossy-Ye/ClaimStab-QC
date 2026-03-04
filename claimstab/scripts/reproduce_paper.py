from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="One-command paper reproduction: runs experiments, reports, and figures."
    )
    ap.add_argument("--out-root", default="output/paper_artifact")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default="basic")
    ap.add_argument("--sample-size-large", type=int, default=64)
    ap.add_argument("--sample-size-structural", type=int, default=48)
    ap.add_argument("--sample-seed", type=int, default=42)
    return ap.parse_args()


def _render_reports(root: Path) -> list[str]:
    generated: list[str] = []
    for claim_json in sorted(root.glob("**/claim_stability.json")):
        report_html = claim_json.parent / "stability_report.html"
        _run(
            [
                sys.executable,
                "-m",
                "claimstab.scripts.generate_stability_report",
                "--json",
                str(claim_json),
                "--out",
                str(report_html),
                "--with-plots",
            ]
        )
        generated.append(str(report_html))
    return generated


def main() -> None:
    args = parse_args()
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    calibration_dir = out_root / "calibration"
    large_dir = out_root / "large"
    structural_dir = out_root / "structural"
    figures_main_dir = out_root / "figures" / "main"
    figures_structural_dir = out_root / "figures" / "structural"

    commands: list[list[str]] = [
        [
            sys.executable,
            "examples/exp_comprehensive_calibration.py",
            "--out-dir",
            str(calibration_dir),
            "--backend-engine",
            args.backend_engine,
            "--no-include-structural",
        ],
        [
            sys.executable,
            "examples/exp_comprehensive_large.py",
            "--out-dir",
            str(large_dir),
            "--sample-size",
            str(args.sample_size_large),
            "--sample-seed",
            str(args.sample_seed),
            "--backend-engine",
            args.backend_engine,
            "--no-include-structural",
        ],
        [
            sys.executable,
            "examples/exp_structural_compilation.py",
            "--out-dir",
            str(structural_dir),
            "--sample-size",
            str(args.sample_size_structural),
            "--sample-seed",
            str(args.sample_seed),
            "--backend-engine",
            args.backend_engine,
        ],
    ]
    for cmd in commands:
        _run(cmd)

    generated_reports = _render_reports(out_root)

    _run(
        [
            sys.executable,
            "-m",
            "claimstab.scripts.make_paper_figures",
            "--input-dir",
            str(large_dir),
            "--also-calibration",
            str(calibration_dir),
            "--output-dir",
            str(figures_main_dir),
            "--threshold",
            "0.95",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "claimstab.scripts.make_paper_figures",
            "--input-dir",
            str(structural_dir),
            "--output-dir",
            str(figures_structural_dir),
            "--threshold",
            "0.95",
        ]
    )

    manifest = {
        "out_root": str(out_root.resolve()),
        "runs": {
            "calibration": str(calibration_dir),
            "large": str(large_dir),
            "structural": str(structural_dir),
        },
        "figures": {
            "main": str(figures_main_dir),
            "structural": str(figures_structural_dir),
        },
        "generated_reports": generated_reports,
        "commands": [" ".join(cmd) for cmd in commands],
    }
    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
