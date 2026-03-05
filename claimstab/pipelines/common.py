from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from claimstab.core import ArtifactManifest, ExecutionEvent, JsonlEventLogger, TraceIndex
from claimstab.perturbations.space import CompilationPerturbation, ExecutionPerturbation, PerturbationConfig, PerturbationSpace
from claimstab.runners.matrix_runner import ScoreRow
from claimstab.spec import load_spec

PerturbationKey = tuple[int, int, str | None, int, int | None]

SUITE_ALIASES: dict[str, str] = {
    "core": "core",
    "standard": "standard",
    "large": "large",
    "day1": "core",
    "day2": "standard",
    "day2_large": "large",
}

LEGACY_SUITE_ALIASES: set[str] = {"day1", "day2", "day2_large"}

SPACE_ALIASES: dict[str, str] = {
    "baseline": "baseline",
    "compilation_only": "compilation_only",
    "sampling_only": "sampling_only",
    "combined_light": "combined_light",
    "day1_default": "baseline",
}

CSV_COLUMNS: tuple[str, ...] = (
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
)


def parse_csv_tokens(raw: str) -> list[str]:
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def parse_deltas(raw: str, *, error_message: str = "At least one delta must be provided.") -> list[float]:
    deltas = [float(token) for token in parse_csv_tokens(raw)]
    if not deltas:
        raise ValueError(error_message)
    return deltas


def parse_claim_pairs(
    raw: str,
    *,
    fallback_pair: tuple[str, str] | None = None,
    require_distinct: bool = False,
    empty_error: str = "At least one claim pair is required.",
) -> list[tuple[str, str]]:
    if not str(raw).strip():
        if fallback_pair is not None:
            return [fallback_pair]
        raise ValueError(empty_error)

    pairs: list[tuple[str, str]] = []
    for token in parse_csv_tokens(raw):
        if ">" in token:
            left, right = token.split(">", 1)
        elif ":" in token:
            left, right = token.split(":", 1)
        else:
            raise ValueError(f"Invalid claim pair token '{token}'. Use MethodA>MethodB.")
        method_a = left.strip()
        method_b = right.strip()
        if not method_a or not method_b:
            raise ValueError(f"Invalid claim pair token '{token}'.")
        if require_distinct and method_a == method_b:
            raise ValueError("Claim pair must compare different methods.")
        pairs.append((method_a, method_b))

    if not pairs:
        raise ValueError(empty_error)
    return pairs


def try_load_spec(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return load_spec(path, validate=False)


def canonical_suite_name(name: str) -> str:
    key = str(name).strip().lower()
    canonical = SUITE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SUITE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown suite '{name}'. Use one of: {valid}.")
    if key in LEGACY_SUITE_ALIASES:
        print(f"[WARN] Suite alias '{name}' is deprecated; using '{canonical}'.")
    return canonical


def canonical_space_name(name: str, *, space_label: str = "space preset") -> str:
    key = str(name).strip()
    canonical = SPACE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SPACE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown {space_label} '{name}'. Use one of: {valid}.")
    return canonical


def make_space(name: str, *, combined_light_shots: Sequence[int] | None = None) -> PerturbationSpace:
    if name == "baseline":
        return PerturbationSpace.conf_level_default()
    if name == "compilation_only":
        return PerturbationSpace.compilation_only()
    if name == "sampling_only":
        return PerturbationSpace.sampling_only()
    if name == "combined_light":
        if combined_light_shots is None:
            return PerturbationSpace.combined_light()
        shots = [int(v) for v in combined_light_shots]
        return PerturbationSpace(
            seeds_transpiler=list(range(10)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=shots,
            seeds_simulator=[0, 1, 2],
        )
    raise ValueError(f"Unknown preset: {name}")


def build_baseline_config(space: PerturbationSpace) -> tuple[dict[str, int | str | None], PerturbationConfig, PerturbationKey]:
    first = next(space.iter_configs())
    baseline_cfg: dict[str, int | str | None] = {
        "seed_transpiler": first.compilation.seed_transpiler,
        "optimization_level": first.compilation.optimization_level,
        "layout_method": first.compilation.layout_method,
        "shots": first.execution.shots,
        "seed_simulator": first.execution.seed_simulator,
    }
    baseline_pc = PerturbationConfig(
        compilation=CompilationPerturbation(
            seed_transpiler=first.compilation.seed_transpiler,
            optimization_level=first.compilation.optimization_level,
            layout_method=first.compilation.layout_method,
        ),
        execution=ExecutionPerturbation(
            shots=first.execution.shots,
            seed_simulator=first.execution.seed_simulator,
        ),
    )
    baseline_key = config_key(baseline_pc)
    return baseline_cfg, baseline_pc, baseline_key


def config_key(pc: PerturbationConfig) -> PerturbationKey:
    return (
        pc.compilation.seed_transpiler,
        pc.compilation.optimization_level,
        pc.compilation.layout_method,
        pc.execution.shots,
        pc.execution.seed_simulator,
    )


def key_sort_value(key: PerturbationKey) -> tuple[int, int, str, int, int]:
    return (
        int(key[0]),
        int(key[1]),
        "" if key[2] is None else str(key[2]),
        int(key[3]),
        -1 if key[4] is None else int(key[4]),
    )


def config_from_key(key: PerturbationKey) -> PerturbationConfig:
    return PerturbationConfig(
        compilation=CompilationPerturbation(
            seed_transpiler=int(key[0]),
            optimization_level=int(key[1]),
            layout_method=str(key[2]) if key[2] is not None else None,
        ),
        execution=ExecutionPerturbation(
            shots=int(key[3]),
            seed_simulator=None if key[4] is None else int(key[4]),
        ),
    )


def baseline_from_keys(keys: set[PerturbationKey]) -> tuple[dict[str, int | str | None], PerturbationKey]:
    if not keys:
        raise ValueError("Cannot infer baseline from empty key set.")
    baseline_key = sorted(keys, key=key_sort_value)[0]
    baseline_cfg: dict[str, int | str | None] = {
        "seed_transpiler": int(baseline_key[0]),
        "optimization_level": int(baseline_key[1]),
        "layout_method": baseline_key[2],
        "shots": int(baseline_key[3]),
        "seed_simulator": None if baseline_key[4] is None else int(baseline_key[4]),
    }
    return baseline_cfg, baseline_key


def build_evidence_ref(
    *,
    suite_name: str,
    space_name: str,
    metric_name: str,
    claim: dict[str, Any],
    artifact_manifest: ArtifactManifest,
    lookup_fields: Sequence[str],
) -> dict[str, Any]:
    methods: list[str] = []
    for key in ("method_a", "method_b", "method"):
        value = claim.get(key)
        if isinstance(value, str) and value:
            methods.append(value)
    return {
        "trace_query": {
            "suite": suite_name,
            "space_preset": space_name,
            "metric_name": metric_name,
            "methods": sorted(set(methods)),
        },
        "artifacts": {
            "trace_jsonl": artifact_manifest.trace_jsonl,
            "events_jsonl": artifact_manifest.events_jsonl,
            "cache_db": artifact_manifest.cache_db,
        },
        "lookup_fields": [str(v) for v in lookup_fields],
    }


def make_event_logger(path: Path) -> Callable[[dict[str, Any]], None]:
    sink = JsonlEventLogger(path)

    def _log(payload: dict[str, Any]) -> None:
        core_keys = {"event_type", "instance_id", "method", "metric_name", "config"}
        event = ExecutionEvent.build(
            event_type=str(payload.get("event_type", "unknown")),
            instance_id=str(payload.get("instance_id", "unknown")),
            method=str(payload.get("method", "unknown")),
            metric_name=str(payload.get("metric_name", "objective")),
            config=dict(payload.get("config", {}) or {}),
            details={k: v for k, v in payload.items() if k not in core_keys},
        )
        sink.log(event)

    return _log


def _key_from_row(row: ScoreRow) -> PerturbationKey:
    return (
        int(row.seed_transpiler),
        int(row.optimization_level),
        row.layout_method,
        int(row.shots),
        None if row.seed_simulator is None else int(row.seed_simulator),
    )


def load_rows_from_trace_by_space(
    trace_path: Path,
) -> tuple[
    list[tuple[str, str, ScoreRow]],
    dict[str, dict[str, dict[str, list[ScoreRow]]]],
    dict[str, set[PerturbationKey]],
]:
    trace_index = TraceIndex.load_jsonl(trace_path)
    all_rows: list[tuple[str, str, ScoreRow]] = []
    rows_by_space_metric_graph: dict[str, dict[str, dict[str, list[ScoreRow]]]] = {}
    keys_by_space: dict[str, set[PerturbationKey]] = defaultdict(set)

    for rec in trace_index.records:
        suite_name = str(rec.suite or "replay")
        space_name = str(rec.space_preset or "baseline")
        row = rec.to_score_row()
        all_rows.append((suite_name, space_name, row))
        rows_by_space_metric_graph.setdefault(space_name, {}).setdefault(row.metric_name, {}).setdefault(row.instance_id, []).append(row)
        keys_by_space[space_name].add(_key_from_row(row))

    return all_rows, rows_by_space_metric_graph, keys_by_space


def load_rows_from_trace_by_batch(
    trace_path: Path,
) -> tuple[
    str,
    dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]],
    dict[str, set[PerturbationKey]],
    dict[str, str],
]:
    trace_index = TraceIndex.load_jsonl(trace_path)
    rows_by_batch: dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]] = {}
    keys_by_batch: dict[str, set[PerturbationKey]] = defaultdict(set)
    space_by_batch: dict[str, str] = {}
    suites: set[str] = set()

    for rec in trace_index.records:
        row = rec.to_score_row()
        suites.add(str(rec.suite or "replay"))
        batch_mode = str(row.device_mode or "unknown")
        device_name = str(row.device_name or "unknown_device")
        metric_name = str(row.metric_name or "objective")
        space_name = str(rec.space_preset or "baseline")

        rows_by_batch.setdefault(batch_mode, {}).setdefault(device_name, {}).setdefault(metric_name, {}).setdefault(row.instance_id, []).append(row)
        keys_by_batch[batch_mode].add(_key_from_row(row))
        space_by_batch.setdefault(batch_mode, space_name)

    suite_name = sorted(suites)[0] if suites else "replay"
    return suite_name, rows_by_batch, keys_by_batch, space_by_batch


def write_rows_csv(rows: Iterable[ScoreRow], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(CSV_COLUMNS))
        for row in rows:
            writer.writerow(
                [
                    row.instance_id,
                    row.seed_transpiler,
                    row.optimization_level,
                    row.layout_method,
                    row.seed_simulator,
                    row.shots,
                    row.method,
                    row.score,
                    row.transpiled_depth,
                    row.transpiled_size,
                    row.device_provider,
                    row.device_name,
                    row.device_mode,
                    row.device_snapshot_fingerprint,
                    row.circuit_depth,
                    row.two_qubit_count,
                    row.swap_count,
                ]
            )
