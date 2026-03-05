from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from claimstab.runners.matrix_runner import ScoreRow


def write_rows_csv(rows: Iterable[ScoreRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
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
        )
        for r in rows:
            w.writerow(
                [
                    r.instance_id,
                    r.seed_transpiler,
                    r.optimization_level,
                    r.layout_method,
                    r.seed_simulator,
                    r.shots,
                    r.method,
                    r.score,
                    r.transpiled_depth,
                    r.transpiled_size,
                    r.device_provider,
                    r.device_name,
                    r.device_mode,
                    r.device_snapshot_fingerprint,
                    r.circuit_depth,
                    r.two_qubit_count,
                    r.swap_count,
                ]
            )


def write_scores_csv(rows: Iterable[tuple[str, str, ScoreRow]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "suite",
                "space_preset",
                "instance_id",
                "seed_transpiler",
                "optimization_level",
                "layout_method",
                "seed_simulator",
                "shots",
                "method",
                "metric_name",
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
        )

        for suite_name, space_name, r in rows:
            w.writerow(
                [
                    suite_name,
                    space_name,
                    r.instance_id,
                    r.seed_transpiler,
                    r.optimization_level,
                    r.layout_method,
                    r.seed_simulator,
                    r.shots,
                    r.method,
                    r.metric_name,
                    r.score,
                    r.transpiled_depth,
                    r.transpiled_size,
                    r.device_provider,
                    r.device_name,
                    r.device_mode,
                    r.device_snapshot_fingerprint,
                    r.circuit_depth,
                    r.two_qubit_count,
                    r.swap_count,
                ]
            )
