from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run Grover distribution-claim demo and render HTML report.")
    ap.add_argument("--spec", default="examples/community/specs/grover_dist_spec.yaml")
    ap.add_argument("--out-dir", default="output/examples/grover_distribution_demo")
    ap.add_argument("--validate", action="store_true", help="Validate spec against schema before run.")
    ap.add_argument("--dry-run", action="store_true", help="Print command without executing.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    cmd = [
        sys.executable,
        "-m",
        "claimstab.cli",
        "run",
        "--spec",
        str(args.spec),
        "--out-dir",
        str(out_dir),
        "--report",
        "--with-plots",
    ]
    if args.validate:
        cmd.append("--validate")

    print("Running:", " ".join(cmd))
    if args.dry_run:
        return

    subprocess.run(cmd, check=True)

    json_path = out_dir / "claim_stability.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Expected output not found: {json_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    decisions = sorted({str(row.get("decision")) for row in rows if isinstance(row, dict)})

    print("Wrote:")
    print(" ", json_path.resolve())
    print(" ", (out_dir / "stability_report.html").resolve())
    print("Decisions:", decisions)


if __name__ == "__main__":
    main()
