from __future__ import annotations

import argparse
import json
import subprocess
import sys
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


def summarize_claim_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    rows = [row for row in rows if isinstance(row, dict)]
    if not rows:
        return {
            "rows": 0,
            "decisions": {"stable": 0, "unstable": 0, "inconclusive": 0},
            "claim_types": [],
            "spaces": [],
        }

    decisions = {"stable": 0, "unstable": 0, "inconclusive": 0}
    claim_types: set[str] = set()
    spaces: set[str] = set()
    for row in rows:
        decision = str(row.get("decision", "inconclusive"))
        if decision not in decisions:
            decision = "inconclusive"
        decisions[decision] += 1
        claim_types.add(str(row.get("claim_type", "unknown")))
        spaces.add(str(row.get("space_preset", "unknown")))

    return {
        "rows": len(rows),
        "decisions": decisions,
        "claim_types": sorted(claim_types),
        "spaces": sorted(spaces),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run a locked ICSE method-set bundle across claim types.")
    ap.add_argument("--out", default="output/presentation_large/icse_methodset")
    ap.add_argument("--skip-run", action="store_true", help="Skip execution and summarize existing outputs only.")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    runs = [
        {
            "track": "ranking_maxcut",
            "spec": "specs/paper_main.yml",
            "out_dir": out_root / "ranking_maxcut",
        },
        {
            "track": "decision_bv",
            "spec": "specs/paper_decision.yml",
            "out_dir": out_root / "decision_bv",
        },
        {
            "track": "distribution_grover",
            "spec": "specs/paper_distribution.yml",
            "out_dir": out_root / "distribution_grover",
        },
        {
            "track": "structural_ghz",
            "spec": "specs/paper_structural.yml",
            "out_dir": out_root / "structural_ghz",
        },
    ]

    if not args.skip_run:
        for row in runs:
            out_dir = Path(str(row["out_dir"]))
            out_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                sys.executable,
                "-m",
                "claimstab.cli",
                "run",
                "--spec",
                str(row["spec"]),
                "--out-dir",
                str(out_dir),
                "--report",
            ]
            _run(cmd)

    summary_rows: list[dict[str, Any]] = []
    for row in runs:
        out_dir = Path(str(row["out_dir"]))
        claim_json = out_dir / "claim_stability.json"
        if not claim_json.exists():
            continue
        payload = _load_json(claim_json)
        track_summary = summarize_claim_payload(payload)
        summary_rows.append(
            {
                "track": str(row["track"]),
                "spec": str(Path(str(row["spec"])).resolve()),
                "claim_json": str(claim_json.resolve()),
                **track_summary,
            }
        )

    bundle = {
        "schema_version": "icse_methodset_v1",
        "runs": summary_rows,
        "total_tracks": len(summary_rows),
    }
    out_path = out_root / "methodset_summary.json"
    out_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print("Wrote:")
    print(" ", out_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
