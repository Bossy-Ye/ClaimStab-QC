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
    ci_width,
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
from claimstab.pipelines.planning import resolve_main_plan
from claimstab.pipelines.main_execution import execute_main_plan
from claimstab.pipelines.main_aggregate_emit import build_main_outputs, write_main_outputs
from claimstab.pipelines.runner import (
    BoundTask as _BoundTask,
    build_coupling_map as _build_coupling_map,
    filter_rows_by_keys as _filter_rows_by_keys,
    select_adaptive_keys as _select_adaptive_keys,
    select_adaptive_keys_with_width_evaluator as _select_adaptive_keys_with_width_evaluator,
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


def select_adaptive_keys_with_width_evaluator(
    *,
    sampled_configs: list[PerturbationConfig],
    baseline_key: tuple[int, int, str | None, int, int | None],
    evaluate_ci_width_for_keys: Callable[[set[tuple[int, int, str | None, int, int | None]]], float],
    target_ci_width: float,
    min_sample_size: int,
    step_size: int,
) -> tuple[set[tuple[int, int, str | None, int, int | None]], dict[str, object]]:
    return _select_adaptive_keys_with_width_evaluator(
        sampled_configs=sampled_configs,
        baseline_key=baseline_key,
        evaluate_ci_width_for_keys=evaluate_ci_width_for_keys,
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
    plan = resolve_main_plan(
        parse_args(),
        parse_deltas_fn=parse_deltas,
        parse_csv_tokens_fn=parse_csv_tokens,
        canonical_space_name_fn=canonical_space_name,
        canonical_suite_name_fn=canonical_suite_name,
        try_load_spec_fn=try_load_spec,
        parse_claim_pairs_fn=parse_claim_pairs,
        parse_ranking_claims_from_spec_fn=parse_ranking_claims_from_spec,
        parse_decision_claims_from_spec_fn=parse_decision_claims_from_spec,
        parse_distribution_claims_from_spec_fn=parse_distribution_claims_from_spec,
        has_explicit_claims_fn=has_explicit_claims,
        as_bool_fn=_as_bool,
    )
    args = plan.args
    spec_payload = plan.spec_payload
    deltas = plan.deltas
    suite_name = plan.suite_name
    task_kind = plan.task_kind
    task_plugin = plan.task_plugin
    suite = plan.suite
    suite_by_id = plan.suite_by_id
    methods = plan.methods
    method_names = plan.method_names
    selected_spaces = plan.selected_spaces
    ranking_jobs = plan.ranking_jobs
    decision_claims = plan.decision_claims
    distribution_claims = plan.distribution_claims
    sampling_policy = plan.sampling_policy
    metrics_needed = plan.metrics_needed
    decision_metric_name = plan.decision_metric_name
    runtime_meta = plan.runtime_meta
    runtime_context = plan.runtime_context
    out_dir = plan.out_paths.out_dir
    out_csv = plan.out_paths.out_csv
    out_json = plan.out_paths.out_json
    trace_path = plan.out_paths.trace_path
    events_path = plan.out_paths.events_path
    cache_path = plan.out_paths.cache_path
    resolved_device = plan.resolved_device
    noise_model_mode = plan.noise_model_mode

    execution_result = execute_main_plan(plan)
    output_bundle = build_main_outputs(plan, execution_result)
    write_main_outputs(output_bundle, plan, execution_result)


if __name__ == "__main__":
    main()
