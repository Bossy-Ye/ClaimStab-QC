from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping

from qiskit.transpiler import CouplingMap

from claimstab.claims.diagnostics import (
    build_conditional_robustness_summary,
    compute_stability_vs_shots,
    compute_effect_diagnostics,
    minimum_shots_for_stable,
)
from claimstab.claims.evaluation import collect_paired_scores
from claimstab.claims.ranking import HigherIsBetter, RankingClaim
from claimstab.claims.stability import (
    conservative_stability_decision,
    estimate_binomial_rate,
    estimate_clustered_stability,
)
from claimstab.io.runtime_meta import collect_runtime_metadata
from claimstab.analysis.rq import build_rq_summary
from claimstab.baselines.naive import NAIVE_POLICY_REALISTIC, evaluate_naive_baseline
from claimstab.cache.store import CacheStore
from claimstab.core import ArtifactManifest, TraceIndex, TraceRecord
from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.evidence import build_cep_protocol_meta, build_experiment_cep_record
from claimstab.pipelines.aggregate import (
    aggregate_factor_attribution as _aggregate_factor_attribution,
    build_method_scores_by_key as _build_method_scores_by_key,
    build_robustness_map_artifact as _build_robustness_map_artifact,
)
from claimstab.pipelines.common import (
    baseline_from_keys as _baseline_from_keys,
    build_baseline_config as _build_baseline_config,
    build_evidence_ref as _build_evidence_ref,
    canonical_space_name as _canonical_space_name,
    canonical_suite_name as _canonical_suite_name,
    config_from_key as _config_from_key,
    config_key as _config_key,
    key_sort_value as _key_sort_value,
    load_rows_from_trace_by_space as _load_rows_from_trace_by_space,
    make_event_logger as _make_event_logger,
    make_space as _make_space,
    parse_claim_pairs as _parse_claim_pairs,
    parse_csv_tokens as _parse_csv_tokens,
    parse_deltas as _parse_deltas,
    try_load_spec as _try_load_spec,
)
from claimstab.pipelines.emit import write_scores_csv as _write_scores_csv
from claimstab.pipelines.evaluate import (
    derive_instance_strata as _derive_instance_strata_impl,
    evaluate_auxiliary_claim_examples as _evaluate_auxiliary_claim_examples,
    evaluate_claim_on_rows as _evaluate_claim_on_rows,
    evaluate_decision_claim_on_rows as _evaluate_decision_claim_on_rows,
    evaluate_distribution_claim_on_rows as _evaluate_distribution_claim_on_rows,
)
from claimstab.pipelines.runner import (
    BoundTask as _BoundTask,
    build_coupling_map as _build_coupling_map,
    filter_rows_by_keys as _filter_rows_by_keys,
    select_adaptive_keys as _select_adaptive_keys,
)
from claimstab.perturbations.sampling import SamplingPolicy, ensure_config_included, sample_configs
from claimstab.perturbations.space import PerturbationConfig, PerturbationSpace
from claimstab.runners.matrix_runner import MatrixRunner, ScoreRow
from claimstab.runners.qiskit_aer import QiskitAerRunner
from claimstab.tasks.factory import make_task, parse_methods

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
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ClaimStab demo with batch claim/space evaluation")
    ap.add_argument(
        "--suite",
        default="core",
        help="Suite preset: core | standard | large.",
    )
    ap.add_argument(
        "--task",
        default=None,
        help="Optional task override, e.g. maxcut or bv.",
    )
    ap.add_argument(
        "--space-preset",
        default="baseline",
        help="Single-space mode. Ignored if --space-presets is provided.",
    )
    ap.add_argument(
        "--space-presets",
        default="",
        help="Comma-separated spaces for deterministic comparison, e.g. compilation_only,sampling_only,combined_light",
    )
    ap.add_argument("--sampling-mode", choices=["full_factorial", "random_k", "adaptive_ci"], default="full_factorial")
    ap.add_argument("--sample-size", type=int, default=40, help="Used when --sampling-mode random_k")
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--target-ci-width", type=float, default=0.02, help="Used when --sampling-mode adaptive_ci")
    ap.add_argument("--max-sample-size", type=int, default=96, help="Used when --sampling-mode adaptive_ci")
    ap.add_argument("--min-sample-size", type=int, default=16, help="Used when --sampling-mode adaptive_ci")
    ap.add_argument("--step-size", type=int, default=8, help="Used when --sampling-mode adaptive_ci")
    ap.add_argument("--stability-threshold", type=float, default=0.95)
    ap.add_argument("--confidence-level", type=float, default=0.95)
    ap.add_argument("--deltas", default="0.0,0.01,0.05", help="Comma-separated delta values")
    ap.add_argument(
        "--ranking-metric",
        choices=["objective", "circuit_depth", "two_qubit_count", "swap_count"],
        default="objective",
        help="Metric for ranking claims (default: objective).",
    )
    ap.add_argument(
        "--lower-is-better",
        action="store_true",
        help="Treat ranking metric as lower-is-better.",
    )
    ap.add_argument("--method-a", default="QAOA_p2")
    ap.add_argument("--method-b", default="RandomBaseline")
    ap.add_argument(
        "--claim-pairs",
        default="",
        help="Comma-separated ranking pairs, e.g. QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1",
    )
    ap.add_argument("--top-k-unstable", type=int, default=5)
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default=os.getenv("CLAIMSTAB_SIMULATOR", "basic"))
    ap.add_argument("--spot-check-noise", action="store_true", help="Use a lightweight Aer depolarizing noise model.")
    ap.add_argument("--one-qubit-error", type=float, default=0.001)
    ap.add_argument("--two-qubit-error", type=float, default=0.01)
    ap.add_argument("--out-dir", default="output")
    ap.add_argument(
        "--spec",
        default=None,
        help="Optional YAML/JSON file. Optional blocks: device_profile, backend.noise_model.",
    )
    ap.add_argument(
        "--cache-db",
        default=None,
        help="Optional sqlite cache path. If set, runner reuses cached cells by fingerprint.",
    )
    ap.add_argument(
        "--events-out",
        default=None,
        help="Optional JSONL file for execution events.",
    )
    ap.add_argument(
        "--trace-out",
        default=None,
        help="Optional JSONL file for trace records (default: <out-dir>/trace.jsonl).",
    )
    ap.add_argument(
        "--replay-trace",
        default=None,
        help="Replay mode: load trace JSONL and recompute claims/reports without executing circuits.",
    )
    ap.add_argument(
        "--use-operator-shim",
        action="store_true",
        help="Use perturbation operator shim to generate config pool (backward-compatible opt-in).",
    )
    ap.add_argument(
        "--debug-attribution",
        action="store_true",
        help="Print intermediate RQ2 attribution aggregation diagnostics.",
    )
    return ap.parse_args()


def parse_deltas(raw: str) -> list[float]:
    return _parse_deltas(raw, error_message="At least one delta must be provided")


def _as_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def parse_csv_tokens(raw: str) -> list[str]:
    return _parse_csv_tokens(raw)


def try_load_spec(path: str | None) -> dict:
    return _try_load_spec(path)


def parse_claim_pairs(raw: str, fallback_pair: tuple[str, str]) -> list[tuple[str, str]]:
    return _parse_claim_pairs(
        raw,
        fallback_pair=fallback_pair,
        require_distinct=False,
        empty_error="At least one claim pair must be provided",
    )


def canonical_suite_name(name: str) -> str:
    return _canonical_suite_name(name)


def canonical_space_name(name: str) -> str:
    return _canonical_space_name(name, space_label="space preset")


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


DIMENSION_NAMES = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]


def write_scores_csv(rows: Iterable[tuple[str, str, ScoreRow]], path: Path) -> None:
    _write_scores_csv(rows, path)


def make_space(preset: str) -> PerturbationSpace:
    # Keep combined perturbations small but include multiple shot budgets so
    # the stability-vs-cost section can estimate a trend instead of a single point.
    return _make_space(preset, combined_light_shots=[64, 256, 1024])


def build_baseline_config(space: PerturbationSpace) -> tuple[dict[str, int | str], PerturbationConfig, tuple[int, int, str | None, int, int | None]]:
    return _build_baseline_config(space)


def config_key(pc: PerturbationConfig) -> tuple[int, int, str | None, int, int | None]:
    return _config_key(pc)


def key_sort_value(key: tuple[int, int, str | None, int, int | None]) -> tuple[int, int, str, int, int]:
    return _key_sort_value(key)


def config_from_key(key: tuple[int, int, str | None, int, int | None]) -> PerturbationConfig:
    return _config_from_key(key)


def baseline_from_keys(
    keys: set[tuple[int, int, str | None, int, int | None]],
) -> tuple[dict[str, int | str | None], tuple[int, int, str | None, int, int | None]]:
    return _baseline_from_keys(keys)


def make_event_logger(path: Path) -> Callable[[dict[str, Any]], None]:
    return _make_event_logger(path)


def filter_rows_by_keys(
    rows: list[ScoreRow],
    allowed_keys: set[tuple[int, int, str | None, int, int | None]],
) -> list[ScoreRow]:
    return _filter_rows_by_keys(rows, allowed_keys)


def select_adaptive_keys(
    *,
    sampled_configs: list[PerturbationConfig],
    paired_scores_by_graph: dict[str, dict[tuple[int, int, str | None, int, int | None], tuple[float, float]]],
    method_a: str,
    method_b: str,
    deltas: list[float],
    baseline_key: tuple[int, int, str | None, int, int | None],
    confidence_level: float,
    target_ci_width: float,
    min_sample_size: int,
    step_size: int,
) -> tuple[set[tuple[int, int, str | None, int, int | None]], dict[str, object]]:
    return _select_adaptive_keys(
        sampled_configs=sampled_configs,
        paired_scores_by_graph=paired_scores_by_graph,
        method_a=method_a,
        method_b=method_b,
        deltas=deltas,
        baseline_key=baseline_key,
        confidence_level=confidence_level,
        target_ci_width=target_ci_width,
        min_sample_size=min_sample_size,
        step_size=step_size,
    )


def parse_ranking_claims_from_spec(
    spec_payload: dict[str, Any],
    *,
    default_deltas: list[float],
    default_metric_name: str,
    default_higher_is_better: bool,
) -> list[dict[str, Any]]:
    claims = spec_payload.get("claims")
    jobs: list[dict[str, Any]] = []

    if isinstance(claims, list):
        for item in claims:
            if not isinstance(item, dict):
                continue
            if str(item.get("type", "ranking")).strip().lower() != "ranking":
                continue
            method_a = item.get("method_a")
            method_b = item.get("method_b")
            if not (isinstance(method_a, str) and method_a.strip() and isinstance(method_b, str) and method_b.strip()):
                continue
            deltas_raw = item.get("deltas")
            deltas = [float(x) for x in deltas_raw] if isinstance(deltas_raw, list) and deltas_raw else list(default_deltas)
            metric_name = str(item.get("metric_name", item.get("metric", default_metric_name))).strip() or default_metric_name
            jobs.append(
                {
                    "method_a": method_a.strip(),
                    "method_b": method_b.strip(),
                    "deltas": deltas,
                    "metric_name": metric_name,
                    "higher_is_better": _as_bool(item.get("higher_is_better"), default_higher_is_better),
                }
            )
    elif isinstance(claims, dict):
        ranking = claims.get("ranking")
        if isinstance(ranking, dict):
            method_a = ranking.get("method_a")
            method_b = ranking.get("method_b")
            if isinstance(method_a, str) and method_a.strip() and isinstance(method_b, str) and method_b.strip():
                deltas_raw = ranking.get("deltas")
                deltas = [float(x) for x in deltas_raw] if isinstance(deltas_raw, list) and deltas_raw else list(default_deltas)
                jobs.append(
                    {
                        "method_a": method_a.strip(),
                        "method_b": method_b.strip(),
                        "deltas": deltas,
                        "metric_name": str(ranking.get("metric_name", ranking.get("metric", default_metric_name))).strip()
                        or default_metric_name,
                        "higher_is_better": _as_bool(ranking.get("higher_is_better"), default_higher_is_better),
                    }
                )

    return jobs


def parse_decision_claims_from_spec(spec_payload: dict[str, Any]) -> list[dict[str, Any]]:
    claims = spec_payload.get("claims")
    out: list[dict[str, Any]] = []
    if isinstance(claims, list):
        for item in claims:
            if not isinstance(item, dict):
                continue
            if str(item.get("type", "")).strip().lower() != "decision":
                continue
            method = item.get("method")
            if not isinstance(method, str) or not method.strip():
                continue
            out.append(
                {
                    "type": "decision",
                    "method": method.strip(),
                    "top_k": int(item.get("top_k", 1)),
                    "label": item.get("label"),
                    "label_meta_key": str(item.get("label_meta_key", "target_label")),
                }
            )
    elif isinstance(claims, dict):
        decision = claims.get("decision")
        if isinstance(decision, dict):
            method = decision.get("method")
            if isinstance(method, str) and method.strip():
                out.append(
                    {
                        "type": "decision",
                        "method": method.strip(),
                        "top_k": int(decision.get("top_k", decision.get("k", 1))),
                        "label": decision.get("label"),
                        "label_meta_key": str(decision.get("label_meta_key", "target_label")),
                    }
                )
    return out


def parse_distribution_claims_from_spec(spec_payload: dict[str, Any]) -> list[dict[str, Any]]:
    claims = spec_payload.get("claims")
    out: list[dict[str, Any]] = []
    if isinstance(claims, list):
        for item in claims:
            if not isinstance(item, dict):
                continue
            if str(item.get("type", "")).strip().lower() != "distribution":
                continue
            method = item.get("method")
            if not isinstance(method, str) or not method.strip():
                continue
            out.append(
                {
                    "type": "distribution",
                    "method": method.strip(),
                    "epsilon": float(item.get("epsilon", 0.2)),
                    "primary_distance": str(item.get("primary_distance", "js")).strip().lower() or "js",
                    "sanity_distance": str(item.get("sanity_distance", "tvd")).strip().lower() or "tvd",
                    "reference_shots": item.get("reference_shots", "max"),
                    "metric_name": str(item.get("metric_name", "objective")).strip() or "objective",
                }
            )
    elif isinstance(claims, dict):
        distribution = claims.get("distribution")
        if isinstance(distribution, dict):
            method = distribution.get("method")
            if isinstance(method, str) and method.strip():
                out.append(
                    {
                        "type": "distribution",
                        "method": method.strip(),
                        "epsilon": float(distribution.get("epsilon", 0.2)),
                        "primary_distance": str(distribution.get("primary_distance", "js")).strip().lower() or "js",
                        "sanity_distance": str(distribution.get("sanity_distance", "tvd")).strip().lower() or "tvd",
                        "reference_shots": distribution.get("reference_shots", "max"),
                        "metric_name": str(distribution.get("metric_name", "objective")).strip() or "objective",
                    }
                )
    return out


def has_explicit_claims(spec_payload: dict[str, Any]) -> bool:
    claims = spec_payload.get("claims")
    if isinstance(claims, list):
        return any(isinstance(item, dict) for item in claims)
    if isinstance(claims, dict):
        return bool(claims)
    return False


BoundTask = _BoundTask


def build_coupling_map(num_qubits: int) -> CouplingMap:
    return _build_coupling_map(num_qubits)


def aggregate_factor_attribution(per_graph_summary: dict[str, dict[str, object]], deltas: list[float], top_k: int) -> dict[str, object]:
    return _aggregate_factor_attribution(per_graph_summary, deltas, top_k)


def build_method_scores_by_key(rows: list[ScoreRow]) -> dict[tuple[int, int, str | None, int, int | None], dict[str, float]]:
    return _build_method_scores_by_key(rows)


def _derive_instance_strata(
    *,
    task_kind: str,
    graph_id: str,
    instance: Any | None,
    graph_rows: list[ScoreRow],
    method_name: str,
    baseline_key: tuple[int, int, str | None, int, int | None],
) -> dict[str, object]:
    return _derive_instance_strata_impl(
        task_kind=task_kind,
        graph_id=graph_id,
        instance=instance,
        graph_rows=graph_rows,
        method_name=method_name,
        baseline_key=baseline_key,
    )


def evaluate_auxiliary_claim_examples(
    *,
    method_scores_by_key: dict[tuple[int, int, str | None, int, int | None], dict[str, float]],
    baseline_key: tuple[int, int, str | None, int, int | None],
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    return _evaluate_auxiliary_claim_examples(
        method_scores_by_key=method_scores_by_key,
        baseline_key=baseline_key,
        stability_threshold=stability_threshold,
        confidence_level=confidence_level,
    )


def build_robustness_map_artifact(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    return _build_robustness_map_artifact(experiments)


def evaluate_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method_a: str,
    method_b: str,
    deltas: list[float],
    higher_is_better: bool,
    baseline_key: tuple[int, int, str | None, int, int | None],
    stability_threshold: float,
    confidence_level: float,
    top_k_unstable: int,
) -> dict[str, object]:
    return _evaluate_claim_on_rows(
        rows=rows,
        method_a=method_a,
        method_b=method_b,
        deltas=deltas,
        higher_is_better=higher_is_better,
        baseline_key=baseline_key,
        stability_threshold=stability_threshold,
        confidence_level=confidence_level,
        top_k_unstable=top_k_unstable,
    )


def evaluate_decision_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method: str,
    top_k: int,
    instance_target_label: str,
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    return _evaluate_decision_claim_on_rows(
        rows=rows,
        method=method,
        top_k=top_k,
        instance_target_label=instance_target_label,
        stability_threshold=stability_threshold,
        confidence_level=confidence_level,
    )


def evaluate_distribution_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method: str,
    baseline_key: tuple[int, int, str | None, int, int | None],
    epsilon: float,
    primary_distance: str,
    sanity_distance: str,
    reference_shots: int | str | None,
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    return _evaluate_distribution_claim_on_rows(
        rows=rows,
        method=method,
        baseline_key=baseline_key,
        key_sort_value=key_sort_value,
        epsilon=epsilon,
        primary_distance=primary_distance,
        sanity_distance=sanity_distance,
        reference_shots=reference_shots,
        stability_threshold=stability_threshold,
        confidence_level=confidence_level,
    )


def load_rows_from_trace(
    trace_path: Path,
) -> tuple[
    list[tuple[str, str, ScoreRow]],
    dict[str, dict[str, dict[str, list[ScoreRow]]]],
    dict[str, set[tuple[int, int, str | None, int, int | None]]],
]:
    return _load_rows_from_trace_by_space(trace_path)


def main() -> None:
    args = parse_args()
    args.suite = canonical_suite_name(args.suite)
    spec_payload = try_load_spec(args.spec)
    if args.task:
        if not isinstance(spec_payload, dict):
            spec_payload = {}
        task_block = spec_payload.get("task")
        if not isinstance(task_block, dict):
            task_block = {}
        task_block["kind"] = str(args.task).strip()
        task_block.setdefault("suite", args.suite)
        spec_payload["task"] = task_block
    deltas = parse_deltas(args.deltas)
    default_ranking_metric = args.ranking_metric
    default_higher_is_better = not args.lower_is_better
    selected_space_inputs = parse_csv_tokens(args.space_presets) if args.space_presets.strip() else [args.space_preset]
    selected_spaces = [canonical_space_name(name) for name in selected_space_inputs]

    task_plugin, task_suite = make_task(
        spec_payload.get("task") if isinstance(spec_payload, dict) else None,
        default_suite=args.suite,
    )
    suite_raw = str(spec_payload.get("suite", task_suite)).strip() if isinstance(spec_payload, dict) else str(task_suite)
    suite_name = canonical_suite_name(suite_raw)
    suite = task_plugin.instances(suite_name)
    if not suite:
        raise ValueError(f"Task '{getattr(task_plugin, 'name', 'unknown')}' returned an empty suite for '{suite_name}'.")
    suite_by_id = {inst.instance_id: inst for inst in suite}

    out_dir = Path(args.out_dir)
    out_csv = out_dir / "scores.csv"
    out_json = out_dir / "claim_stability.json"

    task_kind = str(getattr(task_plugin, "name", "maxcut")).strip().lower()
    methods = parse_methods(spec_payload if isinstance(spec_payload, dict) else {}, task_kind=task_kind)
    method_names = {m.name for m in methods}
    decision_claims = parse_decision_claims_from_spec(spec_payload if isinstance(spec_payload, dict) else {})
    distribution_claims = parse_distribution_claims_from_spec(spec_payload if isinstance(spec_payload, dict) else {})
    if task_kind == "bv" and not decision_claims:
        method_for_decision = methods[0].name if methods else "BVOracle"
        decision_claims = [
            {
                "type": "decision",
                "method": method_for_decision,
                "top_k": 1,
                "label": None,
                "label_meta_key": "target_label",
            },
            {
                "type": "decision",
                "method": method_for_decision,
                "top_k": 3,
                "label": None,
                "label_meta_key": "target_label",
            },
        ]
    if task_kind == "grover" and not distribution_claims:
        method_for_distribution = methods[0].name if methods else "GroverOracle"
        distribution_claims = [
            {
                "type": "distribution",
                "method": method_for_distribution,
                "epsilon": 0.20,
                "primary_distance": "js",
                "sanity_distance": "tvd",
                "reference_shots": "max",
                "metric_name": "objective",
            }
        ]
    spec_ranking_jobs = parse_ranking_claims_from_spec(
        spec_payload if isinstance(spec_payload, dict) else {},
        default_deltas=deltas,
        default_metric_name=default_ranking_metric,
        default_higher_is_better=default_higher_is_better,
    )
    if args.claim_pairs.strip():
        ranking_jobs = [
            {
                "method_a": method_a,
                "method_b": method_b,
                "deltas": list(deltas),
                "metric_name": default_ranking_metric,
                "higher_is_better": default_higher_is_better,
            }
            for method_a, method_b in parse_claim_pairs(args.claim_pairs, (args.method_a, args.method_b))
        ]
    elif spec_ranking_jobs:
        ranking_jobs = spec_ranking_jobs
    elif task_kind == "bv" and decision_claims:
        ranking_jobs = []
    elif has_explicit_claims(spec_payload if isinstance(spec_payload, dict) else {}) and not spec_ranking_jobs:
        ranking_jobs = []
    elif task_kind == "ghz":
        ranking_jobs = [
            {
                "method_a": "GHZ_Linear",
                "method_b": "GHZ_Star",
                "deltas": list(deltas),
                "metric_name": default_ranking_metric,
                "higher_is_better": default_higher_is_better,
            }
        ]
    else:
        ranking_jobs = [
            {
                "method_a": method_a,
                "method_b": method_b,
                "deltas": list(deltas),
                "metric_name": default_ranking_metric,
                "higher_is_better": default_higher_is_better,
            }
            for method_a, method_b in parse_claim_pairs(args.claim_pairs, (args.method_a, args.method_b))
        ]

    allowed_metrics = {"objective", "circuit_depth", "two_qubit_count", "swap_count"}
    for job in ranking_jobs:
        method_a = str(job["method_a"])
        method_b = str(job["method_b"])
        if method_a not in method_names or method_b not in method_names:
            raise ValueError(
                f"Unknown claim methods: {method_a}, {method_b}. Available: {sorted(method_names)}"
            )
        if method_a == method_b:
            raise ValueError("Claim pair must compare two different methods.")
        metric_name = str(job.get("metric_name", "objective"))
        if metric_name not in allowed_metrics:
            raise ValueError(
                f"Unsupported ranking metric '{metric_name}'. Use one of: {sorted(allowed_metrics)}"
            )
        dvals = job.get("deltas")
        if not isinstance(dvals, list) or not dvals:
            raise ValueError("Ranking claim job must include non-empty deltas.")
        job["deltas"] = [float(v) for v in dvals]

    ranking_metric_names = sorted({str(job["metric_name"]) for job in ranking_jobs})
    decision_metric_name = "objective" if "objective" in ranking_metric_names else (ranking_metric_names[0] if ranking_metric_names else "objective")
    metrics_needed = list(ranking_metric_names)
    if decision_claims and decision_metric_name not in metrics_needed:
        metrics_needed.append(decision_metric_name)
    for distribution_claim in distribution_claims:
        metric_name = str(distribution_claim.get("metric_name", "objective"))
        if metric_name not in allowed_metrics:
            raise ValueError(
                f"Unsupported distribution metric '{metric_name}'. Use one of: {sorted(allowed_metrics)}"
            )
        method_name = str(distribution_claim.get("method", ""))
        if method_name not in method_names:
            raise ValueError(f"Unknown distribution claim method '{method_name}'. Available: {sorted(method_names)}")
        primary_distance = str(distribution_claim.get("primary_distance", "js")).lower()
        sanity_distance = str(distribution_claim.get("sanity_distance", "tvd")).lower()
        if primary_distance not in {"js", "tvd"} or sanity_distance not in {"js", "tvd"}:
            raise ValueError("Distribution claim distances must be in {'js','tvd'}.")
        epsilon = float(distribution_claim.get("epsilon", 0.2))
        if epsilon < 0.0:
            raise ValueError(f"Distribution claim epsilon must be >= 0, got {epsilon}")
        distribution_claim["epsilon"] = epsilon
        distribution_claim["primary_distance"] = primary_distance
        distribution_claim["sanity_distance"] = sanity_distance
        distribution_claim["metric_name"] = metric_name
        if metric_name not in metrics_needed:
            metrics_needed.append(metric_name)

    sampling_policy = SamplingPolicy(
        mode=args.sampling_mode,
        sample_size=args.sample_size if args.sampling_mode == "random_k" else args.max_sample_size if args.sampling_mode == "adaptive_ci" else None,
        seed=args.sample_seed,
        target_ci_width=args.target_ci_width if args.sampling_mode == "adaptive_ci" else None,
        max_sample_size=args.max_sample_size if args.sampling_mode == "adaptive_ci" else None,
        min_sample_size=args.min_sample_size,
        step_size=args.step_size,
    )
    runtime_meta = collect_runtime_metadata(
        include_dependencies=not bool(args.replay_trace),
        include_environment_flags=not bool(args.replay_trace),
        include_git=not bool(args.replay_trace),
    )
    runtime_context: Mapping[str, Any] = {
        "python_version": runtime_meta.get("python_version"),
        "git_commit": runtime_meta.get("git_commit"),
        "qiskit_version": (runtime_meta.get("dependencies", {}) or {}).get("qiskit"),
    }
    trace_path = Path(args.trace_out) if args.trace_out else (out_dir / "trace.jsonl")
    events_path = Path(args.events_out) if args.events_out else None
    cache_path = Path(args.cache_db) if args.cache_db else None

    device_profile = parse_device_profile(spec_payload.get("device_profile") if isinstance(spec_payload, dict) else None)
    resolved_device = resolve_device_profile(device_profile)
    noise_model_mode = parse_noise_model_mode(spec_payload.get("backend") if isinstance(spec_payload, dict) else None)

    all_rows: list[tuple[str, str, ScoreRow]] = []
    rows_by_space_metric_graph: dict[str, dict[str, dict[str, list[ScoreRow]]]] = {}
    sampling_by_space: dict[str, dict[str, object]] = {}
    baseline_by_space: dict[str, dict[str, int | str | None]] = {}
    baseline_key_by_space: dict[str, tuple[int, int, str | None, int, int | None]] = {}
    sampled_configs_by_space: dict[str, list[PerturbationConfig]] = {}

    if args.replay_trace:
        replay_path = Path(args.replay_trace)
        all_rows, rows_by_space_metric_graph, keys_by_space = load_rows_from_trace(replay_path)
        if not all_rows:
            raise ValueError(f"Replay trace has no rows: {replay_path}")
        replay_suites = sorted({suite_token for suite_token, _, _ in all_rows})
        if replay_suites:
            suite_name = replay_suites[0]
        selected_spaces = sorted(rows_by_space_metric_graph.keys())
        sampling_policy = SamplingPolicy(mode="full_factorial", sample_size=None, seed=args.sample_seed)
        trace_path = replay_path
        for space_name in selected_spaces:
            keys = keys_by_space.get(space_name, set())
            if not keys:
                continue
            try:
                default_space = make_space(space_name)
                baseline_cfg_default, _, baseline_key_default = build_baseline_config(default_space)
                if baseline_key_default in keys:
                    baseline_cfg = baseline_cfg_default
                    baseline_key = baseline_key_default
                else:
                    baseline_cfg, baseline_key = baseline_from_keys(keys)
            except Exception:
                baseline_cfg, baseline_key = baseline_from_keys(keys)
            sampled_configs = [config_from_key(k) for k in sorted(keys, key=key_sort_value)]
            baseline_by_space[space_name] = baseline_cfg
            baseline_key_by_space[space_name] = baseline_key
            sampled_configs_by_space[space_name] = sampled_configs
            sampling_by_space[space_name] = {
                "suite": suite_name,
                "space_preset": space_name,
                "mode": "replay_trace",
                "sample_size": None,
                "seed": args.sample_seed,
                "target_ci_width": None,
                "max_sample_size": None,
                "min_sample_size": None,
                "step_size": None,
                "sampled_configurations_with_baseline": len(sampled_configs),
                "perturbation_space_size": len(sampled_configs),
                "replay_trace": str(replay_path),
            }
    else:
        runner = MatrixRunner(
            backend=QiskitAerRunner(
                engine=args.backend_engine,
                spot_check_noise=args.spot_check_noise,
                one_qubit_error=args.one_qubit_error,
                two_qubit_error=args.two_qubit_error,
            )
        )
        trace_index = TraceIndex()
        cache_store: CacheStore | None = CacheStore(cache_path) if cache_path is not None else None
        event_logger = make_event_logger(events_path) if events_path is not None else None

        try:
            for space_name in selected_spaces:
                space = make_space(space_name)
                baseline_cfg, baseline_pc, baseline_key = build_baseline_config(space)
                sampled_configs = sample_configs(space, sampling_policy, use_operator_shim=args.use_operator_shim)
                sampled_configs = ensure_config_included(sampled_configs, baseline_pc)

                by_metric_rows: dict[str, dict[str, list[ScoreRow]]] = {}
                for metric_name in metrics_needed or ["objective"]:
                    rows_by_graph: dict[str, list[ScoreRow]] = {}
                    for inst in suite:
                        task = BoundTask(task_plugin, inst)
                        coupling_map = build_coupling_map(task.infer_num_qubits(methods))
                        rows = runner.run(
                            task=task,
                            methods=methods,
                            space=space,
                            configs=sampled_configs,
                            coupling_map=coupling_map,
                            metric_name=metric_name,
                            device_profile=resolved_device.profile,
                            device_backend=resolved_device.backend,
                            noise_model_mode=noise_model_mode,
                            device_snapshot_fingerprint=resolved_device.snapshot_fingerprint,
                            device_snapshot_summary=resolved_device.snapshot,
                            store_counts=bool(decision_claims or distribution_claims),
                            cache_store=cache_store,
                            runtime_context=runtime_context,
                            event_logger=event_logger,
                        )
                        rows_by_graph[inst.instance_id] = rows
                        all_rows.extend((suite_name, space_name, row) for row in rows)
                        trace_index.extend(
                            [
                                TraceRecord.from_score_row(suite=suite_name, space_preset=space_name, row=row)
                                for row in rows
                            ]
                        )
                    by_metric_rows[metric_name] = rows_by_graph

                rows_by_space_metric_graph[space_name] = by_metric_rows
                baseline_by_space[space_name] = baseline_cfg
                baseline_key_by_space[space_name] = baseline_key
                sampled_configs_by_space[space_name] = sampled_configs
                sampling_by_space[space_name] = {
                    "suite": suite_name,
                    "space_preset": space_name,
                    "mode": sampling_policy.mode,
                    "sample_size": sampling_policy.sample_size,
                    "seed": sampling_policy.seed,
                    "target_ci_width": sampling_policy.target_ci_width,
                    "max_sample_size": sampling_policy.max_sample_size,
                    "min_sample_size": sampling_policy.min_sample_size,
                    "step_size": sampling_policy.step_size,
                    "sampled_configurations_with_baseline": len(sampled_configs),
                    "perturbation_space_size": space.size(),
                    "operator_shim": bool(args.use_operator_shim),
                }
        finally:
            if cache_store is not None:
                cache_store.close()

        trace_index.save_jsonl(trace_path)

    artifact_manifest = ArtifactManifest(
        trace_jsonl=str(trace_path.resolve()),
        events_jsonl=str(events_path.resolve()) if events_path is not None else None,
        cache_db=str(cache_path.resolve()) if cache_path is not None else None,
    )

    experiments: list[dict[str, object]] = []
    comparative_rows: list[dict[str, object]] = []

    for space_name in selected_spaces:
        baseline_key = baseline_key_by_space[space_name]

        for ranking_job in ranking_jobs:
            method_a = str(ranking_job["method_a"])
            method_b = str(ranking_job["method_b"])
            claim_deltas = [float(v) for v in ranking_job.get("deltas", [])]
            metric_name = str(ranking_job.get("metric_name", "objective"))
            higher_is_better = _as_bool(ranking_job.get("higher_is_better"), True)
            direction = HigherIsBetter.YES if higher_is_better else HigherIsBetter.NO
            space_rows = rows_by_space_metric_graph[space_name][metric_name]
            per_graph_summary: dict[str, dict[str, object]] = {}
            by_delta_flip: dict[float, list[float]] = defaultdict(list)
            by_delta_decision: dict[float, list[str]] = defaultdict(list)
            by_delta_stability_successes: dict[float, int] = defaultdict(int)
            by_delta_stability_totals: dict[float, int] = defaultdict(int)
            by_delta_claim_holds_successes: dict[float, int] = defaultdict(int)
            by_delta_claim_holds_totals: dict[float, int] = defaultdict(int)
            by_delta_baseline_holds_successes: dict[float, int] = defaultdict(int)
            by_delta_baseline_holds_totals: dict[float, int] = defaultdict(int)
            paired_scores_by_graph: dict[str, dict[tuple[int, int, str | None, int, int | None], tuple[float, float]]] = {}
            method_scores_by_graph: dict[str, dict[tuple[int, int, str | None, int, int | None], dict[str, float]]] = {}
            robustness_observations_by_delta: dict[str, list[dict[str, object]]] = defaultdict(list)
            stratified_counts_by_delta: dict[str, dict[tuple[tuple[str, object], ...], dict[str, object]]] = defaultdict(
                lambda: defaultdict(
                    lambda: {
                        "total": 0,
                        "flips": 0,
                        "instance_ids": set(),
                        "conditions": {},
                    }
                )
            )
            strata_dimension_names: set[str] = set()
            for graph_id, graph_rows in space_rows.items():
                paired_scores_by_graph[graph_id] = collect_paired_scores(graph_rows, method_a, method_b)

            adaptive_info: dict[str, object] = {"enabled": False}
            allowed_keys: set[tuple[int, int, str | None, int, int | None]] | None = None
            if sampling_policy.mode == "adaptive_ci":
                allowed_keys, adaptive_info = select_adaptive_keys(
                    sampled_configs=sampled_configs_by_space[space_name],
                    paired_scores_by_graph=paired_scores_by_graph,
                    method_a=method_a,
                    method_b=method_b,
                    deltas=claim_deltas,
                    baseline_key=baseline_key,
                    confidence_level=args.confidence_level,
                    target_ci_width=float(sampling_policy.target_ci_width or 0.02),
                    min_sample_size=max(1, int(sampling_policy.min_sample_size)),
                    step_size=max(1, int(sampling_policy.step_size)),
                )

            for graph_id, graph_rows in space_rows.items():
                eval_rows = graph_rows if allowed_keys is None else filter_rows_by_keys(graph_rows, allowed_keys)
                graph_eval = evaluate_claim_on_rows(
                    eval_rows,
                    method_a=method_a,
                    method_b=method_b,
                    deltas=claim_deltas,
                    higher_is_better=higher_is_better,
                    baseline_key=baseline_key,
                    stability_threshold=args.stability_threshold,
                    confidence_level=args.confidence_level,
                    top_k_unstable=args.top_k_unstable,
                )
                method_scores_by_graph[graph_id] = build_method_scores_by_key(eval_rows)
                paired_scores_by_graph[graph_id] = graph_eval["paired_scores"]
                instance = suite_by_id.get(graph_id)
                instance_strata = _derive_instance_strata(
                    task_kind=task_kind,
                    graph_id=graph_id,
                    instance=instance,
                    graph_rows=eval_rows,
                    method_name=method_a,
                    baseline_key=baseline_key,
                )
                strata_dimension_names.update(instance_strata.keys())
                strata_key = tuple(sorted(instance_strata.items(), key=lambda kv: kv[0]))
                per_graph_summary[graph_id] = {
                    "sampled_configurations": graph_eval["sampled_configurations"],
                    "delta_sweep": graph_eval["delta_sweep"],
                    "factor_attribution": graph_eval["factor_attribution"],
                    "lockdown_recommendation": graph_eval["lockdown_recommendation"],
                    "conditional_stability": graph_eval["conditional_stability"],
                }
                for delta_key, obs_rows in graph_eval["flip_observations_by_delta"].items():
                    for obs_row in obs_rows:
                        robustness_observations_by_delta[delta_key].append(
                            {
                                **obs_row,
                                "graph_id": graph_id,
                            }
                        )
                for delta in claim_deltas:
                    by_delta_flip[delta].extend(graph_eval["by_delta_flip"][delta])
                    by_delta_decision[delta].extend(graph_eval["by_delta_decision"][delta])
                for record in graph_eval["delta_sweep"]:
                    delta_key = float(record["delta"])
                    by_delta_stability_successes[delta_key] += int(record["total"]) - int(record["flips"])
                    by_delta_stability_totals[delta_key] += int(record["total"])
                    by_delta_claim_holds_successes[delta_key] += int(record["claim_holds_count"])
                    by_delta_claim_holds_totals[delta_key] += int(record["claim_total_count"])
                    by_delta_baseline_holds_successes[delta_key] += 1 if bool(record["baseline_holds"]) else 0
                    by_delta_baseline_holds_totals[delta_key] += 1
                    dkey = str(record["delta"])
                    strat_slot = stratified_counts_by_delta[dkey][strata_key]
                    strat_slot["total"] += int(record["total"])
                    strat_slot["flips"] += int(record["flips"])
                    strat_slot["instance_ids"].add(graph_id)
                    strat_slot["conditions"] = instance_strata

            all_selected_rows = [
                row
                for graph_rows in space_rows.values()
                for row in (graph_rows if allowed_keys is None else filter_rows_by_keys(graph_rows, allowed_keys))
            ]
            overall_delta = []
            for delta in claim_deltas:
                flips = by_delta_flip[delta]
                decisions = by_delta_decision[delta]
                n = len(flips)
                clustered = estimate_clustered_stability(
                    all_selected_rows,
                    RankingClaim(method_a=method_a, method_b=method_b, delta=delta, direction=direction),
                    baseline_by_space[space_name],
                    stability_threshold=args.stability_threshold,
                    confidence_level=args.confidence_level,
                    n_boot=2000,
                    seed=args.sample_seed,
                )
                holds_estimate = estimate_binomial_rate(
                    successes=by_delta_claim_holds_successes[delta],
                    total=by_delta_claim_holds_totals[delta],
                    confidence=args.confidence_level,
                )
                stability_estimate = estimate_binomial_rate(
                    successes=by_delta_stability_successes[delta],
                    total=by_delta_stability_totals[delta],
                    confidence=args.confidence_level,
                )
                aggregate_decision = conservative_stability_decision(
                    estimate=stability_estimate,
                    stability_threshold=args.stability_threshold,
                ).value
                row = {
                    "delta": delta,
                    "n_instances": len(per_graph_summary),
                    "n_claim_evals": by_delta_stability_totals[delta],
                    "flip_rate_mean": sum(flips) / n if n else 0.0,
                    "flip_rate_max": max(flips) if n else 0.0,
                    "flip_rate_min": min(flips) if n else 0.0,
                    "holds_rate_mean": holds_estimate.rate,
                    "holds_rate_ci_low": holds_estimate.ci_low,
                    "holds_rate_ci_high": holds_estimate.ci_high,
                    "stability_hat": stability_estimate.rate,
                    "stability_ci_low": stability_estimate.ci_low,
                    "stability_ci_high": stability_estimate.ci_high,
                    "decision": aggregate_decision,
                    **clustered,
                    "decision_counts": {
                        "stable": sum(1 for d in decisions if d == "stable"),
                        "unstable": sum(1 for d in decisions if d == "unstable"),
                        "inconclusive": sum(1 for d in decisions if d == "inconclusive"),
                    },
                }
                naive = evaluate_naive_baseline(
                    claim_type="ranking",
                    baseline_holds=bool(
                        by_delta_baseline_holds_totals[delta] > 0
                        and by_delta_baseline_holds_successes[delta] == by_delta_baseline_holds_totals[delta]
                    ),
                    baseline_holds_successes=by_delta_baseline_holds_successes[delta],
                    baseline_holds_total=by_delta_baseline_holds_totals[delta],
                    claimstab_decision=aggregate_decision,
                    stability_ci_low=stability_estimate.ci_low,
                    stability_ci_high=stability_estimate.ci_high,
                    threshold=args.stability_threshold,
                )
                naive_realistic = evaluate_naive_baseline(
                    claim_type="ranking",
                    baseline_holds=bool(
                        by_delta_baseline_holds_totals[delta] > 0
                        and by_delta_baseline_holds_successes[delta] == by_delta_baseline_holds_totals[delta]
                    ),
                    baseline_holds_successes=by_delta_baseline_holds_successes[delta],
                    baseline_holds_total=by_delta_baseline_holds_totals[delta],
                    claimstab_decision=aggregate_decision,
                    stability_ci_low=stability_estimate.ci_low,
                    stability_ci_high=stability_estimate.ci_high,
                    threshold=args.stability_threshold,
                    naive_policy=NAIVE_POLICY_REALISTIC,
                )
                row["naive_baseline"] = naive
                row["naive_baseline_realistic"] = naive_realistic
                overall_delta.append(row)
                comparative_rows.append(
                    {
                        "space_preset": space_name,
                        "claim_pair": f"{method_a}>{method_b}",
                        "claim_type": "ranking",
                        "metric_name": metric_name,
                        "higher_is_better": higher_is_better,
                        **row,
                    }
                )

            diagnostics_summary = aggregate_factor_attribution(
                per_graph_summary=per_graph_summary,
                deltas=claim_deltas,
                top_k=args.top_k_unstable,
            )
            conditional_robustness_summary = build_conditional_robustness_summary(
                observations_by_delta=robustness_observations_by_delta,
                stability_threshold=args.stability_threshold,
                confidence_level=args.confidence_level,
                context_conditions={
                    "space_preset": space_name,
                    "device_mode": resolved_device.profile.mode,
                    "noise_model": noise_model_mode,
                },
            )
            effect_diagnostics_summary = compute_effect_diagnostics(
                observations_by_delta=robustness_observations_by_delta,
                context_conditions={
                    "space_preset": space_name,
                    "device_mode": resolved_device.profile.mode,
                    "noise_model": noise_model_mode,
                },
                top_k=max(3, args.top_k_unstable),
            )
            stratified_stability_by_delta: dict[str, list[dict[str, object]]] = {}
            for delta in claim_deltas:
                dkey = str(delta)
                rows: list[dict[str, object]] = []
                for entry in stratified_counts_by_delta.get(dkey, {}).values():
                    total = int(entry["total"])
                    if total <= 0:
                        continue
                    flips = int(entry["flips"])
                    estimate = estimate_binomial_rate(
                        successes=total - flips,
                        total=total,
                        confidence=args.confidence_level,
                    )
                    decision = conservative_stability_decision(
                        estimate=estimate,
                        stability_threshold=args.stability_threshold,
                    ).value
                    rows.append(
                        {
                            "conditions": dict(entry["conditions"]),
                            "n_instances": len(entry["instance_ids"]),
                            "n_eval": total,
                            "flip_rate": flips / total,
                            "stability_hat": estimate.rate,
                            "stability_ci_low": estimate.ci_low,
                            "stability_ci_high": estimate.ci_high,
                            "decision": decision,
                        }
                    )
                rows.sort(
                    key=lambda row: (
                        str(row["decision"]) == "stable",
                        int(row["n_eval"]),
                        float(row["stability_ci_low"]),
                    ),
                    reverse=True,
                )
                stratified_stability_by_delta[dkey] = rows

            stability_vs_cost_by_delta: dict[str, list[dict[str, object]]] = {}
            minimum_shots_by_delta: dict[str, int | None] = {}
            all_space_rows = all_selected_rows
            for delta in claim_deltas:
                shot_rows = compute_stability_vs_shots(
                    all_space_rows,
                    claim_spec={
                        "method_a": method_a,
                        "method_b": method_b,
                        "delta": delta,
                        "higher_is_better": higher_is_better,
                    },
                    baseline_config=baseline_by_space[space_name],
                    threshold=args.stability_threshold,
                    confidence_level=args.confidence_level,
                )
                stability_vs_cost_by_delta[str(delta)] = shot_rows
                minimum_shots_by_delta[str(delta)] = minimum_shots_for_stable(shot_rows)

            graph_for_aux = sorted(method_scores_by_graph.keys())[0] if method_scores_by_graph else None
            auxiliary_claims = {}
            if graph_for_aux is not None:
                auxiliary_claims = {
                    "graph_id": graph_for_aux,
                    **evaluate_auxiliary_claim_examples(
                        method_scores_by_key=method_scores_by_graph[graph_for_aux],
                        baseline_key=baseline_key,
                        stability_threshold=args.stability_threshold,
                        confidence_level=args.confidence_level,
                    ),
                }

            claim_payload = {
                "type": "ranking",
                "method_a": method_a,
                "method_b": method_b,
                "deltas": claim_deltas,
                "metric_name": metric_name,
                "higher_is_better": higher_is_better,
                "delta_interpretation": "delta is a practical significance threshold; increasing delta makes the claim stricter and may change both holds rate and stability.",
            }

            experiment = {
                "experiment_id": f"{space_name}:{method_a}>{method_b}",
                "claim": claim_payload,
                "baseline": baseline_by_space[space_name],
                "stability_rule": {
                    "threshold": args.stability_threshold,
                    "confidence_level": args.confidence_level,
                    "decision": "stable iff CI lower bound >= threshold",
                },
                "sampling": sampling_by_space[space_name],
                "backend": {
                    "engine": args.backend_engine,
                    "noise_model": noise_model_mode,
                    "spot_check_noise": args.spot_check_noise,
                    "one_qubit_error": args.one_qubit_error if args.spot_check_noise else None,
                    "two_qubit_error": args.two_qubit_error if args.spot_check_noise else None,
                },
                "device_profile": {
                    "enabled": resolved_device.profile.enabled,
                    "provider": resolved_device.profile.provider,
                    "name": resolved_device.profile.name,
                    "mode": resolved_device.profile.mode,
                    "snapshot_fingerprint": resolved_device.snapshot_fingerprint,
                    "snapshot": resolved_device.snapshot,
                },
                "per_graph": per_graph_summary,
                "overall": {
                    "graphs": len(per_graph_summary),
                    "delta_sweep": overall_delta,
                    "diagnostics": diagnostics_summary,
                    "conditional_robustness": conditional_robustness_summary,
                    "stratified_stability": {
                        "strata_dimensions": sorted(strata_dimension_names),
                        "by_delta": stratified_stability_by_delta,
                    },
                    "effect_diagnostics": effect_diagnostics_summary,
                    "stability_vs_cost": {
                        "cost_metric": "shots",
                        "by_delta": stability_vs_cost_by_delta,
                        "minimum_shots_for_stable": minimum_shots_by_delta,
                    },
                },
                "auxiliary_claims": auxiliary_claims,
                "evidence": build_evidence_ref(
                    suite_name=suite_name,
                    space_name=space_name,
                    metric_name=metric_name,
                    claim=claim_payload,
                    artifact_manifest=artifact_manifest,
                ),
            }
            if adaptive_info.get("enabled"):
                experiment["sampling"] = {
                    **dict(sampling_by_space[space_name]),
                    "adaptive_stopping": adaptive_info,
                }
            experiments.append(experiment)

        decision_space_rows = rows_by_space_metric_graph[space_name][decision_metric_name]
        for decision_claim in decision_claims:
            method = str(decision_claim["method"])
            top_k = int(decision_claim.get("top_k", 1))
            label_meta_key = str(decision_claim.get("label_meta_key", "target_label"))
            fixed_label = decision_claim.get("label")
            per_graph_summary: dict[str, dict[str, object]] = {}
            accepted_total = 0
            eval_total = 0
            all_failures: list[dict[str, object]] = []

            all_selected_rows = [row for graph_rows in decision_space_rows.values() for row in graph_rows]
            for graph_id, graph_rows in decision_space_rows.items():
                inst = suite_by_id.get(graph_id)
                label = fixed_label
                if label is None and inst is not None and isinstance(inst.meta, dict):
                    label = inst.meta.get(label_meta_key)
                if not isinstance(label, str) or not label:
                    continue
                graph_eval = evaluate_decision_claim_on_rows(
                    graph_rows,
                    method=method,
                    top_k=top_k,
                    instance_target_label=label,
                    stability_threshold=args.stability_threshold,
                    confidence_level=args.confidence_level,
                )
                per_graph_summary[graph_id] = graph_eval
                accepted_total += int(graph_eval["accepted"])
                eval_total += int(graph_eval["total"])
                for fail in graph_eval.get("top_failures", []):
                    fail_copy = dict(fail)
                    fail_copy["graph_id"] = graph_id
                    all_failures.append(fail_copy)

            stability_estimate = estimate_binomial_rate(
                successes=accepted_total,
                total=eval_total,
                confidence=args.confidence_level,
            )
            aggregate_decision = conservative_stability_decision(
                estimate=stability_estimate,
                stability_threshold=args.stability_threshold,
            ).value

            summary_row = {
                "delta": None,
                "n_instances": len(per_graph_summary),
                "n_claim_evals": eval_total,
                "flip_rate_mean": 1.0 - stability_estimate.rate,
                "flip_rate_max": 1.0 - stability_estimate.rate,
                "flip_rate_min": 1.0 - stability_estimate.rate,
                "holds_rate_mean": stability_estimate.rate,
                "holds_rate_ci_low": stability_estimate.ci_low,
                "holds_rate_ci_high": stability_estimate.ci_high,
                "stability_hat": stability_estimate.rate,
                "stability_ci_low": stability_estimate.ci_low,
                "stability_ci_high": stability_estimate.ci_high,
                "decision": aggregate_decision,
                "decision_counts": {
                    "stable": 1 if aggregate_decision == "stable" else 0,
                    "unstable": 1 if aggregate_decision == "unstable" else 0,
                    "inconclusive": 1 if aggregate_decision == "inconclusive" else 0,
                },
            }
            naive = evaluate_naive_baseline(
                claim_type="decision",
                baseline_holds=bool(accepted_total == eval_total and eval_total > 0),
                baseline_holds_successes=accepted_total,
                baseline_holds_total=eval_total,
                claimstab_decision=aggregate_decision,
                stability_ci_low=stability_estimate.ci_low,
                stability_ci_high=stability_estimate.ci_high,
                threshold=args.stability_threshold,
            )
            naive_realistic = evaluate_naive_baseline(
                claim_type="decision",
                baseline_holds=bool(accepted_total == eval_total and eval_total > 0),
                baseline_holds_successes=accepted_total,
                baseline_holds_total=eval_total,
                claimstab_decision=aggregate_decision,
                stability_ci_low=stability_estimate.ci_low,
                stability_ci_high=stability_estimate.ci_high,
                threshold=args.stability_threshold,
                naive_policy=NAIVE_POLICY_REALISTIC,
            )
            summary_row["naive_baseline"] = naive
            summary_row["naive_baseline_realistic"] = naive_realistic

            comparative_rows.append(
                {
                    "space_preset": space_name,
                    "claim_pair": f"{method}:top_k={top_k}",
                    "claim_type": "decision",
                    "metric_name": decision_metric_name,
                    **summary_row,
                }
            )

            decision_claim_payload = {
                "type": "decision",
                "method": method,
                "top_k": top_k,
                "label_meta_key": label_meta_key,
                "metric_name": decision_metric_name,
            }

            experiments.append(
                {
                    "experiment_id": f"{space_name}:{method}:decision_top{top_k}",
                    "claim": decision_claim_payload,
                    "baseline": baseline_by_space[space_name],
                    "stability_rule": {
                        "threshold": args.stability_threshold,
                        "confidence_level": args.confidence_level,
                        "decision": "stable iff CI lower bound >= threshold",
                    },
                    "sampling": sampling_by_space[space_name],
                    "backend": {
                        "engine": args.backend_engine,
                        "noise_model": noise_model_mode,
                        "spot_check_noise": args.spot_check_noise,
                    },
                    "device_profile": {
                        "enabled": resolved_device.profile.enabled,
                        "provider": resolved_device.profile.provider,
                        "name": resolved_device.profile.name,
                        "mode": resolved_device.profile.mode,
                        "snapshot_fingerprint": resolved_device.snapshot_fingerprint,
                        "snapshot": resolved_device.snapshot,
                    },
                    "per_graph": per_graph_summary,
                    "overall": {
                        "graphs": len(per_graph_summary),
                        "delta_sweep": [summary_row],
                        "decision_failures": all_failures[:12],
                    },
                    "naive_baseline": naive,
                    "evidence": build_evidence_ref(
                        suite_name=suite_name,
                        space_name=space_name,
                        metric_name=decision_metric_name,
                        claim=decision_claim_payload,
                        artifact_manifest=artifact_manifest,
                    ),
                }
            )

        for distribution_claim in distribution_claims:
            method = str(distribution_claim.get("method"))
            epsilon = float(distribution_claim.get("epsilon", 0.2))
            primary_distance = str(distribution_claim.get("primary_distance", "js")).lower()
            sanity_distance = str(distribution_claim.get("sanity_distance", "tvd")).lower()
            reference_shots = distribution_claim.get("reference_shots", "max")
            metric_name = str(distribution_claim.get("metric_name", "objective"))

            distribution_space_rows = rows_by_space_metric_graph[space_name][metric_name]
            per_graph_summary: dict[str, dict[str, object]] = {}
            accepted_total = 0
            eval_total = 0
            flip_rates: list[float] = []
            decisions: list[str] = []
            all_violations: list[dict[str, object]] = []
            reference_shots_used: list[int] = []

            for graph_id, graph_rows in distribution_space_rows.items():
                graph_eval = evaluate_distribution_claim_on_rows(
                    graph_rows,
                    method=method,
                    baseline_key=baseline_key,
                    epsilon=epsilon,
                    primary_distance=primary_distance,
                    sanity_distance=sanity_distance,
                    reference_shots=reference_shots,
                    stability_threshold=args.stability_threshold,
                    confidence_level=args.confidence_level,
                )
                per_graph_summary[graph_id] = graph_eval
                accepted_total += int(graph_eval.get("accepted", 0))
                eval_total += int(graph_eval.get("total", 0))
                flip_rates.append(float(graph_eval.get("flip_rate", 0.0)))
                decisions.append(str(graph_eval.get("decision", "inconclusive")))
                ref_shots_used = graph_eval.get("reference_shots")
                if isinstance(ref_shots_used, int):
                    reference_shots_used.append(ref_shots_used)
                for violation in graph_eval.get("top_violations", []):
                    if not isinstance(violation, dict):
                        continue
                    all_violations.append({"graph_id": graph_id, **violation})

            stability_estimate = estimate_binomial_rate(
                successes=accepted_total,
                total=eval_total,
                confidence=args.confidence_level,
            )
            aggregate_decision = conservative_stability_decision(
                estimate=stability_estimate,
                stability_threshold=args.stability_threshold,
            ).value
            all_violations.sort(key=lambda row: float(row.get("primary_value", 0.0)), reverse=True)

            summary_row = {
                "delta": None,
                "n_instances": len(per_graph_summary),
                "n_claim_evals": eval_total,
                "flip_rate_mean": (sum(flip_rates) / len(flip_rates)) if flip_rates else 0.0,
                "flip_rate_max": max(flip_rates) if flip_rates else 0.0,
                "flip_rate_min": min(flip_rates) if flip_rates else 0.0,
                "holds_rate_mean": stability_estimate.rate,
                "holds_rate_ci_low": stability_estimate.ci_low,
                "holds_rate_ci_high": stability_estimate.ci_high,
                "stability_hat": stability_estimate.rate,
                "stability_ci_low": stability_estimate.ci_low,
                "stability_ci_high": stability_estimate.ci_high,
                "decision": aggregate_decision,
                "epsilon": epsilon,
                "primary_distance": primary_distance,
                "sanity_distance": sanity_distance,
                "reference_shots": (max(reference_shots_used) if reference_shots_used else None),
                "decision_counts": {
                    "stable": sum(1 for d in decisions if d == "stable"),
                    "unstable": sum(1 for d in decisions if d == "unstable"),
                    "inconclusive": sum(1 for d in decisions if d == "inconclusive"),
                },
            }
            naive = evaluate_naive_baseline(
                claim_type="distribution",
                baseline_holds=bool(accepted_total == eval_total and eval_total > 0),
                baseline_holds_successes=accepted_total,
                baseline_holds_total=eval_total,
                claimstab_decision=aggregate_decision,
                stability_ci_low=stability_estimate.ci_low,
                stability_ci_high=stability_estimate.ci_high,
                threshold=args.stability_threshold,
            )
            naive_realistic = evaluate_naive_baseline(
                claim_type="distribution",
                baseline_holds=bool(accepted_total == eval_total and eval_total > 0),
                baseline_holds_successes=accepted_total,
                baseline_holds_total=eval_total,
                claimstab_decision=aggregate_decision,
                stability_ci_low=stability_estimate.ci_low,
                stability_ci_high=stability_estimate.ci_high,
                threshold=args.stability_threshold,
                naive_policy=NAIVE_POLICY_REALISTIC,
            )
            summary_row["naive_baseline"] = naive
            summary_row["naive_baseline_realistic"] = naive_realistic

            comparative_rows.append(
                {
                    "space_preset": space_name,
                    "claim_pair": f"{method}:dist<={epsilon}",
                    "claim_type": "distribution",
                    "metric_name": metric_name,
                    **summary_row,
                }
            )

            distribution_claim_payload = {
                "type": "distribution",
                "method": method,
                "epsilon": epsilon,
                "primary_distance": primary_distance,
                "sanity_distance": sanity_distance,
                "reference_shots": reference_shots,
                "metric_name": metric_name,
            }
            experiments.append(
                {
                    "experiment_id": f"{space_name}:{method}:distribution",
                    "claim": distribution_claim_payload,
                    "baseline": baseline_by_space[space_name],
                    "stability_rule": {
                        "threshold": args.stability_threshold,
                        "confidence_level": args.confidence_level,
                        "decision": "stable iff CI lower bound >= threshold",
                    },
                    "sampling": sampling_by_space[space_name],
                    "backend": {
                        "engine": args.backend_engine,
                        "noise_model": noise_model_mode,
                        "spot_check_noise": args.spot_check_noise,
                    },
                    "device_profile": {
                        "enabled": resolved_device.profile.enabled,
                        "provider": resolved_device.profile.provider,
                        "name": resolved_device.profile.name,
                        "mode": resolved_device.profile.mode,
                        "snapshot_fingerprint": resolved_device.snapshot_fingerprint,
                        "snapshot": resolved_device.snapshot,
                    },
                    "per_graph": per_graph_summary,
                    "overall": {
                        "graphs": len(per_graph_summary),
                        "delta_sweep": [summary_row],
                        "distribution_violations": all_violations[:12],
                    },
                    "naive_baseline": naive,
                    "evidence": build_evidence_ref(
                        suite_name=suite_name,
                        space_name=space_name,
                        metric_name=metric_name,
                        claim=distribution_claim_payload,
                        artifact_manifest=artifact_manifest,
                    ),
                }
            )

    write_scores_csv(all_rows, out_csv)

    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        evidence = exp.get("evidence")
        if not isinstance(evidence, dict):
            continue
        evidence["cep"] = build_experiment_cep_record(
            experiment=exp,
            runtime_meta=runtime_meta,
            evidence=evidence,
        )

    meta_deltas = (
        sorted({float(delta) for job in ranking_jobs for delta in job.get("deltas", [])})
        if ranking_jobs
        else list(deltas)
    )
    robustness_map_artifact = build_robustness_map_artifact(experiments)
    payload = {
        "meta": {
            "suite": suite_name,
            "task": task_kind,
            "deltas": meta_deltas,
            "methods_available": sorted(method_names),
            "generated_by": "claimstab/pipelines/claim_stability_app.py",
            "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
            "runtime": runtime_meta,
            "artifacts": {
                "trace_jsonl": artifact_manifest.trace_jsonl,
                "events_jsonl": artifact_manifest.events_jsonl,
                "cache_db": artifact_manifest.cache_db,
                "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                "robustness_map_json": str((out_dir / "robustness_map.json").resolve()),
            },
            "evidence_chain": {
                **build_cep_protocol_meta(
                    lookup_fields=EVIDENCE_LOOKUP_FIELDS,
                    decision_provenance=(
                        "each experiment includes evidence.trace_query + evidence.cep blocks "
                        "that can be matched against trace records for reproducible decision provenance"
                    ),
                ),
            },
        },
        "device_profile": {
            "enabled": resolved_device.profile.enabled,
            "provider": resolved_device.profile.provider,
            "name": resolved_device.profile.name,
            "mode": resolved_device.profile.mode,
            "snapshot_fingerprint": resolved_device.snapshot_fingerprint,
            "snapshot": resolved_device.snapshot,
        },
        "batch": {
            "space_presets": selected_spaces,
            "claim_pairs": [
                f"{job['method_a']}>{job['method_b']}[{job['metric_name']}]"
                for job in ranking_jobs
            ],
            "ranking_claims": ranking_jobs,
            "metrics_evaluated": metrics_needed or ["objective"],
            "decision_claims": decision_claims,
            "num_experiments": len(experiments),
        },
        "experiments": experiments,
        "comparative": {
            "space_claim_delta": comparative_rows,
        },
    }
    if isinstance(spec_payload, dict):
        m = spec_payload.get("meta")
        if isinstance(m, dict) and isinstance(m.get("deprecated_field_used"), list):
            payload["meta"]["deprecated_field_used"] = [str(x) for x in m.get("deprecated_field_used", [])]

    rq_summary = build_rq_summary(payload, debug_attribution=args.debug_attribution)
    payload["rq_summary"] = rq_summary

    if len(experiments) == 1:
        exp = experiments[0]
        payload["claim"] = exp["claim"]
        payload["baseline"] = exp["baseline"]
        payload["stability_rule"] = exp["stability_rule"]
        payload["sampling"] = exp["sampling"]
        payload["backend_engine"] = exp["backend"]["engine"]
        payload["perturbation_space_size"] = exp["sampling"]["perturbation_space_size"]
        payload["per_graph"] = exp["per_graph"]
        payload["overall"] = exp["overall"]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out_dir / "robustness_map.json").write_text(json.dumps(robustness_map_artifact, indent=2), encoding="utf-8")
    (out_dir / "rq_summary.json").write_text(json.dumps(rq_summary, indent=2), encoding="utf-8")

    print("Wrote:")
    print(" ", out_csv.resolve())
    print(" ", out_json.resolve())
    print(" ", (out_dir / "robustness_map.json").resolve())
    print("Batch:", payload["batch"])


if __name__ == "__main__":
    main()
