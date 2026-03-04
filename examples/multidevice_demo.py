from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from claimstab.cache.store import CacheStore
from claimstab.claims.evaluation import collect_paired_scores
from claimstab.claims.ranking import HigherIsBetter, RankingClaim, compute_rank_flip_summary
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.core import ArtifactManifest, ExecutionEvent, JsonlEventLogger, TraceIndex, TraceRecord
from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.io.runtime_meta import collect_runtime_metadata
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.sampling import SamplingPolicy, ensure_config_included, sample_configs
from claimstab.perturbations.space import CompilationPerturbation, ExecutionPerturbation, PerturbationConfig, PerturbationSpace
from claimstab.runners.matrix_runner import MatrixRunner, ScoreRow
from claimstab.runners.qiskit_aer import QiskitAerRunner
from claimstab.spec import load_spec
from claimstab.tasks.base import BuiltWorkflow
from claimstab.tasks.factory import make_task, parse_methods


SUITE_ALIASES = {
    "core": "core",
    "standard": "standard",
    "large": "large",
    "day1": "core",
    "day2": "standard",
    "day2_large": "large",
}

SPACE_ALIASES = {
    "baseline": "baseline",
    "compilation_only": "compilation_only",
    "sampling_only": "sampling_only",
    "combined_light": "combined_light",
    "day1_default": "baseline",
}


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
    return [token.strip() for token in raw.split(",") if token.strip()]


def parse_deltas(raw: str) -> list[float]:
    vals = [float(t) for t in parse_csv_tokens(raw)]
    if not vals:
        raise ValueError("At least one delta must be provided.")
    return vals


def parse_claim_pairs(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for token in parse_csv_tokens(raw):
        if ">" in token:
            left, right = token.split(">", 1)
        elif ":" in token:
            left, right = token.split(":", 1)
        else:
            raise ValueError(f"Invalid claim pair token '{token}'. Use MethodA>MethodB.")
        a = left.strip()
        b = right.strip()
        if not a or not b:
            raise ValueError(f"Invalid claim pair token '{token}'.")
        if a == b:
            raise ValueError("Claim pair must compare different methods.")
        pairs.append((a, b))
    if not pairs:
        raise ValueError("At least one claim pair is required.")
    return pairs


def canonical_suite_name(name: str) -> str:
    key = name.strip()
    canonical = SUITE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SUITE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown suite '{name}'. Use one of: {valid}.")
    return canonical


def canonical_space_name(name: str) -> str:
    key = name.strip()
    canonical = SPACE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SPACE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown space '{name}'. Use one of: {valid}.")
    return canonical


def make_space(name: str) -> PerturbationSpace:
    if name == "baseline":
        return PerturbationSpace.conf_level_default()
    if name == "compilation_only":
        return PerturbationSpace.compilation_only()
    if name == "sampling_only":
        return PerturbationSpace.sampling_only()
    if name == "combined_light":
        return PerturbationSpace.combined_light()
    raise ValueError(f"Unknown space '{name}'")


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
    first = next(space.iter_configs())
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
    baseline_key = (
        first.compilation.seed_transpiler,
        first.compilation.optimization_level,
        first.compilation.layout_method,
        first.execution.shots,
        first.execution.seed_simulator,
    )
    baseline_dict = {
        "seed_transpiler": first.compilation.seed_transpiler,
        "optimization_level": first.compilation.optimization_level,
        "layout_method": first.compilation.layout_method,
        "shots": first.execution.shots,
        "seed_simulator": first.execution.seed_simulator,
    }
    return baseline_pc, baseline_key, baseline_dict


def key_sort_value(key: tuple[int, int, str | None, int, int | None]) -> tuple[int, int, str, int, int]:
    return (
        int(key[0]),
        int(key[1]),
        "" if key[2] is None else str(key[2]),
        int(key[3]),
        -1 if key[4] is None else int(key[4]),
    )


def config_from_key(key: tuple[int, int, str | None, int, int | None]) -> PerturbationConfig:
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


def baseline_from_keys(
    keys: set[tuple[int, int, str | None, int, int | None]],
) -> tuple[tuple[int, int, str | None, int, int | None], dict[str, int | str | None]]:
    if not keys:
        raise ValueError("Cannot infer baseline from empty key set.")
    baseline_key = sorted(keys, key=key_sort_value)[0]
    baseline_dict: dict[str, int | str | None] = {
        "seed_transpiler": int(baseline_key[0]),
        "optimization_level": int(baseline_key[1]),
        "layout_method": baseline_key[2],
        "shots": int(baseline_key[3]),
        "seed_simulator": None if baseline_key[4] is None else int(baseline_key[4]),
    }
    return baseline_key, baseline_dict


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


def load_rows_from_trace(
    trace_path: Path,
) -> tuple[
    str,
    dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]],
    dict[str, set[tuple[int, int, str | None, int, int | None]]],
    dict[str, str],
]:
    trace_index = TraceIndex.load_jsonl(trace_path)
    rows_by_batch: dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]] = {}
    keys_by_batch: dict[str, set[tuple[int, int, str | None, int, int | None]]] = defaultdict(set)
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
        keys_by_batch[batch_mode].add(
            (
                row.seed_transpiler,
                row.optimization_level,
                row.layout_method,
                row.shots,
                row.seed_simulator,
            )
        )
        space_by_batch.setdefault(batch_mode, space_name)

    suite_name = sorted(suites)[0] if suites else "replay"
    return suite_name, rows_by_batch, keys_by_batch, space_by_batch


def evaluate_rows_for_claim(
    *,
    rows_by_graph: dict[str, list[ScoreRow]],
    method_a: str,
    method_b: str,
    deltas: list[float],
    baseline_key,
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
                    sum(flip_rates_per_delta[delta]) / len(flip_rates_per_delta[delta])
                    if flip_rates_per_delta[delta]
                    else 0.0
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


def write_rows_csv(rows: Iterable[ScoreRow], out_csv: Path) -> None:
    fields = [
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
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
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


def try_load_spec(path: str | None) -> dict:
    if not path:
        return {}
    return load_spec(path, validate=False)


def main() -> None:
    args = parse_args()
    deltas = parse_deltas(args.deltas)
    transpile_space = canonical_space_name(args.transpile_space)
    noisy_space = canonical_space_name(args.noisy_space)
    runtime_meta = collect_runtime_metadata()
    spec_payload = try_load_spec(args.spec)
    task_plugin, task_suite = make_task(
        spec_payload.get("task") if isinstance(spec_payload, dict) else None,
        default_suite=args.suite,
    )
    suite_name = str(spec_payload.get("suite", task_suite)).strip() if isinstance(spec_payload, dict) else str(task_suite)
    suite = task_plugin.instances(suite_name)
    if not suite:
        raise ValueError(f"Task '{getattr(task_plugin, 'name', 'unknown')}' returned an empty suite for '{suite_name}'.")

    methods = parse_methods(spec_payload if isinstance(spec_payload, dict) else {})
    method_names = {m.name for m in methods}
    num_qubits_by_instance: dict[str, int] = {}
    for inst in suite:
        num_qubits_by_instance[inst.instance_id] = BoundTask(task_plugin, inst).infer_num_qubits(methods)

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

    global_device_summary: list[dict[str, object]] = []
    replay_rows_by_batch: dict[str, dict[str, dict[str, dict[str, list[ScoreRow]]]]] = {}
    replay_keys_by_batch: dict[str, set[tuple[int, int, str | None, int, int | None]]] = {}
    replay_space_by_batch: dict[str, str] = {}
    global_trace_index = TraceIndex() if not args.replay_trace else None
    if args.replay_trace:
        replay_path = Path(args.replay_trace)
        replay_suite_name, replay_rows_by_batch, replay_keys_by_batch, replay_space_by_batch = load_rows_from_trace(replay_path)
        suite_name = replay_suite_name
        trace_path = replay_path
        artifact_manifest = ArtifactManifest(
            trace_jsonl=str(trace_path.resolve()),
            events_jsonl=str(events_path.resolve()) if events_path is not None else None,
            cache_db=str(cache_path.resolve()) if cache_path is not None else None,
        )

    def write_skipped_batch_summary(*, batch_mode: str, requested_devices: list[str], reason: str) -> None:
        batch_dir = out_root / batch_mode
        batch_dir.mkdir(parents=True, exist_ok=True)
        summary_payload = {
            "meta": {
                "suite": suite_name,
                "batch_mode": batch_mode,
                "generated_by": "examples/multidevice_demo.py",
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                "runtime": runtime_meta,
                "artifacts": {
                    "trace_jsonl": artifact_manifest.trace_jsonl,
                    "events_jsonl": artifact_manifest.events_jsonl,
                    "cache_db": artifact_manifest.cache_db,
                    "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                },
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
        replay_keys: set[tuple[int, int, str | None, int, int | None]] | None = None,
    ):
        batch_dir = out_root / batch_mode
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
                for d in replay_device_list:
                    for metric_map in replay_device_rows.get(d, {}).values():
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
            baseline_key, baseline_dict = baseline_from_keys(key_set)
            sampled_configs = [config_from_key(k) for k in sorted(key_set, key=key_sort_value)]
            for device_name in replay_device_list:
                metric_map = replay_device_rows.get(device_name, {})
                for metric_name in metric_names:
                    rows_by_graph = metric_map.get(metric_name, {})
                    all_rows = [row for rows in rows_by_graph.values() for row in rows]
                    if not all_rows:
                        continue
                    csv_name = f"{batch_mode}_{device_name}_{metric_name}.csv"
                    write_rows_csv(all_rows, batch_dir / csv_name)

                    first_row = all_rows[0]
                    for method_a, method_b in claim_pairs:
                        if method_a not in method_names or method_b not in method_names:
                            continue
                        per_graph, overall = evaluate_rows_for_claim(
                            rows_by_graph=rows_by_graph,
                            method_a=method_a,
                            method_b=method_b,
                            deltas=deltas,
                            baseline_key=baseline_key,
                            direction=direction,
                            stability_threshold=args.stability_threshold,
                            confidence_level=args.confidence_level,
                        )
                        exp = {
                            "experiment_id": f"{batch_mode}:{device_name}:{metric_name}:{method_a}>{method_b}",
                            "claim": {
                                "type": "ranking",
                                "metric_name": metric_name,
                                "direction": direction.value,
                                "method_a": method_a,
                                "method_b": method_b,
                                "deltas": deltas,
                            },
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
                        }
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
                        "generated_by": "examples/multidevice_demo.py",
                        "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                        "runtime": runtime_meta,
                        "artifacts": {
                            "trace_jsonl": artifact_manifest.trace_jsonl,
                            "events_jsonl": artifact_manifest.events_jsonl,
                            "cache_db": artifact_manifest.cache_db,
                            "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                        },
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
            space = make_space(space_name)
            baseline_pc, baseline_key, baseline_dict = build_baseline(space)
            sampled_configs = ensure_config_included(
                sample_configs(space, sampling_policy, use_operator_shim=args.use_operator_shim),
                baseline_pc,
            )
            cache_store: CacheStore | None = CacheStore(cache_path) if cache_path is not None else None
            event_logger = make_event_logger(events_path) if events_path is not None else None

            try:
                for device_name in device_names:
                    profile_dict = spec_payload.get("device_profile", {}) if isinstance(spec_payload, dict) else {}
                    profile_dict = dict(profile_dict)
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
                    for inst in suite:
                        graph_qubits = num_qubits_by_instance.get(inst.instance_id)
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
                            task = BoundTask(task_plugin, inst)
                            rows = runner.run(
                                task=task,
                                methods=methods,
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
                                runtime_context={**runtime_context, "batch_mode": batch_mode},
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
                        write_rows_csv(all_rows, batch_dir / csv_name)

                        for method_a, method_b in claim_pairs:
                            if method_a not in method_names or method_b not in method_names:
                                continue
                            per_graph, overall = evaluate_rows_for_claim(
                                rows_by_graph=rows_by_graph,
                                method_a=method_a,
                                method_b=method_b,
                                deltas=deltas,
                                baseline_key=baseline_key,
                                direction=direction,
                                stability_threshold=args.stability_threshold,
                                confidence_level=args.confidence_level,
                            )
                            exp = {
                                "experiment_id": f"{batch_mode}:{device_name}:{metric_name}:{method_a}>{method_b}",
                                "claim": {
                                    "type": "ranking",
                                    "metric_name": metric_name,
                                    "direction": direction.value,
                                    "method_a": method_a,
                                    "method_b": method_b,
                                    "deltas": deltas,
                                },
                                "baseline": baseline_dict,
                                "sampling": {
                                    "suite": suite_name,
                                    "space_preset": space_name,
                                    "mode": sampling_policy.mode,
                                    "sample_size": sampling_policy.sample_size,
                                    "seed": sampling_policy.seed,
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
                            }
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
                            "generated_by": "examples/multidevice_demo.py",
                            "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                            "runtime": runtime_meta,
                            "artifacts": {
                                "trace_jsonl": artifact_manifest.trace_jsonl,
                                "events_jsonl": artifact_manifest.events_jsonl,
                                "cache_db": artifact_manifest.cache_db,
                                "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                            },
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
                "generated_by": "examples/multidevice_demo.py",
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                "runtime": runtime_meta,
                "artifacts": {
                    "trace_jsonl": artifact_manifest.trace_jsonl,
                    "events_jsonl": artifact_manifest.events_jsonl,
                    "cache_db": artifact_manifest.cache_db,
                    "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                },
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
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for row in combined_rows:
                    w.writerow(row)

        print("Wrote:")
        print(" ", out_json.resolve())
        print(" ", out_csv.resolve())

    run_transpile = args.run in {"all", "transpile_only"}
    run_noisy = args.run in {"all", "noisy_sim"}

    if run_transpile:
        if args.replay_trace and "transpile_only" not in replay_rows_by_batch:
            write_skipped_batch_summary(
                batch_mode="transpile_only",
                requested_devices=parse_csv_tokens(args.transpile_devices),
                reason=f"replay trace does not contain batch 'transpile_only': {args.replay_trace}",
            )
        else:
            run_batch(
                batch_mode="transpile_only",
                device_names=parse_csv_tokens(args.transpile_devices),
                space_name=replay_space_by_batch.get("transpile_only", transpile_space) if args.replay_trace else transpile_space,
                metric_names=["circuit_depth", "two_qubit_count"],
                claim_pairs=parse_claim_pairs(args.transpile_claim_pairs),
                direction=HigherIsBetter.NO,
                noise_model_mode="none",
                replay_device_rows=replay_rows_by_batch.get("transpile_only") if args.replay_trace else None,
                replay_keys=replay_keys_by_batch.get("transpile_only") if args.replay_trace else None,
            )

    if run_noisy:
        noisy_devices = parse_csv_tokens(args.noisy_devices)
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
                space_name=replay_space_by_batch.get("noisy_sim", noisy_space) if args.replay_trace else noisy_space,
                metric_names=["objective"],
                claim_pairs=parse_claim_pairs(args.noisy_claim_pairs),
                direction=HigherIsBetter.YES,
                noise_model_mode=noise_model_mode,
                replay_device_rows=replay_rows_by_batch.get("noisy_sim") if args.replay_trace else None,
                replay_keys=replay_keys_by_batch.get("noisy_sim") if args.replay_trace else None,
            )

    if global_trace_index is not None:
        global_trace_index.save_jsonl(trace_path)

    if global_device_summary:
        final_summary = {
            "meta": {
                "suite": suite_name,
                "generated_by": "examples/multidevice_demo.py",
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                "runtime": runtime_meta,
                "artifacts": {
                    "trace_jsonl": artifact_manifest.trace_jsonl,
                    "events_jsonl": artifact_manifest.events_jsonl,
                    "cache_db": artifact_manifest.cache_db,
                    "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                },
            },
            "device_summary": global_device_summary,
            "comparative": {"space_claim_delta": global_device_summary},
        }
        final_json = out_root / "combined_summary.json"
        final_json.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")
        print(" ", final_json.resolve())


if __name__ == "__main__":
    main()
