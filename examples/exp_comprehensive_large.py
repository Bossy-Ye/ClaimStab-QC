from __future__ import annotations

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Main-paper large-scale track: random-k comparative claim evaluation on large suite."
    )
    ap.add_argument("--out-dir", default="output/exp_comprehensive_large")
    ap.add_argument("--sample-size", type=int, default=64)
    ap.add_argument("--sample-seed", type=int, default=42)
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
        "examples/claim_stability_demo.py",
        "--suite",
        "large",
        "--space-presets",
        "compilation_only,sampling_only,combined_light",
        "--claim-pairs",
        "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline",
        "--sampling-mode",
        "random_k",
        "--sample-size",
        str(args.sample_size),
        "--sample-seed",
        str(args.sample_seed),
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
            "--sample-size",
            str(max(24, min(args.sample_size, 64))),
            "--sample-seed",
            str(args.sample_seed),
            "--backend-engine",
            args.backend_engine,
        ]
        print("Running:", " ".join(ghz_cmd))
        subprocess.run(ghz_cmd, check=True)


if __name__ == "__main__":
    main()
