from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from claimstab.runners.matrix_runner import ScoreRow


@dataclass(frozen=True)
class TraceRecord:
    suite: str
    space_preset: str
    instance_id: str
    method: str
    metric_name: str
    seed_transpiler: int
    optimization_level: int
    layout_method: str | None
    seed_simulator: int | None
    shots: int
    score: float
    transpiled_depth: int
    transpiled_size: int
    circuit_depth: int | None = None
    two_qubit_count: int | None = None
    swap_count: int | None = None
    counts: dict[str, int] | None = None
    transpile_time_ms: float | None = None
    execute_time_ms: float | None = None
    wall_time_ms: float | None = None
    device_provider: str | None = None
    device_name: str | None = None
    device_mode: str | None = None
    device_snapshot_fingerprint: str | None = None

    @staticmethod
    def from_score_row(*, suite: str, space_preset: str, row: ScoreRow) -> "TraceRecord":
        return TraceRecord(
            suite=suite,
            space_preset=space_preset,
            instance_id=row.instance_id,
            method=row.method,
            metric_name=row.metric_name,
            seed_transpiler=row.seed_transpiler,
            optimization_level=row.optimization_level,
            layout_method=row.layout_method,
            seed_simulator=row.seed_simulator,
            shots=row.shots,
            score=float(row.score),
            transpiled_depth=row.transpiled_depth,
            transpiled_size=row.transpiled_size,
            circuit_depth=row.circuit_depth,
            two_qubit_count=row.two_qubit_count,
            swap_count=row.swap_count,
            counts=dict(row.counts) if row.counts is not None else None,
            transpile_time_ms=row.transpile_time_ms,
            execute_time_ms=row.execute_time_ms,
            wall_time_ms=row.wall_time_ms,
            device_provider=row.device_provider,
            device_name=row.device_name,
            device_mode=row.device_mode,
            device_snapshot_fingerprint=row.device_snapshot_fingerprint,
        )

    def to_score_row(self) -> ScoreRow:
        return ScoreRow(
            instance_id=self.instance_id,
            seed_transpiler=self.seed_transpiler,
            optimization_level=self.optimization_level,
            transpiled_depth=self.transpiled_depth,
            transpiled_size=self.transpiled_size,
            method=self.method,
            score=float(self.score),
            metric_name=self.metric_name,
            seed_simulator=self.seed_simulator,
            shots=self.shots,
            layout_method=self.layout_method,
            device_provider=self.device_provider,
            device_name=self.device_name,
            device_mode=self.device_mode,
            device_snapshot_fingerprint=self.device_snapshot_fingerprint,
            circuit_depth=self.circuit_depth,
            two_qubit_count=self.two_qubit_count,
            swap_count=self.swap_count,
            counts=dict(self.counts) if self.counts is not None else None,
            transpile_time_ms=self.transpile_time_ms,
            execute_time_ms=self.execute_time_ms,
            wall_time_ms=self.wall_time_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(payload: Mapping[str, Any]) -> "TraceRecord":
        counts = payload.get("counts")
        return TraceRecord(
            suite=str(payload.get("suite", "")),
            space_preset=str(payload.get("space_preset", "")),
            instance_id=str(payload.get("instance_id", "")),
            method=str(payload.get("method", "")),
            metric_name=str(payload.get("metric_name", "objective")),
            seed_transpiler=int(payload.get("seed_transpiler", 0)),
            optimization_level=int(payload.get("optimization_level", 0)),
            layout_method=(None if payload.get("layout_method") is None else str(payload.get("layout_method"))),
            seed_simulator=(None if payload.get("seed_simulator") is None else int(payload.get("seed_simulator"))),
            shots=int(payload.get("shots", 1024)),
            score=float(payload.get("score", 0.0)),
            transpiled_depth=int(payload.get("transpiled_depth", 0)),
            transpiled_size=int(payload.get("transpiled_size", 0)),
            circuit_depth=(None if payload.get("circuit_depth") is None else int(payload.get("circuit_depth"))),
            two_qubit_count=(None if payload.get("two_qubit_count") is None else int(payload.get("two_qubit_count"))),
            swap_count=(None if payload.get("swap_count") is None else int(payload.get("swap_count"))),
            counts=({str(k): int(v) for k, v in dict(counts).items()} if isinstance(counts, Mapping) else None),
            transpile_time_ms=(
                None if payload.get("transpile_time_ms") is None else float(payload.get("transpile_time_ms"))
            ),
            execute_time_ms=(
                None if payload.get("execute_time_ms") is None else float(payload.get("execute_time_ms"))
            ),
            wall_time_ms=(None if payload.get("wall_time_ms") is None else float(payload.get("wall_time_ms"))),
            device_provider=(None if payload.get("device_provider") is None else str(payload.get("device_provider"))),
            device_name=(None if payload.get("device_name") is None else str(payload.get("device_name"))),
            device_mode=(None if payload.get("device_mode") is None else str(payload.get("device_mode"))),
            device_snapshot_fingerprint=(
                None if payload.get("device_snapshot_fingerprint") is None else str(payload.get("device_snapshot_fingerprint"))
            ),
        )


@dataclass
class TraceIndex:
    records: list[TraceRecord] = field(default_factory=list)

    def add(self, record: TraceRecord) -> None:
        self.records.append(record)

    def extend(self, records: Iterable[TraceRecord]) -> None:
        self.records.extend(records)

    def save_jsonl(self, path: str | Path) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec.to_dict(), sort_keys=True) + "\n")

    @staticmethod
    def load_jsonl(path: str | Path) -> "TraceIndex":
        src = Path(path)
        records: list[TraceRecord] = []
        with src.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(TraceRecord.from_dict(json.loads(line)))
        return TraceIndex(records=records)


@dataclass(frozen=True)
class ArtifactManifest:
    trace_jsonl: str
    events_jsonl: str | None
    cache_db: str | None
