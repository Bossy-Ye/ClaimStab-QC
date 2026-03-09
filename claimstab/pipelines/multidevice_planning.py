from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from claimstab.core import ArtifactManifest
from claimstab.io.runtime_meta import collect_runtime_metadata
from claimstab.perturbations.sampling import SamplingPolicy
from claimstab.tasks.factory import make_task, parse_methods


@dataclass
class MultidevicePlan:
    args: argparse.Namespace
    spec_payload: dict[str, Any]
    suite_name: str
    task_plugin: Any
    suite: list[Any]
    methods: list[Any]
    method_names: set[str]
    num_qubits_by_instance: dict[str, int]
    out_root: Path
    sampling_policy: SamplingPolicy
    trace_path: Path
    events_path: Path | None
    cache_path: Path | None
    artifact_manifest: ArtifactManifest
    runtime_meta: dict[str, Any]
    runtime_context: Mapping[str, Any]
    deltas: list[float]
    transpile_space: str
    noisy_space: str


def resolve_multidevice_plan(
    args: argparse.Namespace,
    *,
    canonical_suite_name_fn: Callable[[str], str],
    parse_deltas_fn: Callable[[str], list[float]],
    canonical_space_name_fn: Callable[[str], str],
    try_load_spec_fn: Callable[[str | None], dict[str, Any]],
    bound_task_cls: Any,
) -> MultidevicePlan:
    args.suite = canonical_suite_name_fn(args.suite)
    deltas = parse_deltas_fn(args.deltas)
    transpile_space = canonical_space_name_fn(args.transpile_space)
    noisy_space = canonical_space_name_fn(args.noisy_space)
    runtime_meta = collect_runtime_metadata(
        include_dependencies=not bool(args.replay_trace),
        include_environment_flags=not bool(args.replay_trace),
        include_git=not bool(args.replay_trace),
    )
    spec_payload = try_load_spec_fn(args.spec)
    task_plugin, task_suite = make_task(
        spec_payload.get("task") if isinstance(spec_payload, dict) else None,
        default_suite=args.suite,
    )
    suite_raw = str(spec_payload.get("suite", task_suite)).strip() if isinstance(spec_payload, dict) else str(task_suite)
    suite_name = canonical_suite_name_fn(suite_raw)
    suite = task_plugin.instances(suite_name)
    if not suite:
        raise ValueError(f"Task '{getattr(task_plugin, 'name', 'unknown')}' returned an empty suite for '{suite_name}'.")

    methods = parse_methods(spec_payload if isinstance(spec_payload, dict) else {})
    method_names = {m.name for m in methods}
    num_qubits_by_instance: dict[str, int] = {}
    for inst in suite:
        num_qubits_by_instance[inst.instance_id] = bound_task_cls(task_plugin, inst).infer_num_qubits(methods)

    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    sampling_policy = SamplingPolicy(
        mode=args.sampling_mode,
        sample_size=args.sample_size if args.sampling_mode == "random_k" else None,
        seed=args.sample_seed,
    )
    trace_path = Path(args.trace_out) if args.trace_out else (out_root / "trace.jsonl")
    events_path = Path(args.events_out) if args.events_out else None
    cache_path = Path(args.cache_db) if args.cache_db else None
    artifact_manifest = ArtifactManifest(
        trace_jsonl=str(trace_path.resolve()),
        events_jsonl=str(events_path.resolve()) if events_path is not None else None,
        cache_db=str(cache_path.resolve()) if cache_path is not None else None,
    )
    runtime_context: Mapping[str, Any] = {
        "python_version": runtime_meta.get("python_version"),
        "git_commit": runtime_meta.get("git_commit"),
        "qiskit_version": (runtime_meta.get("dependencies", {}) or {}).get("qiskit"),
    }

    return MultidevicePlan(
        args=args,
        spec_payload=spec_payload if isinstance(spec_payload, dict) else {},
        suite_name=suite_name,
        task_plugin=task_plugin,
        suite=suite,
        methods=methods,
        method_names=method_names,
        num_qubits_by_instance=num_qubits_by_instance,
        out_root=out_root,
        sampling_policy=sampling_policy,
        trace_path=trace_path,
        events_path=events_path,
        cache_path=cache_path,
        artifact_manifest=artifact_manifest,
        runtime_meta=runtime_meta,
        runtime_context=runtime_context,
        deltas=deltas,
        transpile_space=transpile_space,
        noisy_space=noisy_space,
    )
