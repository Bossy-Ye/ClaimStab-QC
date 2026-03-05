from __future__ import annotations

import subprocess


def run_subprocess(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    return int(proc.returncode)
