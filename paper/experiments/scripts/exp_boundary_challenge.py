from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _decision_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"stable": 0, "unstable": 0, "inconclusive": 0}
    for row in rows:
        decision = str(row.get("decision", "inconclusive"))
        if decision not in out:
            decision = "inconclusive"
        out[decision] += 1
    return out


def _delta_sort_key(delta: str) -> tuple[int, float | str]:
    try:
        return (0, float(delta))
    except Exception:
        return (1, delta)


def summarize_boundary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows_raw = payload.get("comparative", {}).get("space_claim_delta", [])
    rows = [row for row in rows_raw if isinstance(row, dict)]

    by_space: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_delta: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_space[str(row.get("space_preset", "unknown"))].append(row)
        by_delta[str(row.get("delta", "unknown"))].append(row)

    summary = {
        "schema_version": "boundary_summary_v1",
        "total_rows": len(rows),
        "overall_decisions": _decision_counts(rows),
        "by_space": {},
        "by_delta": {},
        "boundary_signal_detected": any(str(row.get("decision")) != "stable" for row in rows),
    }

    for space_name, group in sorted(by_space.items()):
        summary["by_space"][space_name] = {
            "rows": len(group),
            "decisions": _decision_counts(group),
        }
    for delta, group in sorted(by_delta.items(), key=lambda item: _delta_sort_key(item[0])):
        summary["by_delta"][delta] = {
            "rows": len(group),
            "decisions": _decision_counts(group),
        }

    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run boundary challenge pack and summarize near-threshold outcomes.")
    ap.add_argument("--spec", default="paper/experiments/specs/paper_boundary.yml")
    ap.add_argument("--out", default="output/presentation_large/boundary")
    ap.add_argument("--skip-run", action="store_true", help="Skip execution and summarize existing output only.")
    ap.add_argument(
        "--require-boundary-signal",
        action="store_true",
        help="Return non-zero if no unstable/inconclusive rows are detected.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    out_root = Path(args.out)
    run_dir = out_root / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_run:
        cmd = [
            sys.executable,
            "-m",
            "claimstab.cli",
            "run",
            "--spec",
            str(args.spec),
            "--out-dir",
            str(run_dir),
            "--report",
            "--seed",
            "19",
        ]
        _run(cmd)

    claim_json = run_dir / "claim_stability.json"
    if not claim_json.exists():
        raise FileNotFoundError(f"Expected output not found: {claim_json}")

    payload = _load_json(claim_json)
    summary = summarize_boundary_payload(payload)
    summary["claim_json"] = str(claim_json.resolve())
    summary["spec"] = str(Path(args.spec).resolve())

    summary_path = out_root / "boundary_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote:")
    print(" ", summary_path.resolve())
    print("Boundary signal detected:", summary.get("boundary_signal_detected"))

    if args.require_boundary_signal and not bool(summary.get("boundary_signal_detected")):
        print("Boundary signal was required but not detected.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
