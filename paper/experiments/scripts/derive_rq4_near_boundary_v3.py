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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Derive RQ4 near-boundary policy summaries for evaluation_v3.")
    ap.add_argument("--root", default="output/paper/evaluation_v3")
    ap.add_argument("--source-e5", default="output/paper/evaluation_v2/runs/E5_policy_comparison/rq4_policy_summary.json")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    out_dir = root / "derived_paper_evaluation" / "RQ4_practicality"
    out_dir.mkdir(parents=True, exist_ok=True)

    w5_summary = _read_json(root / "runs" / "W5_near_boundary_policy" / "rq4_near_boundary_summary.json")
    e5_summary = _read_json(Path(args.source_e5))

    by_strategy: list[dict[str, Any]] = []
    by_variant: list[dict[str, Any]] = []
    combined: list[dict[str, Any]] = []

    for pack_name, summary in [("baseline_e5", e5_summary), ("near_boundary_w5", w5_summary)]:
        for strategy in summary.get("strategies", []):
            if not isinstance(strategy, dict):
                continue
            by_strategy.append(
                {
                    "pack": pack_name,
                    "strategy": strategy.get("strategy"),
                    "strategy_group": strategy.get("strategy_group"),
                    "k_used": strategy.get("k_used"),
                    "perturbation_space_size": strategy.get("perturbation_space_size"),
                    "agreement_rate": (strategy.get("agreement_with_factorial") or {}).get("rate"),
                }
            )
            combined.append(
                {
                    "pack": pack_name,
                    "strategy": strategy.get("strategy"),
                    "k_used": strategy.get("k_used"),
                    "agreement_rate": (strategy.get("agreement_with_factorial") or {}).get("rate"),
                }
            )
            for row in strategy.get("rows_by_delta", []):
                if not isinstance(row, dict):
                    continue
                by_variant.append(
                    {
                        "pack": pack_name,
                        "strategy": strategy.get("strategy"),
                        "claim_pair": row.get("claim_pair"),
                        "delta": row.get("delta"),
                        "decision": row.get("decision"),
                        "stability_hat": row.get("stability_hat"),
                        "stability_ci_low": row.get("stability_ci_low"),
                        "stability_ci_high": row.get("stability_ci_high"),
                        "source_s2_space_preset": row.get("source_s2_space_preset"),
                        "source_s2_stability_hat": row.get("source_s2_stability_hat"),
                        "source_s2_decision": row.get("source_s2_decision"),
                    }
                )

    _write_csv(out_dir / "w5_policy_by_strategy.csv", by_strategy)
    _write_csv(out_dir / "w5_policy_by_variant.csv", by_variant)
    _write_csv(out_dir / "e5_w5_policy_combined.csv", combined)
    _write_json(
        out_dir / "w5_near_boundary_summary.json",
        {
            "schema_version": "rq4_near_boundary_v3_v1",
            "w5_summary_path": str((root / "runs" / "W5_near_boundary_policy" / "rq4_near_boundary_summary.json").resolve()),
            "source_e5_summary_path": str(Path(args.source_e5).resolve()),
            "rows": {
                "by_strategy": len(by_strategy),
                "by_variant": len(by_variant),
            },
        },
    )
    print("Wrote RQ4 near-boundary derived outputs to:", out_dir.resolve())


if __name__ == "__main__":
    main()
