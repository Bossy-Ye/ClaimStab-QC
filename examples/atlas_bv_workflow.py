from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run a non-MaxCut BV claim-stability demo and publish it to ClaimAtlas."
    )
    ap.add_argument("--spec", default="specs/atlas_bv_demo.yml", help="Path to BV demo spec.")
    ap.add_argument("--run-dir", default="output/atlas_bv_demo", help="Directory for experiment outputs.")
    ap.add_argument("--atlas-root", default="atlas", help="ClaimAtlas root directory.")
    ap.add_argument("--contributor", default="demo_user", help="Contributor id for atlas metadata.")
    ap.add_argument(
        "--submission-id",
        default=None,
        help="Optional stable submission id. If omitted, a timestamp id is generated.",
    )
    ap.add_argument("--skip-run", action="store_true", help="Skip experiment run and publish existing run-dir only.")
    return ap.parse_args()


def _run_command(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    atlas_root = Path(args.atlas_root)
    submission_id = args.submission_id
    if not submission_id:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        submission_id = f"bv_demo_{stamp}"

    if not args.skip_run:
        run_cmd = [
            sys.executable,
            "-m",
            "claimstab.cli",
            "run",
            "--spec",
            str(args.spec),
            "--out-dir",
            str(run_dir),
            "--report",
        ]
        _run_command(run_cmd)

    publish_cmd = [
        sys.executable,
        "-m",
        "claimstab.cli",
        "publish-result",
        "--run-dir",
        str(run_dir),
        "--atlas-root",
        str(atlas_root),
        "--contributor",
        str(args.contributor),
        "--submission-id",
        str(submission_id),
        "--title",
        "BV Atlas Demo",
    ]
    _run_command(publish_cmd)

    validate_cmd = [
        sys.executable,
        "-m",
        "claimstab.cli",
        "validate-atlas",
        "--atlas-root",
        str(atlas_root),
    ]
    _run_command(validate_cmd)

    print()
    print("Done.")
    print(f"Run artifacts: {run_dir.resolve()}")
    print(f"Published submission: {(atlas_root / 'submissions' / submission_id).resolve()}")
    print(f"Atlas index: {(atlas_root / 'index.json').resolve()}")


if __name__ == "__main__":
    main()
