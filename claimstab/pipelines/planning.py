from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.io.runtime_meta import collect_runtime_metadata
from claimstab.perturbations.sampling import SamplingPolicy
from claimstab.tasks.factory import make_task, parse_methods


@dataclass(frozen=True)
class MainOutPaths:
    out_dir: Path
    out_csv: Path
    out_json: Path
    rq_json: Path
    robustness_json: Path
    trace_path: Path
    events_path: Path | None
    cache_path: Path | None


@dataclass
class MainPlan:
    args: argparse.Namespace
    spec_payload: dict[str, Any]
    suite_name: str
    task_kind: str
    task_plugin: Any
    suite: list[Any]
    suite_by_id: dict[str, Any]
    methods: list[Any]
    method_names: set[str]
    selected_spaces: list[str]
    ranking_jobs: list[dict[str, Any]]
    decision_claims: list[dict[str, Any]]
    distribution_claims: list[dict[str, Any]]
    sampling_mode: str
    sampling_params: dict[str, Any]
    sampling_policy: SamplingPolicy
    stability_rule: dict[str, float]
    out_paths: MainOutPaths
    backend_config: dict[str, Any]
    device_profile_config: dict[str, Any]
    flags: dict[str, Any]
    metrics_needed: list[str]
    decision_metric_name: str
    runtime_meta: dict[str, Any]
    runtime_context: Mapping[str, Any]
    resolved_device: Any
    noise_model_mode: str
    deltas: list[float]


def resolve_main_plan(
    args: argparse.Namespace,
    *,
    parse_deltas_fn: Callable[[str], list[float]],
    parse_csv_tokens_fn: Callable[[str], list[str]],
    canonical_space_name_fn: Callable[[str], str],
    canonical_suite_name_fn: Callable[[str], str],
    try_load_spec_fn: Callable[[str | None], dict[str, Any]],
    parse_claim_pairs_fn: Callable[[str, tuple[str, str]], list[tuple[str, str]]],
    parse_ranking_claims_from_spec_fn: Callable[..., list[dict[str, Any]]],
    parse_decision_claims_from_spec_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    parse_distribution_claims_from_spec_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    has_explicit_claims_fn: Callable[[dict[str, Any]], bool],
    as_bool_fn: Callable[[Any, bool], bool],
) -> MainPlan:
    args.suite = canonical_suite_name_fn(args.suite)
    spec_payload = try_load_spec_fn(args.spec)
    if args.task:
        if not isinstance(spec_payload, dict):
            spec_payload = {}
        task_block = spec_payload.get("task")
        if not isinstance(task_block, dict):
            task_block = {}
        task_block["kind"] = str(args.task).strip()
        task_block.setdefault("suite", args.suite)
        spec_payload["task"] = task_block

    deltas = parse_deltas_fn(args.deltas)
    default_ranking_metric = args.ranking_metric
    default_higher_is_better = not args.lower_is_better
    selected_space_inputs = parse_csv_tokens_fn(args.space_presets) if args.space_presets.strip() else [args.space_preset]
    selected_spaces = [canonical_space_name_fn(name) for name in selected_space_inputs]

    task_plugin, task_suite = make_task(
        spec_payload.get("task") if isinstance(spec_payload, dict) else None,
        default_suite=args.suite,
    )
    suite_raw = str(spec_payload.get("suite", task_suite)).strip() if isinstance(spec_payload, dict) else str(task_suite)
    suite_name = canonical_suite_name_fn(suite_raw)
    suite = task_plugin.instances(suite_name)
    if not suite:
        raise ValueError(f"Task '{getattr(task_plugin, 'name', 'unknown')}' returned an empty suite for '{suite_name}'.")
    suite_by_id = {inst.instance_id: inst for inst in suite}

    out_dir = Path(args.out_dir)
    out_paths = MainOutPaths(
        out_dir=out_dir,
        out_csv=out_dir / "scores.csv",
        out_json=out_dir / "claim_stability.json",
        rq_json=out_dir / "rq_summary.json",
        robustness_json=out_dir / "robustness_map.json",
        trace_path=Path(args.trace_out) if args.trace_out else (out_dir / "trace.jsonl"),
        events_path=Path(args.events_out) if args.events_out else None,
        cache_path=Path(args.cache_db) if args.cache_db else None,
    )

    task_kind = str(getattr(task_plugin, "name", "maxcut")).strip().lower()
    methods = parse_methods(spec_payload if isinstance(spec_payload, dict) else {}, task_kind=task_kind)
    method_names = {m.name for m in methods}
    decision_claims = parse_decision_claims_from_spec_fn(spec_payload if isinstance(spec_payload, dict) else {})
    distribution_claims = parse_distribution_claims_from_spec_fn(spec_payload if isinstance(spec_payload, dict) else {})
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

    spec_ranking_jobs = parse_ranking_claims_from_spec_fn(
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
            for method_a, method_b in parse_claim_pairs_fn(args.claim_pairs, (args.method_a, args.method_b))
        ]
    elif spec_ranking_jobs:
        ranking_jobs = spec_ranking_jobs
    elif task_kind == "bv" and decision_claims:
        ranking_jobs = []
    elif has_explicit_claims_fn(spec_payload if isinstance(spec_payload, dict) else {}) and not spec_ranking_jobs:
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
            for method_a, method_b in parse_claim_pairs_fn(args.claim_pairs, (args.method_a, args.method_b))
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
        job["higher_is_better"] = as_bool_fn(job.get("higher_is_better"), default_higher_is_better)

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
    device_profile = parse_device_profile(spec_payload.get("device_profile") if isinstance(spec_payload, dict) else None)
    resolved_device = resolve_device_profile(device_profile)
    noise_model_mode = parse_noise_model_mode(spec_payload.get("backend") if isinstance(spec_payload, dict) else None)

    return MainPlan(
        args=args,
        spec_payload=spec_payload if isinstance(spec_payload, dict) else {},
        suite_name=suite_name,
        task_kind=task_kind,
        task_plugin=task_plugin,
        suite=suite,
        suite_by_id=suite_by_id,
        methods=methods,
        method_names=method_names,
        selected_spaces=selected_spaces,
        ranking_jobs=ranking_jobs,
        decision_claims=decision_claims,
        distribution_claims=distribution_claims,
        sampling_mode=args.sampling_mode,
        sampling_params={
            "sample_size": args.sample_size,
            "sample_seed": args.sample_seed,
            "target_ci_width": args.target_ci_width,
            "max_sample_size": args.max_sample_size,
            "min_sample_size": args.min_sample_size,
            "step_size": args.step_size,
        },
        sampling_policy=sampling_policy,
        stability_rule={
            "threshold": float(args.stability_threshold),
            "confidence_level": float(args.confidence_level),
        },
        out_paths=out_paths,
        backend_config={
            "engine": args.backend_engine,
            "spot_check_noise": bool(args.spot_check_noise),
            "one_qubit_error": float(args.one_qubit_error),
            "two_qubit_error": float(args.two_qubit_error),
        },
        device_profile_config={
            "enabled": resolved_device.profile.enabled,
            "provider": resolved_device.profile.provider,
            "name": resolved_device.profile.name,
            "mode": resolved_device.profile.mode,
        },
        flags={
            "debug_attribution": bool(args.debug_attribution),
            "use_operator_shim": bool(args.use_operator_shim),
            "replay_trace": args.replay_trace,
            "cache_db": args.cache_db,
            "events_out": args.events_out,
            "trace_out": args.trace_out,
            "spec": args.spec,
        },
        metrics_needed=metrics_needed,
        decision_metric_name=decision_metric_name,
        runtime_meta=runtime_meta,
        runtime_context=runtime_context,
        resolved_device=resolved_device,
        noise_model_mode=noise_model_mode,
        deltas=deltas,
    )
