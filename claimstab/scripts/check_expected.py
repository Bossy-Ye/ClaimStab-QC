from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_JSON_KEYS = {"meta", "batch", "experiments", "comparative"}
REQUIRED_DECISIONS = {"stable", "unstable", "inconclusive"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run a tiny ClaimStab check and verify structural output invariants.")
    ap.add_argument("--out-dir", default="output/expected_check")
    ap.add_argument("--keep", action="store_true", help="Keep output directory after checks")
    return ap.parse_args()


def run_tiny_experiment(out_dir: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "claimstab.pipelines.claim_stability_app",
        "--suite",
        "standard",
        "--space-preset",
        "baseline",
        "--sampling-mode",
        "random_k",
        "--sample-size",
        "4",
        "--sample-seed",
        "1",
        "--deltas",
        "0.0,0.01",
        "--claim-pairs",
        "QAOA_p2>RandomBaseline",
        "--out-dir",
        str(out_dir),
    ]
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError("Tiny experiment failed.")


def check_outputs(out_dir: Path) -> None:
    json_path = out_dir / "claim_stability.json"
    csv_path = out_dir / "scores.csv"

    if not json_path.exists():
        raise RuntimeError(f"Missing output JSON: {json_path}")
    if not csv_path.exists():
        raise RuntimeError(f"Missing output CSV: {csv_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    missing = REQUIRED_JSON_KEYS - set(payload.keys())
    if missing:
        raise RuntimeError(f"JSON missing required top-level keys: {sorted(missing)}")

    experiments = payload.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        raise RuntimeError("Expected non-empty experiments list.")

    overall = experiments[0].get("overall", {})
    delta_sweep = overall.get("delta_sweep", []) if isinstance(overall, dict) else []
    if not isinstance(delta_sweep, list) or not delta_sweep:
        raise RuntimeError("Expected non-empty overall.delta_sweep.")

    for row in delta_sweep:
        decision = row.get("decision")
        if decision not in REQUIRED_DECISIONS:
            raise RuntimeError(f"Unexpected decision label: {decision}")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_tiny_experiment(out_dir)
        check_outputs(out_dir)
        print("Expected-output check passed.")
    finally:
        if not args.keep:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
