from __future__ import annotations

import csv
import json
import shlex
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from claimstab.cache.store import CacheStore
from claimstab.claims.evaluation import collect_paired_scores
from claimstab.claims.ranking import HigherIsBetter, RankingClaim, compute_rank_flip_summary
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.core import ArtifactManifest, TraceIndex, TraceRecord
from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.evidence import build_experiment_cep_record
from claimstab.pipelines.multidevice_planning import MultidevicePlan
from claimstab.runners.matrix_runner import MatrixRunner, ScoreRow
from claimstab.runners.qiskit_aer import QiskitAerRunner

ConfigKey = tuple[int, int, str | None, int, int | None]


@dataclass(frozen=True)
class MultideviceCallbacks:
    parse_csv_tokens: Callable[[str], list[str]]
    parse_claim_pairs: Callable[[str], list[tuple[str, str]]]
    make_space: Callable[[str], Any]
    build_baseline: Callable[[Any], tuple[Any, ConfigKey, dict[str, int | str | None]]]
    key_sort_value: Callable[[ConfigKey], tuple[int, int, str, int, int]]
    config_from_key: Callable[[ConfigKey], Any]
    baseline_from_keys: Callable[[set[ConfigKey]], tuple[ConfigKey, dict[str, int | str | None]]]
    build_evidence_ref: Callable[..., dict[str, Any]]
    evidence_chain_meta: Callable[[], dict[str, Any]]
    make_event_logger: Callable[[Path], Callable[[dict[str, Any]], None]]
    load_rows_from_trace: Callable[[Path], tuple[str, dict[str, dict[str, dict[str, list[ScoreRow]]]], dict[str, set[ConfigKey]], dict[str, str]]]
    evaluate_rows_for_claim: Callable[..., tuple[dict[str, dict[str, object]], list[dict[str, object]]]]
    write_rows_csv: Callable[[Iterable[ScoreRow], Path], None]


@dataclass
class MultideviceExecutionResult:
    suite_name: str
    artifact_manifest: ArtifactManifest
    trace_path: Path
    global_trace_index: TraceIndex | None
    global_device_summary: list[dict[str, object]]


def execute_multidevice_plan(
    plan: MultidevicePlan,
    *,
    callbacks: MultideviceCallbacks,
    bound_task_cls: Any,
    generated_by: str = "claimstab/pipelines/multidevice_app.py",
) -> MultideviceExecutionResult:
    args = plan.args
    spec_payload = plan.spec_payload
    runtime_meta = plan.runtime_meta

    suite_name = plan.suite_name
    artifact_manifest = plan.artifact_manifest
    trace_path = plan.trace_path

    global_device_summary: list[dict[str, object]] = []
    replay_rows_by_batch: dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]] = {}
    replay_keys_by_batch: dict[str, set[ConfigKey]] = {}
    replay_space_by_batch: dict[str, str] = {}
    global_trace_index = TraceIndex() if not args.replay_trace else None

    if args.replay_trace:
        replay_path = Path(args.replay_trace)
        replay_suite_name, replay_rows_by_batch, replay_keys_by_batch, replay_space_by_batch = callbacks.load_rows_from_trace(
            replay_path
        )
        suite_name = replay_suite_name
        trace_path = replay_path
        artifact_manifest = ArtifactManifest(
            trace_jsonl=str(trace_path.resolve()),
            events_jsonl=artifact_manifest.events_jsonl,
            cache_db=artifact_manifest.cache_db,
        )

    def write_skipped_batch_summary(*, batch_mode: str, requested_devices: list[str], reason: str) -> None:
        batch_dir = plan.out_root / batch_mode
        batch_dir.mkdir(parents=True, exist_ok=True)
        summary_payload = {
            "meta": {
                "suite": suite_name,
                "batch_mode": batch_mode,
                "generated_by": generated_by,
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                "runtime": runtime_meta,
                "artifacts": {
                    "trace_jsonl": artifact_manifest.trace_jsonl,
                    "events_jsonl": artifact_manifest.events_jsonl,
                    "cache_db": artifact_manifest.cache_db,
                    "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                },
                "evidence_chain": callbacks.evidence_chain_meta(),
            },
            "batch": {
                "mode": batch_mode,
                "devices_requested": requested_devices,
                "devices_completed": [],
                "devices_skipped": [{"device_name": d, "reason": reason} for d in requested_devices],
            },
            "experiments": [],
            "device_summary": [],
            "comparative": {"space_claim_delta": []},
        }
        out_json = batch_dir / f"{batch_mode}_summary.json"
        out_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        out_csv = batch_dir / f"{batch_mode}_summary.csv"
        out_csv.write_text("", encoding="utf-8")
        print("[WARN]", reason)
        print("Wrote:")
        print(" ", out_json.resolve())
        print(" ", out_csv.resolve())

    def run_batch(
        *,
        batch_mode: str,
        device_names: list[str],
        space_name: str,
        metric_names: list[str],
        claim_pairs: list[tuple[str, str]],
        direction: HigherIsBetter,
        noise_model_mode: str,
        replay_device_rows: dict[str, dict[str, dict[str, list[ScoreRow]]]] | None = None,
        replay_keys: set[ConfigKey] | None = None,
    ) -> None:
        batch_dir = plan.out_root / batch_mode
        batch_dir.mkdir(parents=True, exist_ok=True)
        batch_experiments: list[dict[str, object]] = []
        combined_rows: list[dict[str, object]] = []
        skipped: list[dict[str, str]] = []

        if replay_device_rows is not None:
            replay_device_list = [d for d in device_names if d in replay_device_rows]
            if not replay_device_list:
                replay_device_list = sorted(replay_device_rows.keys())
            key_set = set(replay_keys or set())
            if not key_set:
                for device_name in replay_device_list:
                    for metric_map in replay_device_rows.get(device_name, {}).values():
                        for rows in metric_map.values():
                            for row in rows:
                                key_set.add(
                                    (
                                        row.seed_transpiler,
                                        row.optimization_level,
                                        row.layout_method,
                                        row.shots,
                                        row.seed_simulator,
                                    )
                                )
            baseline_key, baseline_dict = callbacks.baseline_from_keys(key_set)
            sampled_configs = [callbacks.config_from_key(k) for k in sorted(key_set, key=callbacks.key_sort_value)]

            for device_name in replay_device_list:
                metric_map = replay_device_rows.get(device_name, {})
                for metric_name in metric_names:
                    rows_by_graph = metric_map.get(metric_name, {})
                    all_rows = [row for rows in rows_by_graph.values() for row in rows]
                    if not all_rows:
                        continue
                    csv_name = f"{batch_mode}_{device_name}_{metric_name}.csv"
                    callbacks.write_rows_csv(all_rows, batch_dir / csv_name)

                    first_row = all_rows[0]
                    for method_a, method_b in claim_pairs:
                        if method_a not in plan.method_names or method_b not in plan.method_names:
                            continue
                        per_graph, overall = callbacks.evaluate_rows_for_claim(
                            rows_by_graph=rows_by_graph,
                            method_a=method_a,
                            method_b=method_b,
                            deltas=plan.deltas,
                            baseline_key=baseline_key,
                            direction=direction,
                            stability_threshold=args.stability_threshold,
                            confidence_level=args.confidence_level,
                        )
                        claim_payload = {
                            "type": "ranking",
                            "metric_name": metric_name,
                            "direction": direction.value,
                            "method_a": method_a,
                            "method_b": method_b,
                            "deltas": plan.deltas,
                        }
                        exp = {
                            "experiment_id": f"{batch_mode}:{device_name}:{metric_name}:{method_a}>{method_b}",
                            "claim": claim_payload,
                            "baseline": baseline_dict,
                            "sampling": {
                                "suite": suite_name,
                                "space_preset": space_name,
                                "mode": "replay_trace",
                                "sample_size": None,
                                "seed": args.sample_seed,
                                "sampled_configurations_with_baseline": len(sampled_configs),
                                "perturbation_space_size": len(sampled_configs),
                                "replay_trace": str(args.replay_trace),
                            },
                            "backend": {
                                "engine": args.backend_engine,
                                "noise_model": noise_model_mode,
                            },
                            "device_profile": {
                                "enabled": True,
                                "provider": first_row.device_provider,
                                "name": first_row.device_name,
                                "mode": first_row.device_mode,
                                "snapshot_fingerprint": first_row.device_snapshot_fingerprint,
                                "snapshot": {},
                            },
                            "per_graph": per_graph,
                            "overall": {
                                "graphs": len(per_graph),
                                "delta_sweep": overall,
                            },
                            "evidence": callbacks.build_evidence_ref(
                                suite_name=suite_name,
                                space_name=space_name,
                                metric_name=metric_name,
                                claim=claim_payload,
                                artifact_manifest=artifact_manifest,
                            ),
                        }
                        evidence = exp.get("evidence")
                        if isinstance(evidence, dict):
                            evidence["cep"] = build_experiment_cep_record(
                                experiment=exp,
                                runtime_meta=runtime_meta,
                                evidence=evidence,
                            )
                        batch_experiments.append(exp)
                        for row in overall:
                            summary_row = {
                                "batch_mode": batch_mode,
                                "device_name": device_name,
                                "metric_name": metric_name,
                                "claim_pair": f"{method_a}>{method_b}",
                                **row,
                            }
                            combined_rows.append(summary_row)
                            global_device_summary.append(summary_row)

                device_json = batch_dir / f"{batch_mode}_{device_name}.json"
                device_payload = {
                    "meta": {
                        "suite": suite_name,
                        "batch_mode": batch_mode,
                        "device_name": device_name,
                        "generated_by": generated_by,
                        "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                        "runtime": runtime_meta,
                        "artifacts": {
                            "trace_jsonl": artifact_manifest.trace_jsonl,
                            "events_jsonl": artifact_manifest.events_jsonl,
                            "cache_db": artifact_manifest.cache_db,
                            "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                        },
                        "evidence_chain": callbacks.evidence_chain_meta(),
                    },
                    "device_compatibility": {
                        "device_qubits": None,
                        "included_instances": sorted({i for m in metric_map.values() for i in m.keys()}),
                        "skipped_instances": [],
                    },
                    "experiments": [e for e in batch_experiments if f":{device_name}:" in str(e["experiment_id"])],
                }
                device_json.write_text(json.dumps(device_payload, indent=2), encoding="utf-8")
        else:
            from claimstab.perturbations.sampling import ensure_config_included, sample_configs

            space = callbacks.make_space(space_name)
            baseline_pc, baseline_key, baseline_dict = callbacks.build_baseline(space)
            sampled_configs = ensure_config_included(
                sample_configs(space, plan.sampling_policy, use_operator_shim=args.use_operator_shim),
                baseline_pc,
            )
            cache_store: CacheStore | None = CacheStore(plan.cache_path) if plan.cache_path is not None else None
            event_logger = callbacks.make_event_logger(plan.events_path) if plan.events_path is not None else None

            try:
                for device_name in device_names:
                    profile_dict = dict(spec_payload.get("device_profile", {})) if isinstance(spec_payload, dict) else {}
                    profile_dict.update(
                        {
                            "enabled": True,
                            "provider": profile_dict.get("provider", "ibm_fake"),
                            "name": device_name,
                            "mode": batch_mode,
                        }
                    )
                    profile = parse_device_profile(profile_dict)
                    try:
                        resolved = resolve_device_profile(profile)
                    except Exception as exc:
                        skipped.append({"device_name": device_name, "reason": str(exc)})
                        continue

                    device_num_qubits_raw = getattr(resolved.backend, "num_qubits", None) if resolved.backend is not None else None
                    device_num_qubits = int(device_num_qubits_raw) if device_num_qubits_raw is not None else None
                    compatible_suite = []
                    skipped_instances: list[dict[str, object]] = []
                    for inst in plan.suite:
                        graph_qubits = plan.num_qubits_by_instance.get(inst.instance_id)
                        if device_num_qubits is not None and graph_qubits is not None and int(graph_qubits) > device_num_qubits:
                            skipped_instances.append(
                                {
                                    "instance_id": getattr(inst, "instance_id", "unknown"),
                                    "required_qubits": int(graph_qubits),
                                    "device_qubits": device_num_qubits,
                                }
                            )
                            continue
                        compatible_suite.append(inst)

                    if not compatible_suite:
                        skipped.append(
                            {
                                "device_name": device_name,
                                "reason": (
                                    f"No compatible instances for this device "
                                    f"(device_qubits={device_num_qubits}, suite={suite_name})."
                                ),
                            }
                        )
                        continue

                    runner = MatrixRunner(backend=QiskitAerRunner(engine=args.backend_engine))
                    device_event_logger: Callable[[dict[str, Any]], None] | None = None
                    if event_logger is not None:

                        def _device_event(payload: dict[str, Any], *, _device=device_name, _batch=batch_mode) -> None:
                            event_logger({**payload, "device_name": _device, "batch_mode": _batch})

                        device_event_logger = _device_event

                    for metric_name in metric_names:
                        rows_by_graph: dict[str, list[ScoreRow]] = {}
                        all_rows: list[ScoreRow] = []
                        for inst in compatible_suite:
                            task = bound_task_cls(plan.task_plugin, inst)
                            rows = runner.run(
                                task=task,
                                methods=plan.methods,
                                space=space,
                                configs=sampled_configs,
                                coupling_map=None,
                                metric_name=metric_name,
                                device_profile=resolved.profile,
                                device_backend=resolved.backend,
                                noise_model_mode=noise_model_mode,
                                device_snapshot_fingerprint=resolved.snapshot_fingerprint,
                                device_snapshot_summary=resolved.snapshot,
                                cache_store=cache_store,
                                runtime_context={**plan.runtime_context, "batch_mode": batch_mode},
                                event_logger=device_event_logger,
                            )
                            rows_by_graph[inst.instance_id] = rows
                            all_rows.extend(rows)
                            if global_trace_index is not None:
                                global_trace_index.extend(
                                    [
                                        TraceRecord.from_score_row(suite=suite_name, space_preset=space_name, row=row)
                                        for row in rows
                                    ]
                                )

                        csv_name = f"{batch_mode}_{device_name}_{metric_name}.csv"
                        callbacks.write_rows_csv(all_rows, batch_dir / csv_name)

                        for method_a, method_b in claim_pairs:
                            if method_a not in plan.method_names or method_b not in plan.method_names:
                                continue
                            per_graph, overall = callbacks.evaluate_rows_for_claim(
                                rows_by_graph=rows_by_graph,
                                method_a=method_a,
                                method_b=method_b,
                                deltas=plan.deltas,
                                baseline_key=baseline_key,
                                direction=direction,
                                stability_threshold=args.stability_threshold,
                                confidence_level=args.confidence_level,
                            )
                            claim_payload = {
                                "type": "ranking",
                                "metric_name": metric_name,
                                "direction": direction.value,
                                "method_a": method_a,
                                "method_b": method_b,
                                "deltas": plan.deltas,
                            }
                            exp = {
                                "experiment_id": f"{batch_mode}:{device_name}:{metric_name}:{method_a}>{method_b}",
                                "claim": claim_payload,
                                "baseline": baseline_dict,
                                "sampling": {
                                    "suite": suite_name,
                                    "space_preset": space_name,
                                    "mode": plan.sampling_policy.mode,
                                    "sample_size": plan.sampling_policy.sample_size,
                                    "seed": plan.sampling_policy.seed,
                                    "sampled_configurations_with_baseline": len(sampled_configs),
                                    "perturbation_space_size": space.size(),
                                    "operator_shim": bool(args.use_operator_shim),
                                },
                                "backend": {
                                    "engine": args.backend_engine,
                                    "noise_model": noise_model_mode,
                                },
                                "device_profile": {
                                    "enabled": resolved.profile.enabled,
                                    "provider": resolved.profile.provider,
                                    "name": resolved.profile.name,
                                    "mode": resolved.profile.mode,
                                    "snapshot_fingerprint": resolved.snapshot_fingerprint,
                                    "snapshot": resolved.snapshot,
                                },
                                "per_graph": per_graph,
                                "overall": {
                                    "graphs": len(per_graph),
                                    "delta_sweep": overall,
                                },
                                "evidence": callbacks.build_evidence_ref(
                                    suite_name=suite_name,
                                    space_name=space_name,
                                    metric_name=metric_name,
                                    claim=claim_payload,
                                    artifact_manifest=artifact_manifest,
                                ),
                            }
                            evidence = exp.get("evidence")
                            if isinstance(evidence, dict):
                                evidence["cep"] = build_experiment_cep_record(
                                    experiment=exp,
                                    runtime_meta=runtime_meta,
                                    evidence=evidence,
                                )
                            batch_experiments.append(exp)
                            for row in overall:
                                summary_row = {
                                    "batch_mode": batch_mode,
                                    "device_name": device_name,
                                    "metric_name": metric_name,
                                    "claim_pair": f"{method_a}>{method_b}",
                                    **row,
                                }
                                combined_rows.append(summary_row)
                                global_device_summary.append(summary_row)

                    device_json = batch_dir / f"{batch_mode}_{device_name}.json"
                    device_payload = {
                        "meta": {
                            "suite": suite_name,
                            "batch_mode": batch_mode,
                            "device_name": device_name,
                            "generated_by": generated_by,
                            "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                            "runtime": runtime_meta,
                            "artifacts": {
                                "trace_jsonl": artifact_manifest.trace_jsonl,
                                "events_jsonl": artifact_manifest.events_jsonl,
                                "cache_db": artifact_manifest.cache_db,
                                "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                            },
                            "evidence_chain": callbacks.evidence_chain_meta(),
                        },
                        "device_compatibility": {
                            "device_qubits": device_num_qubits,
                            "included_instances": [getattr(inst, "instance_id", "unknown") for inst in compatible_suite],
                            "skipped_instances": skipped_instances,
                        },
                        "experiments": [e for e in batch_experiments if f":{device_name}:" in str(e["experiment_id"])],
                    }
                    device_json.write_text(json.dumps(device_payload, indent=2), encoding="utf-8")
            finally:
                if cache_store is not None:
                    cache_store.close()

        summary_payload = {
            "meta": {
                "suite": suite_name,
                "batch_mode": batch_mode,
                "generated_by": generated_by,
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                "runtime": runtime_meta,
                "artifacts": {
                    "trace_jsonl": artifact_manifest.trace_jsonl,
                    "events_jsonl": artifact_manifest.events_jsonl,
                    "cache_db": artifact_manifest.cache_db,
                    "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                },
                "evidence_chain": callbacks.evidence_chain_meta(),
            },
            "batch": {
                "mode": batch_mode,
                "devices_requested": device_names,
                "devices_completed": sorted({row["device_name"] for row in combined_rows}),
                "devices_skipped": skipped,
            },
            "experiments": batch_experiments,
            "device_summary": combined_rows,
            "comparative": {
                "space_claim_delta": combined_rows,
            },
        }
        out_json = batch_dir / f"{batch_mode}_summary.json"
        out_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        out_csv = batch_dir / f"{batch_mode}_summary.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            if combined_rows:
                cols = list(combined_rows[0].keys())
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                for row in combined_rows:
                    writer.writerow(row)

        print("Wrote:")
        print(" ", out_json.resolve())
        print(" ", out_csv.resolve())

    run_transpile = args.run in {"all", "transpile_only"}
    run_noisy = args.run in {"all", "noisy_sim"}

    if run_transpile:
        if args.replay_trace and "transpile_only" not in replay_rows_by_batch:
            write_skipped_batch_summary(
                batch_mode="transpile_only",
                requested_devices=callbacks.parse_csv_tokens(args.transpile_devices),
                reason=f"replay trace does not contain batch 'transpile_only': {args.replay_trace}",
            )
        else:
            run_batch(
                batch_mode="transpile_only",
                device_names=callbacks.parse_csv_tokens(args.transpile_devices),
                space_name=(
                    replay_space_by_batch.get("transpile_only", plan.transpile_space)
                    if args.replay_trace
                    else plan.transpile_space
                ),
                metric_names=["circuit_depth", "two_qubit_count"],
                claim_pairs=callbacks.parse_claim_pairs(args.transpile_claim_pairs),
                direction=HigherIsBetter.NO,
                noise_model_mode="none",
                replay_device_rows=replay_rows_by_batch.get("transpile_only") if args.replay_trace else None,
                replay_keys=replay_keys_by_batch.get("transpile_only") if args.replay_trace else None,
            )

    if run_noisy:
        noisy_devices = callbacks.parse_csv_tokens(args.noisy_devices)
        if sys.version_info >= (3, 13) and not args.replay_trace:
            write_skipped_batch_summary(
                batch_mode="noisy_sim",
                requested_devices=noisy_devices,
                reason="noisy_sim skipped on Python 3.13 due known native qiskit-aer runtime instability in this environment.",
            )
        elif args.replay_trace and "noisy_sim" not in replay_rows_by_batch:
            write_skipped_batch_summary(
                batch_mode="noisy_sim",
                requested_devices=noisy_devices,
                reason=f"replay trace does not contain batch 'noisy_sim': {args.replay_trace}",
            )
        else:
            backend_cfg = spec_payload.get("backend", {}) if isinstance(spec_payload, dict) else {}
            noise_model_mode = parse_noise_model_mode(backend_cfg)
            run_batch(
                batch_mode="noisy_sim",
                device_names=noisy_devices,
                space_name=replay_space_by_batch.get("noisy_sim", plan.noisy_space) if args.replay_trace else plan.noisy_space,
                metric_names=["objective"],
                claim_pairs=callbacks.parse_claim_pairs(args.noisy_claim_pairs),
                direction=HigherIsBetter.YES,
                noise_model_mode=noise_model_mode,
                replay_device_rows=replay_rows_by_batch.get("noisy_sim") if args.replay_trace else None,
                replay_keys=replay_keys_by_batch.get("noisy_sim") if args.replay_trace else None,
            )

    return MultideviceExecutionResult(
        suite_name=suite_name,
        artifact_manifest=artifact_manifest,
        trace_path=trace_path,
        global_trace_index=global_trace_index,
        global_device_summary=global_device_summary,
    )


def evaluate_rows_for_claim(
    *,
    rows_by_graph: dict[str, list[ScoreRow]],
    method_a: str,
    method_b: str,
    deltas: list[float],
    baseline_key: ConfigKey,
    direction: HigherIsBetter,
    stability_threshold: float,
    confidence_level: float,
) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    per_graph: dict[str, dict[str, object]] = {}
    agg_stability_successes: dict[float, int] = defaultdict(int)
    agg_stability_total: dict[float, int] = defaultdict(int)
    agg_holds_successes: dict[float, int] = defaultdict(int)
    agg_holds_total: dict[float, int] = defaultdict(int)
    decisions_per_delta: dict[float, list[str]] = defaultdict(list)
    flip_rates_per_delta: dict[float, list[float]] = defaultdict(list)

    for graph_id, rows in rows_by_graph.items():
        paired = collect_paired_scores(rows, method_a, method_b)
        if baseline_key not in paired:
            continue
        baseline_a, baseline_b = paired[baseline_key]
        perturbed = [v for k, v in paired.items() if k != baseline_key]

        graph_delta = []
        for delta in deltas:
            claim = RankingClaim(method_a=method_a, method_b=method_b, delta=delta, direction=direction)
            summary = compute_rank_flip_summary(
                claim=claim,
                baseline_score_a=baseline_a,
                baseline_score_b=baseline_b,
                perturbed_scores=perturbed,
            )
            stable_successes = summary.total - summary.flips
            stability_est = estimate_binomial_rate(stable_successes, summary.total, confidence=confidence_level)
            decision = conservative_stability_decision(stability_est, stability_threshold=stability_threshold).value
            holds_successes = sum(1 for pair in paired.values() if claim.holds(*pair))

            agg_stability_successes[delta] += stable_successes
            agg_stability_total[delta] += summary.total
            agg_holds_successes[delta] += holds_successes
            agg_holds_total[delta] += len(paired)
            decisions_per_delta[delta].append(decision)
            flip_rates_per_delta[delta].append(summary.flip_rate)

            graph_delta.append(
                {
                    "delta": delta,
                    "total": summary.total,
                    "flips": summary.flips,
                    "flip_rate": summary.flip_rate,
                    "stability_hat": stability_est.rate,
                    "stability_ci_low": stability_est.ci_low,
                    "stability_ci_high": stability_est.ci_high,
                    "decision": decision,
                    "claim_holds_count": holds_successes,
                    "claim_total_count": len(paired),
                    "claim_holds_rate": (holds_successes / len(paired)) if paired else 0.0,
                }
            )

        per_graph[graph_id] = {
            "sampled_configurations": len(paired),
            "delta_sweep": graph_delta,
        }

    overall = []
    for delta in deltas:
        stability_est = estimate_binomial_rate(
            agg_stability_successes[delta],
            agg_stability_total[delta],
            confidence=confidence_level,
        )
        holds_est = estimate_binomial_rate(
            agg_holds_successes[delta],
            agg_holds_total[delta],
            confidence=confidence_level,
        )
        overall.append(
            {
                "delta": delta,
                "n_instances": len(per_graph),
                "n_claim_evals": agg_stability_total[delta],
                "flip_rate_mean": (
                    sum(flip_rates_per_delta[delta]) / len(flip_rates_per_delta[delta]) if flip_rates_per_delta[delta] else 0.0
                ),
                "flip_rate_max": max(flip_rates_per_delta[delta]) if flip_rates_per_delta[delta] else 0.0,
                "flip_rate_min": min(flip_rates_per_delta[delta]) if flip_rates_per_delta[delta] else 0.0,
                "holds_rate_mean": holds_est.rate,
                "holds_rate_ci_low": holds_est.ci_low,
                "holds_rate_ci_high": holds_est.ci_high,
                "stability_hat": stability_est.rate,
                "stability_ci_low": stability_est.ci_low,
                "stability_ci_high": stability_est.ci_high,
                "decision": conservative_stability_decision(
                    stability_est,
                    stability_threshold=stability_threshold,
                ).value,
                "decision_counts": {
                    "stable": sum(1 for d in decisions_per_delta[delta] if d == "stable"),
                    "unstable": sum(1 for d in decisions_per_delta[delta] if d == "unstable"),
                    "inconclusive": sum(1 for d in decisions_per_delta[delta] if d == "inconclusive"),
                },
            }
        )

    return per_graph, overall
