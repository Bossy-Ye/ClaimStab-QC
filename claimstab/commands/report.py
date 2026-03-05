from __future__ import annotations

import argparse
import sys

from ._utils import run_subprocess


def cmd_report(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        "-m",
        "claimstab.scripts.generate_stability_report",
        "--json",
        args.json,
        "--out",
        args.out,
    ]
    if args.with_plots:
        cmd.append("--with-plots")
    return run_subprocess(cmd)
