from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Callable, Iterable

from claimstab.core import ArtifactManifest
from claimstab.evidence import build_cep_protocol_meta
from claimstab.methods.spec import MethodSpec
from claimstab.pipelines.common import (
    baseline_from_keys as _baseline_from_keys,
    build_baseline_config as _build_baseline_config,
    build_evidence_ref as _build_evidence_ref,
    canonical_space_name as _canonical_space_name,
    canonical_suite_name as _canonical_suite_name,
    config_from_key as _config_from_key,
    key_sort_value as _key_sort_value,
    load_rows_from_trace_by_batch as _load_rows_from_trace_by_batch,
    make_event_logger as _make_event_logger,
    make_space as _make_space,
    parse_claim_pairs as _parse_claim_pairs,
    parse_csv_tokens as _parse_csv_tokens,
    parse_deltas as _parse_deltas,
    try_load_spec as _try_load_spec,
    write_rows_csv as _write_rows_csv,
)
from claimstab.pipelines.multidevice_emit import build_and_write_multidevice_outputs
from claimstab.pipelines.multidevice_execution import (
    MultideviceCallbacks,
    execute_multidevice_plan,
    evaluate_rows_for_claim as _evaluate_rows_for_claim,
)
from claimstab.pipelines.multidevice_planning import resolve_multidevice_plan
from claimstab.perturbations.space import PerturbationConfig, PerturbationSpace
from claimstab.runners.matrix_runner import ScoreRow
from claimstab.tasks.base import BuiltWorkflow

EVIDENCE_LOOKUP_FIELDS = [
    "suite",
    "space_preset",
    "instance_id",
    "method",
    "metric_name",
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
    "device_name",
    "device_mode",
]


ConfigKey = tuple[int, int, str | None, int, int | None]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ClaimStab multi-device demo (transpile-only + noisy simulation)")
    ap.add_argument("--run", choices=["all", "transpile_only", "noisy_sim"], default="all")
    ap.add_argument("--suite", default="standard", help="Suite preset: core | standard | large.")
    ap.add_argument("--out-dir", default="output")
    ap.add_argument("--sampling-mode", choices=["full_factorial", "random_k"], default="full_factorial")
    ap.add_argument("--sample-size", type=int, default=40)
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--stability-threshold", type=float, default=0.95)
    ap.add_argument("--confidence-level", type=float, default=0.95)
    ap.add_argument("--deltas", default="0.0,0.01,0.05")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default=os.getenv("CLAIMSTAB_SIMULATOR", "auto"))
    ap.add_argument("--transpile-space", default="compilation_only")
    ap.add_argument("--noisy-space", default="sampling_only")
    ap.add_argument(
        "--transpile-devices",
        default="FakeManilaV2,FakeBrisbane,FakePrague,FakeSherbrooke,FakeKyoto,FakeTorino",
        help="Comma-separated IBM fake backend names/classes for transpile-only runs.",
    )
    ap.add_argument(
        "--noisy-devices",
        default="FakeManilaV2,FakeBrisbane",
        help="Comma-separated IBM fake backend names/classes for noisy simulation runs.",
    )
    ap.add_argument(
        "--transpile-claim-pairs",
        default="QAOA_p1>QAOA_p2,QAOA_p1>RandomBaseline,QAOA_p2>RandomBaseline",
        help="Comma-separated pairs for structural claims (lower is better).",
    )
    ap.add_argument(
        "--noisy-claim-pairs",
        default="QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline",
        help="Comma-separated pairs for objective claims (higher is better).",
    )
    ap.add_argument(
        "--spec",
        default=None,
        help="Optional YAML/JSON file. Optional blocks: device_profile, backend.noise_model. Missing blocks keep defaults.",
    )
    ap.add_argument("--cache-db", default=None, help="Optional sqlite cache path for matrix cell reuse.")
    ap.add_argument("--events-out", default=None, help="Optional JSONL output path for execution events.")
    ap.add_argument("--trace-out", default=None, help="Optional JSONL output path for trace records.")
    ap.add_argument("--replay-trace", default=None, help="Replay mode: load trace JSONL and skip execution.")
    ap.add_argument(
        "--use-operator-shim",
        action="store_true",
        help="Use perturbation operator shim to generate config pool (backward-compatible opt-in).",
    )
    return ap.parse_args()


def parse_csv_tokens(raw: str) -> list[str]:
    return _parse_csv_tokens(raw)


def parse_deltas(raw: str) -> list[float]:
    return _parse_deltas(raw)


def parse_claim_pairs(raw: str) -> list[tuple[str, str]]:
    return _parse_claim_pairs(raw, require_distinct=True, empty_error="At least one claim pair is required.")


def canonical_suite_name(name: str) -> str:
    return _canonical_suite_name(name)


def canonical_space_name(name: str) -> str:
    return _canonical_space_name(name, space_label="space")


def make_space(name: str) -> PerturbationSpace:
    return _make_space(name)


class BoundTask:
    """MatrixRunner-compatible adapter for TaskPlugin(instance, method) API."""

    def __init__(self, plugin, instance) -> None:
        self.plugin = plugin
        self.instance = instance
        self.instance_id = instance.instance_id

    def build(self, method):
        built = self.plugin.build(self.instance, method)
        if isinstance(built, BuiltWorkflow):
            return built.circuit, built.metric_fn
        return built

    def infer_num_qubits(self, methods: list[MethodSpec]) -> int:
        payload = getattr(self.instance, "payload", None)
        graph_nodes = getattr(payload, "num_nodes", None)
        if isinstance(graph_nodes, int) and graph_nodes > 0:
            return graph_nodes
        if not methods:
            raise ValueError("Cannot infer qubit count without methods.")
        circuit, _ = self.build(methods[0])
        num_qubits = getattr(circuit, "num_qubits", None)
        if not isinstance(num_qubits, int) or num_qubits <= 0:
            raise ValueError(f"Cannot infer qubit count for instance '{self.instance_id}'.")
        return num_qubits


def build_baseline(space: PerturbationSpace):
    baseline_dict, baseline_pc, baseline_key = _build_baseline_config(space)
    return baseline_pc, baseline_key, baseline_dict


def key_sort_value(key: ConfigKey) -> tuple[int, int, str, int, int]:
    return _key_sort_value(key)


def config_from_key(key: ConfigKey) -> PerturbationConfig:
    return _config_from_key(key)


def baseline_from_keys(keys: set[ConfigKey]) -> tuple[ConfigKey, dict[str, int | str | None]]:
    baseline_dict, baseline_key = _baseline_from_keys(keys)
    return baseline_key, baseline_dict


def build_evidence_ref(
    *,
    suite_name: str,
    space_name: str,
    metric_name: str,
    claim: dict[str, Any],
    artifact_manifest: ArtifactManifest,
) -> dict[str, Any]:
    return _build_evidence_ref(
        suite_name=suite_name,
        space_name=space_name,
        metric_name=metric_name,
        claim=claim,
        artifact_manifest=artifact_manifest,
        lookup_fields=EVIDENCE_LOOKUP_FIELDS,
    )


def evidence_chain_meta() -> dict[str, Any]:
    return build_cep_protocol_meta(
        lookup_fields=EVIDENCE_LOOKUP_FIELDS,
        decision_provenance=(
            "each experiment includes evidence.trace_query + evidence.cep blocks "
            "that can be matched against trace records for reproducible decision provenance"
        ),
    )


def make_event_logger(path: Path) -> Callable[[dict[str, Any]], None]:
    return _make_event_logger(path)


def load_rows_from_trace(
    trace_path: Path,
) -> tuple[
    str,
    dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]],
    dict[str, set[ConfigKey]],
    dict[str, str],
]:
    return _load_rows_from_trace_by_batch(trace_path)


def evaluate_rows_for_claim(
    *,
    rows_by_graph: dict[str, list[ScoreRow]],
    method_a: str,
    method_b: str,
    deltas: list[float],
    baseline_key: ConfigKey,
    direction,
    stability_threshold: float,
    confidence_level: float,
) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    return _evaluate_rows_for_claim(
        rows_by_graph=rows_by_graph,
        method_a=method_a,
        method_b=method_b,
        deltas=deltas,
        baseline_key=baseline_key,
        direction=direction,
        stability_threshold=stability_threshold,
        confidence_level=confidence_level,
    )


def write_rows_csv(rows: Iterable[ScoreRow], out_csv: Path) -> None:
    _write_rows_csv(rows, out_csv)


def try_load_spec(path: str | None) -> dict:
    return _try_load_spec(path)


def main() -> None:
    plan = resolve_multidevice_plan(
        parse_args(),
        canonical_suite_name_fn=canonical_suite_name,
        parse_deltas_fn=parse_deltas,
        canonical_space_name_fn=canonical_space_name,
        try_load_spec_fn=try_load_spec,
        bound_task_cls=BoundTask,
    )
    callbacks = MultideviceCallbacks(
        parse_csv_tokens=parse_csv_tokens,
        parse_claim_pairs=parse_claim_pairs,
        make_space=make_space,
        build_baseline=build_baseline,
        key_sort_value=key_sort_value,
        config_from_key=config_from_key,
        baseline_from_keys=baseline_from_keys,
        build_evidence_ref=build_evidence_ref,
        evidence_chain_meta=evidence_chain_meta,
        make_event_logger=make_event_logger,
        load_rows_from_trace=load_rows_from_trace,
        evaluate_rows_for_claim=evaluate_rows_for_claim,
        write_rows_csv=write_rows_csv,
    )
    execution_result = execute_multidevice_plan(
        plan,
        callbacks=callbacks,
        bound_task_cls=BoundTask,
    )
    build_and_write_multidevice_outputs(
        plan,
        execution_result,
        evidence_chain_meta_fn=evidence_chain_meta,
    )


if __name__ == "__main__":
    main()
