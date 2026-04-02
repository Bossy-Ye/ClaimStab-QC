from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

from claimstab.baselines.naive import NAIVE_POLICY_REALISTIC, evaluate_naive_baseline
from claimstab.cache.store import CacheStore
from claimstab.claims.diagnostics import (
    build_conditional_robustness_summary,
    compute_effect_diagnostics,
    compute_stability_vs_shots,
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
from claimstab.core import ArtifactManifest, TraceIndex, TraceRecord
from claimstab.pipelines.aggregate import aggregate_factor_attribution, build_method_scores_by_key
from claimstab.pipelines.common import (
    PerturbationKey,
    baseline_from_keys,
    build_baseline_config,
    config_from_key,
    key_sort_value,
    load_rows_from_trace_by_space,
    make_event_logger,
    make_space as _make_space,
)
from claimstab.pipelines.evaluate import (
    derive_instance_strata as _derive_instance_strata_impl,
    evaluate_auxiliary_claim_examples,
    evaluate_claim_on_rows,
    evaluate_decision_claim_on_rows,
    evaluate_distribution_claim_on_rows,
)
from claimstab.pipelines.planning import MainPlan
from claimstab.pipelines.runner import (
    BoundTask,
    build_coupling_map,
    filter_rows_by_keys,
    select_adaptive_keys,
    select_adaptive_keys_with_width_evaluator,
)
from claimstab.perturbations.sampling import SamplingPolicy, ensure_config_included, sample_configs
from claimstab.perturbations.space import PerturbationConfig
from claimstab.runners.matrix_runner import MatrixRunner, ScoreRow
from claimstab.runners.qiskit_aer import QiskitAerRunner


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

ROBUSTNESS_DIMENSION_NAMES = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
    "init_strategy",
    "init_seed",
]


@dataclass
class MainExecutionResult:
    all_rows: list[tuple[str, str, ScoreRow]]
    experiments: list[dict[str, object]]
    comparative_rows: list[dict[str, object]]
    artifact_manifest: ArtifactManifest
    runtime_meta: dict[str, Any]
    suite_name: str
    selected_spaces: list[str]
    practicality: dict[str, Any]


def make_space(
    preset: str,
    *,
    hybrid_init_strategies: list[str] | None = None,
    hybrid_init_seeds: list[int] | None = None,
):
    # Preserve main pipeline's wider combined_light shots for stability-vs-cost.
    space = _make_space(preset, combined_light_shots=[64, 256, 1024])
    if hybrid_init_strategies and hybrid_init_seeds:
        return space.with_hybrid_optimization(
            init_strategies=list(hybrid_init_strategies),
            init_seeds=list(hybrid_init_seeds),
        )
    return space


def _varying_robustness_dimensions(rows: list[ScoreRow]) -> list[str]:
    varying: list[str] = []
    for name in ROBUSTNESS_DIMENSION_NAMES:
        values = {getattr(row, name) for row in rows if getattr(row, name) is not None}
        if len(values) > 1:
            varying.append(name)
    return varying


def build_evidence_ref(
    *,
    suite_name: str,
    space_name: str,
    metric_name: str,
    claim: dict[str, Any],
    artifact_manifest: ArtifactManifest,
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
        "lookup_fields": [str(v) for v in EVIDENCE_LOOKUP_FIELDS],
    }


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


def load_rows_from_trace(
    trace_path: Path,
) -> tuple[
    list[tuple[str, str, ScoreRow]],
    dict[str, dict[str, dict[str, list[ScoreRow]]]],
    dict[str, set[tuple[int, int, str | None, int, int | None]]],
]:
    return load_rows_from_trace_by_space(trace_path)


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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _effective_k_with_baseline(
    sampling_payload: Mapping[str, Any],
    adaptive_info: Mapping[str, Any] | None,
) -> int | None:
    k_used = _as_int(sampling_payload.get("sampled_configurations_with_baseline"), 0)
    if isinstance(adaptive_info, Mapping) and bool(adaptive_info.get("enabled")):
        selected = _as_int(adaptive_info.get("selected_configurations_with_baseline"), 0)
        if selected > 0:
            k_used = selected
    return k_used if k_used > 0 else None


def _decision_reason(
    *,
    ci_low: float,
    ci_high: float,
    threshold: float,
) -> str:
    if ci_low >= threshold:
        return "ci_low_meets_threshold"
    if ci_high < threshold:
        return "ci_high_below_threshold"
    return "ci_overlaps_threshold"


def _build_decision_explanation(
    *,
    estimate: float,
    ci_low: float,
    ci_high: float,
    threshold: float,
    decision: str,
) -> dict[str, Any]:
    return {
        "threshold": threshold,
        "estimate": estimate,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "decision": decision,
        "reason": _decision_reason(ci_low=ci_low, ci_high=ci_high, threshold=threshold),
    }


def _build_inconclusive_reason(
    *,
    decision: str,
    ci_low: float,
    ci_high: float,
    threshold: float,
    adaptive_enabled: bool,
    stop_reason: str | None,
    n_claim_evals: int,
) -> str | None:
    if decision != "inconclusive":
        return None
    if n_claim_evals <= 0 or stop_reason == "no_candidate_configs":
        return "no_candidate_configs"
    if adaptive_enabled and stop_reason == "max_budget_reached":
        return "budget_exhausted_before_target_ci"
    if ci_low < threshold <= ci_high:
        return "ci_overlaps_threshold"
    return "ci_overlaps_threshold"


def _build_adaptive_stop_reason_detail(
    *,
    stop_reason: str | None,
    target_ci_width: float | None,
    achieved_ci_width: float | None,
    budget_used: int | None,
    budget_limit: int | None,
) -> dict[str, Any] | None:
    if stop_reason is None:
        return None

    if stop_reason == "target_ci_width_reached":
        explanation = "adaptive sampling stopped after the configured CI-width target was reached"
    elif stop_reason == "max_budget_reached":
        explanation = "adaptive sampling exhausted its configuration budget before reaching the CI-width target"
    elif stop_reason == "no_candidate_configs":
        explanation = "adaptive sampling had no non-baseline configurations available to expand"
    else:
        explanation = "adaptive sampling stopped with an implementation-defined reason"

    target_met = (
        achieved_ci_width is not None
        and target_ci_width is not None
        and float(achieved_ci_width) <= float(target_ci_width)
    )
    return {
        "status": stop_reason,
        "explanation": explanation,
        "target_met": bool(target_met),
        "budget_exhausted": stop_reason == "max_budget_reached",
        "budget_used": budget_used,
        "budget_limit": budget_limit,
        "target_ci_width": target_ci_width,
        "achieved_ci_width": achieved_ci_width,
    }


def _enrich_adaptive_info(adaptive_info: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(adaptive_info, Mapping):
        return None

    enabled = bool(adaptive_info.get("enabled"))
    info = dict(adaptive_info)
    budget_used = _as_int(info.get("selected_configurations_without_baseline"), 0) if enabled else None
    budget_limit = _as_int(info.get("evaluated_configurations_without_baseline"), 0) if enabled else None
    stop_reason = str(info.get("stop_reason")) if enabled and info.get("stop_reason") is not None else None
    target_ci_width = (
        _as_float(info.get("target_ci_width"))
        if enabled and info.get("target_ci_width") is not None
        else None
    )
    achieved_ci_width = (
        _as_float(info.get("achieved_ci_width"))
        if enabled and info.get("achieved_ci_width") is not None
        else None
    )
    detail = _build_adaptive_stop_reason_detail(
        stop_reason=stop_reason,
        target_ci_width=target_ci_width,
        achieved_ci_width=achieved_ci_width,
        budget_used=budget_used,
        budget_limit=budget_limit,
    )
    if enabled:
        info["budget_used"] = budget_used
        info["budget_limit"] = budget_limit
    info["stop_reason_detail"] = detail
    return info


def _build_claim_interpretation(
    *,
    claim_type: str,
    space_name: str,
    sampling_mode: str,
) -> dict[str, Any]:
    property_map = {
        "ranking": "conditional robustness of reported ranking claim",
        "decision": "conditional robustness of reported decision claim",
        "distribution": "conditional robustness of reported distribution claim",
    }
    return {
        "validated_property": property_map.get(claim_type, "conditional robustness of reported claim"),
        "perturbation_scope": (
            f"software-visible evaluation perturbations within space preset '{space_name}' "
            f"sampled via '{sampling_mode}'"
        ),
        "non_goal": "scientific correctness",
        "claim_perturbation_mode": "none in default runs; claim perturbations are reserved for supporting validation",
    }


def _build_evaluation_profile(
    *,
    sampling_payload: Mapping[str, Any],
    adaptive_info: Mapping[str, Any] | None,
) -> dict[str, Any]:
    k_used = _effective_k_with_baseline(sampling_payload, adaptive_info)
    adaptive_enabled = bool(isinstance(adaptive_info, Mapping) and adaptive_info.get("enabled"))
    target_ci_width = (
        adaptive_info.get("target_ci_width")
        if adaptive_enabled and isinstance(adaptive_info, Mapping)
        else sampling_payload.get("target_ci_width")
    )
    achieved_ci_width = (
        adaptive_info.get("achieved_ci_width")
        if adaptive_enabled and isinstance(adaptive_info, Mapping)
        else None
    )
    stop_reason = (
        str(adaptive_info.get("stop_reason"))
        if adaptive_enabled and isinstance(adaptive_info, Mapping) and adaptive_info.get("stop_reason") is not None
        else None
    )
    budget_used = (
        _as_int(adaptive_info.get("budget_used"))
        if adaptive_enabled and isinstance(adaptive_info, Mapping) and adaptive_info.get("budget_used") is not None
        else None
    )
    budget_limit = (
        _as_int(adaptive_info.get("budget_limit"))
        if adaptive_enabled and isinstance(adaptive_info, Mapping) and adaptive_info.get("budget_limit") is not None
        else None
    )
    stop_reason_detail = (
        adaptive_info.get("stop_reason_detail")
        if adaptive_enabled and isinstance(adaptive_info, Mapping)
        else None
    )
    return {
        "profile_version": "icse_eval_v1",
        "sampling_mode": str(sampling_payload.get("mode", "unknown")),
        "k_used_with_baseline": k_used,
        "k_used_without_baseline": (k_used - 1) if isinstance(k_used, int) and k_used > 0 else None,
        "target_ci_width": target_ci_width,
        "adaptive_enabled": adaptive_enabled,
        "adaptive_achieved_ci_width": achieved_ci_width,
        "adaptive_stop_reason": stop_reason,
        "adaptive_stop_reason_detail": stop_reason_detail,
        "budget_used": budget_used,
        "budget_limit": budget_limit,
    }


def _with_common_eval_metrics(
    summary_row: Mapping[str, Any],
    eval_profile: Mapping[str, Any],
    *,
    threshold: float,
) -> dict[str, Any]:
    out = dict(summary_row)
    ci_low = _as_float(out.get("stability_ci_low"), 0.0)
    ci_high = _as_float(out.get("stability_ci_high"), 0.0)
    out["stability_ci_width"] = max(0.0, ci_high - ci_low)
    out["k_used_with_baseline"] = eval_profile.get("k_used_with_baseline")
    out["k_used_without_baseline"] = eval_profile.get("k_used_without_baseline")
    if eval_profile.get("target_ci_width") is not None:
        out["target_ci_width"] = eval_profile.get("target_ci_width")
    if eval_profile.get("budget_used") is not None:
        out["budget_used"] = eval_profile.get("budget_used")
    if eval_profile.get("budget_limit") is not None:
        out["budget_limit"] = eval_profile.get("budget_limit")
    decision = str(out.get("decision", "inconclusive"))
    explanation = _build_decision_explanation(
        estimate=_as_float(out.get("stability_hat"), 0.0),
        ci_low=ci_low,
        ci_high=ci_high,
        threshold=threshold,
        decision=decision,
    )
    out["decision_explanation"] = explanation
    out["inconclusive_reason"] = _build_inconclusive_reason(
        decision=decision,
        ci_low=ci_low,
        ci_high=ci_high,
        threshold=threshold,
        adaptive_enabled=bool(eval_profile.get("adaptive_enabled")),
        stop_reason=(
            str(eval_profile.get("adaptive_stop_reason"))
            if eval_profile.get("adaptive_stop_reason") is not None
            else None
        ),
        n_claim_evals=_as_int(out.get("n_claim_evals"), 0),
    )
    return out


def _summarize_runner_timing(rows: list[tuple[str, str, ScoreRow]]) -> dict[str, Any]:
    total_rows = len(rows)
    transpile_vals = [float(r.transpile_time_ms) for _, _, r in rows if r.transpile_time_ms is not None]
    execute_vals = [float(r.execute_time_ms) for _, _, r in rows if r.execute_time_ms is not None]
    wall_vals = [float(r.wall_time_ms) for _, _, r in rows if r.wall_time_ms is not None]

    def _safe_mean(values: list[float]) -> float | None:
        return (sum(values) / float(len(values))) if values else None

    return {
        "rows_with_timing": len(wall_vals),
        "transpile_time_ms_sum": sum(transpile_vals) if transpile_vals else 0.0,
        "execute_time_ms_sum": sum(execute_vals) if execute_vals else 0.0,
        "wall_time_ms_sum": sum(wall_vals) if wall_vals else 0.0,
        "transpile_time_ms_mean": _safe_mean(transpile_vals),
        "execute_time_ms_mean": _safe_mean(execute_vals),
        "wall_time_ms_mean": _safe_mean(wall_vals),
        "rows_total": total_rows,
    }


def execute_main_plan(plan: MainPlan) -> MainExecutionResult:
    perf_start = perf_counter()
    args = plan.args
    suite_name = plan.suite_name
    task_kind = plan.task_kind
    task_plugin = plan.task_plugin
    suite = plan.suite
    suite_by_id = plan.suite_by_id
    methods = plan.methods
    method_names = plan.method_names
    selected_spaces = list(plan.selected_spaces)
    ranking_jobs = plan.ranking_jobs
    decision_claims = plan.decision_claims
    distribution_claims = plan.distribution_claims
    sampling_policy = plan.sampling_policy
    metrics_needed = plan.metrics_needed
    decision_metric_name = plan.decision_metric_name
    runtime_meta = plan.runtime_meta
    runtime_context = plan.runtime_context
    trace_path = plan.out_paths.trace_path
    events_path = plan.out_paths.events_path
    cache_path = plan.out_paths.cache_path
    resolved_device = plan.resolved_device
    noise_model_mode = plan.noise_model_mode
    deltas = plan.deltas

    all_rows: list[tuple[str, str, ScoreRow]] = []
    rows_by_space_metric_graph: dict[str, dict[str, dict[str, list[ScoreRow]]]] = {}
    sampling_by_space: dict[str, dict[str, object]] = {}
    baseline_by_space: dict[str, dict[str, int | str | None]] = {}
    baseline_key_by_space: dict[str, PerturbationKey] = {}
    sampled_configs_by_space: dict[str, list[PerturbationConfig]] = {}
    hybrid_init_strategies: list[str] | None = None
    hybrid_init_seeds: list[int] | None = None
    if task_kind == "maxcut":
        axes_fn = getattr(task_plugin, "hybrid_space_axes", None)
        if callable(axes_fn):
            raw_strategies, raw_seeds = axes_fn()
            if isinstance(raw_strategies, list) and isinstance(raw_seeds, list) and raw_strategies and raw_seeds:
                hybrid_init_strategies = [str(v) for v in raw_strategies]
                hybrid_init_seeds = [int(v) for v in raw_seeds]

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
                default_space = make_space(
                    space_name,
                    hybrid_init_strategies=hybrid_init_strategies,
                    hybrid_init_seeds=hybrid_init_seeds,
                )
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
                space = make_space(
                    space_name,
                    hybrid_init_strategies=hybrid_init_strategies,
                    hybrid_init_seeds=hybrid_init_seeds,
                )
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
                if hybrid_init_strategies and hybrid_init_seeds:
                    sampling_by_space[space_name]["hybrid_optimization"] = {
                        "enabled": True,
                        "init_strategies": list(hybrid_init_strategies),
                        "init_seeds": list(hybrid_init_seeds),
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
            enriched_adaptive_info = _enrich_adaptive_info(adaptive_info)
            ranking_sampling_payload: dict[str, object] = dict(sampling_by_space[space_name])
            if isinstance(enriched_adaptive_info, dict) and enriched_adaptive_info.get("enabled"):
                ranking_sampling_payload["adaptive_stopping"] = enriched_adaptive_info
            ranking_eval_profile = _build_evaluation_profile(
                sampling_payload=ranking_sampling_payload,
                adaptive_info=enriched_adaptive_info,
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
            robustness_dimensions = _varying_robustness_dimensions(all_selected_rows)
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
                row = _with_common_eval_metrics(
                    row,
                    ranking_eval_profile,
                    threshold=args.stability_threshold,
                )
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
                cell_dimensions=robustness_dimensions,
            )
            effect_diagnostics_summary = compute_effect_diagnostics(
                observations_by_delta=robustness_observations_by_delta,
                context_conditions={
                    "space_preset": space_name,
                    "device_mode": resolved_device.profile.mode,
                    "noise_model": noise_model_mode,
                },
                varying_dimensions=robustness_dimensions,
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
                "interpretation": _build_claim_interpretation(
                    claim_type="ranking",
                    space_name=space_name,
                    sampling_mode=str(ranking_sampling_payload.get("mode", "unknown")),
                ),
                "baseline": baseline_by_space[space_name],
                "stability_rule": {
                    "threshold": args.stability_threshold,
                    "confidence_level": args.confidence_level,
                    "decision": "stable iff CI lower bound >= threshold",
                },
                "sampling": ranking_sampling_payload,
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
                    "evaluation_profile": {
                        **ranking_eval_profile,
                        "ci_width_by_delta": [
                            {
                                "delta": row.get("delta"),
                                "stability_ci_width": row.get("stability_ci_width"),
                                "n_claim_evals": row.get("n_claim_evals"),
                            }
                            for row in overall_delta
                            if isinstance(row, dict)
                        ],
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
            adaptive_info: dict[str, object] = {"enabled": False}
            allowed_keys: set[tuple[int, int, str | None, int, int | None]] | None = None
            if sampling_policy.mode == "adaptive_ci":
                def _decision_ci_width_for_keys(prefix_keys: set[tuple[int, int, str | None, int, int | None]]) -> float:
                    selected_keys = set(prefix_keys)
                    selected_keys.add(baseline_key)
                    successes = 0
                    total = 0
                    for graph_id, graph_rows in decision_space_rows.items():
                        inst = suite_by_id.get(graph_id)
                        label = fixed_label
                        if label is None and inst is not None and isinstance(inst.meta, dict):
                            label = inst.meta.get(label_meta_key)
                        if not isinstance(label, str) or not label:
                            continue
                        eval_rows = filter_rows_by_keys(graph_rows, selected_keys)
                        graph_eval = evaluate_decision_claim_on_rows(
                            eval_rows,
                            method=method,
                            top_k=top_k,
                            instance_target_label=label,
                            stability_threshold=args.stability_threshold,
                            confidence_level=args.confidence_level,
                        )
                        successes += int(graph_eval["accepted"])
                        total += int(graph_eval["total"])
                    if total <= 0:
                        return 1.0
                    estimate = estimate_binomial_rate(
                        successes=successes,
                        total=total,
                        confidence=args.confidence_level,
                    )
                    return ci_width(estimate)

                allowed_keys, adaptive_info = select_adaptive_keys_with_width_evaluator(
                    sampled_configs=sampled_configs_by_space[space_name],
                    baseline_key=baseline_key,
                    evaluate_ci_width_for_keys=_decision_ci_width_for_keys,
                    target_ci_width=float(sampling_policy.target_ci_width or 0.02),
                    min_sample_size=max(1, int(sampling_policy.min_sample_size)),
                    step_size=max(1, int(sampling_policy.step_size)),
                )
            enriched_adaptive_info = _enrich_adaptive_info(adaptive_info)
            decision_sampling_payload: dict[str, object] = dict(sampling_by_space[space_name])
            if isinstance(enriched_adaptive_info, dict) and enriched_adaptive_info.get("enabled"):
                decision_sampling_payload["adaptive_stopping"] = enriched_adaptive_info
            decision_eval_profile = _build_evaluation_profile(
                sampling_payload=decision_sampling_payload,
                adaptive_info=enriched_adaptive_info,
            )
            for graph_id, graph_rows in decision_space_rows.items():
                inst = suite_by_id.get(graph_id)
                label = fixed_label
                if label is None and inst is not None and isinstance(inst.meta, dict):
                    label = inst.meta.get(label_meta_key)
                if not isinstance(label, str) or not label:
                    continue
                eval_rows = graph_rows if allowed_keys is None else filter_rows_by_keys(graph_rows, allowed_keys)
                graph_eval = evaluate_decision_claim_on_rows(
                    eval_rows,
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
            summary_row = _with_common_eval_metrics(
                summary_row,
                decision_eval_profile,
                threshold=args.stability_threshold,
            )
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
                    "interpretation": _build_claim_interpretation(
                        claim_type="decision",
                        space_name=space_name,
                        sampling_mode=str(decision_sampling_payload.get("mode", "unknown")),
                    ),
                    "baseline": baseline_by_space[space_name],
                    "stability_rule": {
                        "threshold": args.stability_threshold,
                        "confidence_level": args.confidence_level,
                        "decision": "stable iff CI lower bound >= threshold",
                    },
                    "sampling": decision_sampling_payload,
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
                        "evaluation_profile": {
                            **decision_eval_profile,
                            "ci_width_by_delta": [
                                {
                                    "delta": summary_row.get("delta"),
                                    "stability_ci_width": summary_row.get("stability_ci_width"),
                                    "n_claim_evals": summary_row.get("n_claim_evals"),
                                }
                            ],
                        },
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
            adaptive_info: dict[str, object] = {"enabled": False}
            allowed_keys: set[tuple[int, int, str | None, int, int | None]] | None = None
            if sampling_policy.mode == "adaptive_ci":
                def _distribution_ci_width_for_keys(prefix_keys: set[tuple[int, int, str | None, int, int | None]]) -> float:
                    selected_keys = set(prefix_keys)
                    selected_keys.add(baseline_key)
                    successes = 0
                    total = 0
                    for graph_rows in distribution_space_rows.values():
                        eval_rows = filter_rows_by_keys(graph_rows, selected_keys)
                        graph_eval = evaluate_distribution_claim_on_rows(
                            eval_rows,
                            method=method,
                            baseline_key=baseline_key,
                            key_sort_value=key_sort_value,
                            epsilon=epsilon,
                            primary_distance=primary_distance,
                            sanity_distance=sanity_distance,
                            reference_shots=reference_shots,
                            stability_threshold=args.stability_threshold,
                            confidence_level=args.confidence_level,
                        )
                        successes += int(graph_eval.get("accepted", 0))
                        total += int(graph_eval.get("total", 0))
                    if total <= 0:
                        return 1.0
                    estimate = estimate_binomial_rate(
                        successes=successes,
                        total=total,
                        confidence=args.confidence_level,
                    )
                    return ci_width(estimate)

                allowed_keys, adaptive_info = select_adaptive_keys_with_width_evaluator(
                    sampled_configs=sampled_configs_by_space[space_name],
                    baseline_key=baseline_key,
                    evaluate_ci_width_for_keys=_distribution_ci_width_for_keys,
                    target_ci_width=float(sampling_policy.target_ci_width or 0.02),
                    min_sample_size=max(1, int(sampling_policy.min_sample_size)),
                    step_size=max(1, int(sampling_policy.step_size)),
                )
            enriched_adaptive_info = _enrich_adaptive_info(adaptive_info)
            distribution_sampling_payload: dict[str, object] = dict(sampling_by_space[space_name])
            if isinstance(enriched_adaptive_info, dict) and enriched_adaptive_info.get("enabled"):
                distribution_sampling_payload["adaptive_stopping"] = enriched_adaptive_info
            distribution_eval_profile = _build_evaluation_profile(
                sampling_payload=distribution_sampling_payload,
                adaptive_info=enriched_adaptive_info,
            )

            for graph_id, graph_rows in distribution_space_rows.items():
                eval_rows = graph_rows if allowed_keys is None else filter_rows_by_keys(graph_rows, allowed_keys)
                graph_eval = evaluate_distribution_claim_on_rows(
                    eval_rows,
                    method=method,
                    baseline_key=baseline_key,
                    key_sort_value=key_sort_value,
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
            summary_row = _with_common_eval_metrics(
                summary_row,
                distribution_eval_profile,
                threshold=args.stability_threshold,
            )
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
                    "interpretation": _build_claim_interpretation(
                        claim_type="distribution",
                        space_name=space_name,
                        sampling_mode=str(distribution_sampling_payload.get("mode", "unknown")),
                    ),
                    "baseline": baseline_by_space[space_name],
                    "stability_rule": {
                        "threshold": args.stability_threshold,
                        "confidence_level": args.confidence_level,
                        "decision": "stable iff CI lower bound >= threshold",
                    },
                    "sampling": distribution_sampling_payload,
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
                        "evaluation_profile": {
                            **distribution_eval_profile,
                            "ci_width_by_delta": [
                                {
                                    "delta": summary_row.get("delta"),
                                    "stability_ci_width": summary_row.get("stability_ci_width"),
                                    "n_claim_evals": summary_row.get("n_claim_evals"),
                                }
                            ],
                        },
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

    total_wall_time = perf_counter() - perf_start
    rows_processed = len(all_rows)
    runner_timing = _summarize_runner_timing(all_rows)
    practicality = {
        "num_workers": 1,
        "total_wall_time": total_wall_time,
        "wall_time_ms": total_wall_time * 1000.0,
        "rows_processed": rows_processed,
        "throughput_runs_per_sec": (rows_processed / total_wall_time) if total_wall_time > 0 else None,
        "runner_timing": runner_timing,
    }

    return MainExecutionResult(
        all_rows=all_rows,
        experiments=experiments,
        comparative_rows=comparative_rows,
        artifact_manifest=artifact_manifest,
        runtime_meta=runtime_meta,
        suite_name=suite_name,
        selected_spaces=selected_spaces,
        practicality=practicality,
    )
