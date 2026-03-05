from __future__ import annotations

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Main-paper calibration track: exhaustive comparative claim evaluation on standard suite."
    )
    ap.add_argument("--out-dir", default="output/exp_comprehensive_calibration")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default="basic")
    ap.add_argument(
        "--include-structural",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also run GHZ structural compilation benchmark.",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    base_cmd = [
        sys.executable,
        "-m",
        "claimstab.pipelines.claim_stability_app",
        "--suite",
        "standard",
        "--space-presets",
        "compilation_only,sampling_only,combined_light",
        "--claim-pairs",
        "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline",
        "--sampling-mode",
        "full_factorial",
        "--deltas",
        "0.0,0.01,0.05",
        "--stability-threshold",
        "0.95",
        "--confidence-level",
        "0.95",
        "--backend-engine",
        args.backend_engine,
    ]
    maxcut_cmd = [*base_cmd, "--task", "maxcut", "--out-dir", f"{args.out_dir}/maxcut_ranking"]
    bv_cmd = [
        *base_cmd,
        "--task",
        "bv",
        "--claim-pairs",
        "",
        "--out-dir",
        f"{args.out_dir}/bv_decision",
    ]
    print("Running:", " ".join(maxcut_cmd))
    subprocess.run(maxcut_cmd, check=True)
    print("Running:", " ".join(bv_cmd))
    subprocess.run(bv_cmd, check=True)
    if args.include_structural:
        ghz_cmd = [
            sys.executable,
            "examples/exp_structural_compilation.py",
            "--out-dir",
            f"{args.out_dir}/ghz_structural",
            "--backend-engine",
            args.backend_engine,
        ]
        print("Running:", " ".join(ghz_cmd))
        subprocess.run(ghz_cmd, check=True)


if __name__ == "__main__":
    main()
