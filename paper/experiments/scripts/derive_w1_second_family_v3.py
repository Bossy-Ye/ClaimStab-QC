from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _extract_rows(family: str, path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "family": family,
                "claim_pair": str(row.get("claim_pair")),
                "space_preset": str(row.get("space_preset")),
                "delta": float(row.get("delta", 0.0)),
                "stability_hat": float(row.get("stability_hat", 0.0)),
                "decision": str(row.get("decision")),
                "stability_ci_low": float(row.get("stability_ci_low", 0.0)),
                "stability_ci_high": float(row.get("stability_ci_high", 0.0)),
            }
        )
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Derive evaluation_v3 W1 second-family summaries.")
    ap.add_argument("--root", default="output/paper/evaluation_v3")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    derived = root / "derived_paper_evaluation" / "RQ2_semantics"
    derived.mkdir(parents=True, exist_ok=True)

    sources = {
        "vqe_h2": root / "runs" / "W1_vqe_pilot" / "claim_stability.json",
        "max2sat_qaoa": root / "runs" / "W1_max2sat_second_family" / "claim_stability.json",
    }

    all_rows: list[dict[str, Any]] = []
    counts: list[dict[str, Any]] = []
    for family, path in sources.items():
        rows = _extract_rows(family, path)
        all_rows.extend(rows)
        decision_counts = {"stable": 0, "unstable": 0, "inconclusive": 0}
        for row in rows:
            decision_counts[row["decision"]] = decision_counts.get(row["decision"], 0) + 1
        counts.append(
            {
                "family": family,
                "stable": decision_counts.get("stable", 0),
                "unstable": decision_counts.get("unstable", 0),
                "inconclusive": decision_counts.get("inconclusive", 0),
                "total": len(rows),
            }
        )

    _write_csv(derived / "w1_second_family_variant_rows.csv", all_rows)
    _write_csv(derived / "w1_second_family_verdict_counts.csv", counts)

    summary = {
        "schema_version": "w1_second_family_summary_v1",
        "sources": {k: str(v.resolve()) for k, v in sources.items()},
        "counts": counts,
    }
    (derived / "w1_second_family_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote W1 summaries to {derived}")


if __name__ == "__main__":
    main()
