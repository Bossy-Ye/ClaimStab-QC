# claimstab/io/writers.py
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, Dict, Any, List

from claimstab.runners.matrix_runner import ScoreRow


CSV_COLUMNS = [
    "instance_id",
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "seed_simulator",
    "shots",
    "method",
    "score",
    "transpiled_depth",
    "transpiled_size",
    "device_provider",
    "device_name",
    "device_mode",
    "device_snapshot_fingerprint",
    "circuit_depth",
    "two_qubit_count",
    "swap_count",
]


def write_scores_csv(rows: Iterable[ScoreRow], out_csv: str | Path) -> Path:
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            d = asdict(r)
            # enforce column order + avoid extra fields
            w.writerow({k: d[k] for k in CSV_COLUMNS})

    return out_path


def compute_method_stats(rows: List[ScoreRow]) -> Dict[str, Dict[str, float]]:
    by_method: Dict[str, List[float]] = {}
    for r in rows:
        by_method.setdefault(r.method, []).append(float(r.score))

    stats: Dict[str, Dict[str, float]] = {}
    for m, xs in by_method.items():
        stats[m] = {
            "n": len(xs),
            "mean": float(mean(xs)) if xs else 0.0,
            "std": float(pstdev(xs)) if len(xs) > 1 else 0.0,
            "min": float(min(xs)) if xs else 0.0,
            "max": float(max(xs)) if xs else 0.0,
        }
    return stats


def write_summary_json(
    rows: List[ScoreRow],
    out_json: str | Path,
    *,
    baseline: Dict[str, Any] | None = None,
    extra: Dict[str, Any] | None = None,
) -> Path:
    out_path = Path(out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "schema": CSV_COLUMNS,
        "total_rows": len(rows),
        "method_stats": compute_method_stats(rows),
        "baseline": baseline or {},
    }
    if extra:
        payload.update(extra)

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
