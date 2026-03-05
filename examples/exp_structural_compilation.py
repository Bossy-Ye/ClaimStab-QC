from __future__ import annotations

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Structural compilation benchmark: GHZ linear vs star under perturbations."
    )
    ap.add_argument("--out-dir", default="output/exp_structural_compilation")
    ap.add_argument("--sample-size", type=int, default=48)
    ap.add_argument("--sample-seed", type=int, default=17)
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default="basic")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cmd = [
        sys.executable,
        "-m",
        "claimstab.pipelines.claim_stability_app",
        "--suite",
        "standard",
        "--task",
        "ghz",
        "--spec",
        "specs/paper_structural.yml",
        "--space-presets",
        "compilation_only,combined_light",
        "--sampling-mode",
        "random_k",
        "--sample-size",
        str(args.sample_size),
        "--sample-seed",
        str(args.sample_seed),
        "--stability-threshold",
        "0.95",
        "--confidence-level",
        "0.95",
        "--backend-engine",
        args.backend_engine,
        "--out-dir",
        args.out_dir,
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
