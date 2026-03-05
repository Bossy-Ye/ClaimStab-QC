from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping

from qiskit.transpiler import CouplingMap

from claimstab.claims.decision import decision_in_top_k, evaluate_decision_claim
from claimstab.claims.diagnostics import (
    aggregate_lockdown_recommendations,
    build_conditional_robustness_summary,
    compute_stability_vs_shots,
    compute_effect_diagnostics,
    conditional_rank_flip_summary,
    minimum_shots_for_stable,
    rank_flip_root_cause_by_dimension,
    single_knob_lockdown_recommendation,
)
from claimstab.claims.distribution import evaluate_distribution_claim
from claimstab.claims.evaluation import collect_paired_scores, perturbation_key
from claimstab.claims.ranking import HigherIsBetter, RankingClaim, compute_rank_flip_summary
from claimstab.claims.stability import (
    ci_width,
    conservative_stability_decision,
    estimate_binomial_rate,
    estimate_clustered_stability,
)
from claimstab.io.runtime_meta import collect_runtime_metadata
from claimstab.analysis.rq import build_rq_summary
from claimstab.baselines.naive import evaluate_naive_baseline
from claimstab.cache.store import CacheStore
from claimstab.core import ArtifactManifest, ExecutionEvent, JsonlEventLogger, TraceIndex, TraceRecord
from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.evidence import build_cep_protocol_meta, build_experiment_cep_record
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.sampling import SamplingPolicy, adaptive_sample_configs, ensure_config_included, sample_configs
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

LEGACY_SUITE_ALIASES = {
    "day1",
    "day2",
    "day2_large",
}

SPACE_ALIASES = {
    "baseline": "baseline",
    "compilation_only": "compilation_only",
    "sampling_only": "sampling_only",
    "combined_light": "combined_light",
    "day1_default": "baseline",
}

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
    deltas = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        deltas.append(float(token))
    if not deltas:
        raise ValueError("At least one delta must be provided")
    return deltas


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
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items


def try_load_spec(path: str | None) -> dict:
    if not path:
        return {}
    return load_spec(path, validate=False)


def parse_claim_pairs(raw: str, fallback_pair: tuple[str, str]) -> list[tuple[str, str]]:
    if not raw.strip():
        return [fallback_pair]
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
        pairs.append((method_a, method_b))
    if not pairs:
        raise ValueError("At least one claim pair must be provided")
    return pairs


def canonical_suite_name(name: str) -> str:
    key = name.strip().lower()
    canonical = SUITE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SUITE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown suite '{name}'. Use one of: {valid}.")
    if key in LEGACY_SUITE_ALIASES:
        print(f"[WARN] Suite alias '{name}' is deprecated; using '{canonical}'.")
    return canonical


def canonical_space_name(name: str) -> str:
    key = name.strip()
    canonical = SPACE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SPACE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown space preset '{name}'. Use one of: {valid}.")
    return canonical


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
        "lookup_fields": [
            *EVIDENCE_LOOKUP_FIELDS,
        ],
    }


DIMENSION_NAMES = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]


def write_scores_csv(rows: Iterable[tuple[str, str, ScoreRow]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "suite",
                "space_preset",
                "instance_id",
                "seed_transpiler",
                "optimization_level",
                "layout_method",
                "seed_simulator",
                "shots",
                "method",
                "metric_name",
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
        )

        for suite_name, space_name, r in rows:
            w.writerow(
                [
                    suite_name,
                    space_name,
                    r.instance_id,
                    r.seed_transpiler,
                    r.optimization_level,
                    r.layout_method,
                    r.seed_simulator,
                    r.shots,
                    r.method,
                    r.metric_name,
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


def make_space(preset: str) -> PerturbationSpace:
    if preset == "baseline":
        return PerturbationSpace.conf_level_default()
    if preset == "compilation_only":
        return PerturbationSpace.compilation_only()
    if preset == "sampling_only":
        return PerturbationSpace.sampling_only()
    if preset == "combined_light":
        # Keep combined perturbations small but include multiple shot budgets so
        # the stability-vs-cost section can estimate a trend instead of a single point.
        return PerturbationSpace(
            seeds_transpiler=list(range(10)),
            opt_levels=[0, 1, 2, 3],
            layout_methods=["trivial", "sabre"],
            shots_list=[64, 256, 1024],
            seeds_simulator=[0, 1, 2],
        )
    raise ValueError(f"Unknown preset: {preset}")


def build_baseline_config(space: PerturbationSpace) -> tuple[dict[str, int | str], PerturbationConfig, tuple[int, int, str | None, int, int | None]]:
    first = next(space.iter_configs())
    baseline_cfg = {
        "seed_transpiler": first.compilation.seed_transpiler,
        "optimization_level": first.compilation.optimization_level,
        "layout_method": first.compilation.layout_method,
        "shots": first.execution.shots,
        "seed_simulator": first.execution.seed_simulator,
    }
    baseline_pc = PerturbationConfig(
        compilation=CompilationPerturbation(
            seed_transpiler=baseline_cfg["seed_transpiler"],
            optimization_level=baseline_cfg["optimization_level"],
            layout_method=str(baseline_cfg["layout_method"]),
        ),
        execution=ExecutionPerturbation(
            shots=baseline_cfg["shots"],
            seed_simulator=baseline_cfg["seed_simulator"],
        ),
    )
    baseline_key = (
        baseline_cfg["seed_transpiler"],
        baseline_cfg["optimization_level"],
        baseline_cfg["layout_method"],
        baseline_cfg["shots"],
        baseline_cfg["seed_simulator"],
    )
    return baseline_cfg, baseline_pc, baseline_key


def config_key(pc: PerturbationConfig) -> tuple[int, int, str | None, int, int | None]:
    return (
        pc.compilation.seed_transpiler,
        pc.compilation.optimization_level,
        pc.compilation.layout_method,
        pc.execution.shots,
        pc.execution.seed_simulator,
    )


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
) -> tuple[dict[str, int | str | None], tuple[int, int, str | None, int, int | None]]:
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


def filter_rows_by_keys(
    rows: list[ScoreRow],
    allowed_keys: set[tuple[int, int, str | None, int, int | None]],
) -> list[ScoreRow]:
    return [row for row in rows if perturbation_key(row) in allowed_keys]


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
    ordered_non_baseline = [pc for pc in sampled_configs if config_key(pc) != baseline_key]

    def eval_prefix(prefix_cfgs: list[PerturbationConfig]) -> tuple[float, float]:
        prefix_keys = {config_key(pc) for pc in prefix_cfgs}
        widths: list[float] = []
        for delta in deltas:
            claim = RankingClaim(method_a=method_a, method_b=method_b, delta=delta)
            successes = 0
            total = 0
            for paired in paired_scores_by_graph.values():
                if baseline_key not in paired:
                    continue
                baseline_relation = claim.relation(*paired[baseline_key])
                for key in prefix_keys:
                    if key not in paired:
                        continue
                    total += 1
                    if claim.relation(*paired[key]) == baseline_relation:
                        successes += 1
            if total > 0:
                widths.append(ci_width(estimate_binomial_rate(successes=successes, total=total, confidence=confidence_level)))
        if not widths:
            return 0.0, 1.0
        return 0.0, max(widths)

    if not ordered_non_baseline:
        return {baseline_key}, {
            "enabled": True,
            "target_ci_width": target_ci_width,
            "achieved_ci_width": None,
            "stop_reason": "no_candidate_configs",
            "selected_configurations_without_baseline": 0,
            "selected_configurations_with_baseline": 1,
            "evaluated_configurations_without_baseline": 0,
        }

    adaptive = adaptive_sample_configs(
        ordered_non_baseline,
        evaluate_prefix=eval_prefix,
        target_ci_width=target_ci_width,
        min_sample_size=min_sample_size,
        step_size=step_size,
        max_sample_size=len(ordered_non_baseline),
    )
    selected_keys = {config_key(pc) for pc in adaptive.selected_configs}
    selected_keys.add(baseline_key)
    return selected_keys, {
        "enabled": True,
        "target_ci_width": adaptive.target_ci_width,
        "achieved_ci_width": adaptive.achieved_ci_width,
        "stop_reason": adaptive.stop_reason,
        "selected_configurations_without_baseline": adaptive.evaluated_configs,
        "selected_configurations_with_baseline": len(selected_keys),
        "evaluated_configurations_without_baseline": len(ordered_non_baseline),
        "min_sample_size": min_sample_size,
        "step_size": step_size,
    }


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
    return out


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


def build_coupling_map(num_qubits: int) -> CouplingMap:
    line_edges = [[i, i + 1] for i in range(num_qubits - 1)]
    reverse_edges = [[i + 1, i] for i in range(num_qubits - 1)]
    return CouplingMap(line_edges + reverse_edges)


def aggregate_factor_attribution(per_graph_summary: dict[str, dict[str, object]], deltas: list[float], top_k: int) -> dict[str, object]:
    combined: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
    top_by_delta: dict[str, list[dict[str, object]]] = {}
    lockdown_by_delta: dict[str, list[dict[str, object]]] = {}

    for delta in deltas:
        dkey = str(delta)
        dim_totals: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"total": 0, "flips": 0}))
        flip_events: list[dict[str, object]] = []
        lockdown_rows: list[dict[str, object]] = []

        for graph_id, payload in per_graph_summary.items():
            attrib = payload.get("factor_attribution", {}).get(dkey, {})
            by_dimension = attrib.get("by_dimension", {})
            for dim_name, values in by_dimension.items():
                for value, stats in values.items():
                    dim_totals[dim_name][value]["total"] += int(stats.get("total", 0))
                    dim_totals[dim_name][value]["flips"] += int(stats.get("flips", 0))

            for event in attrib.get("top_flip_configs", []):
                event_copy = dict(event)
                event_copy["graph_id"] = graph_id
                flip_events.append(event_copy)
            lockdown = payload.get("lockdown_recommendation", {}).get(dkey)
            if isinstance(lockdown, dict):
                lockdown_rows.append(lockdown)

        dim_rates: dict[str, dict[str, dict[str, float | int]]] = {}
        for dim_name, values in dim_totals.items():
            dim_rates[dim_name] = {}
            for value, counts in sorted(values.items()):
                total = counts["total"]
                flips = counts["flips"]
                dim_rates[dim_name][value] = {
                    "total": total,
                    "flips": flips,
                    "flip_rate": 0.0 if total == 0 else flips / total,
                }

        combined[dkey] = dim_rates
        top_by_delta[dkey] = sorted(
            flip_events,
            key=lambda e: (float(e.get("flip_severity", 0.0)), abs(float(e.get("margin_shift_vs_baseline", 0.0)))),
            reverse=True,
        )[:max(0, top_k)]
        lockdown_by_delta[dkey] = aggregate_lockdown_recommendations(lockdown_rows, top_k=top_k)

    return {
        "by_delta_dimension": combined,
        "top_unstable_configs_by_delta": top_by_delta,
        "top_lockdown_recommendations_by_delta": lockdown_by_delta,
    }


def build_method_scores_by_key(rows: list[ScoreRow]) -> dict[tuple[int, int, str | None, int, int | None], dict[str, float]]:
    by_key: dict[tuple[int, int, str | None, int, int | None], dict[str, float]] = defaultdict(dict)
    for row in rows:
        by_key[perturbation_key(row)][row.method] = row.score
    return by_key


def _bucket_problem_size(value: int) -> str:
    if value <= 6:
        return "small"
    if value <= 10:
        return "medium"
    return "large"


def _bucket_density(value: float) -> str:
    if value <= 0.25:
        return "sparse"
    if value <= 0.45:
        return "mid"
    return "dense"


def _bucket_transpiled_depth(depth: int | None) -> str | None:
    if depth is None:
        return None
    if depth <= 40:
        return "depth_low"
    if depth <= 120:
        return "depth_mid"
    return "depth_high"


def _bucket_two_qubit_count(two_q: int | None) -> str | None:
    if two_q is None:
        return None
    if two_q <= 20:
        return "twoq_low"
    if two_q <= 60:
        return "twoq_mid"
    return "twoq_high"


def _derive_instance_strata(
    *,
    task_kind: str,
    graph_id: str,
    instance: Any | None,
    graph_rows: list[ScoreRow],
    method_name: str,
    baseline_key: tuple[int, int, str | None, int, int | None],
) -> dict[str, object]:
    strata: dict[str, object] = {}

    payload = getattr(instance, "payload", None) if instance is not None else None
    meta = getattr(instance, "meta", None) if instance is not None else None

    if task_kind == "maxcut":
        n_nodes = getattr(payload, "num_nodes", None)
        edges = getattr(payload, "edges", None)
        if isinstance(n_nodes, int) and n_nodes > 0:
            strata["graph_size_bucket"] = _bucket_problem_size(int(n_nodes))
        if isinstance(n_nodes, int) and n_nodes > 1 and isinstance(edges, list):
            density = (2.0 * len(edges)) / float(n_nodes * (n_nodes - 1))
            strata["edge_density_bucket"] = _bucket_density(density)
        if str(graph_id).startswith("ring"):
            strata["instance_family"] = "ring"
        elif str(graph_id).startswith("er_"):
            strata["instance_family"] = "erdos_renyi"
        else:
            strata["instance_family"] = "other_graph"
    elif task_kind == "bv":
        hidden = getattr(payload, "hidden_string", None)
        if isinstance(hidden, str) and hidden:
            strata["input_size_bucket"] = _bucket_problem_size(len(hidden))
        strata["instance_family"] = "bv"
    elif task_kind == "ghz":
        n_qubits = getattr(payload, "num_qubits", None)
        if not isinstance(n_qubits, int) and isinstance(meta, dict):
            mq = meta.get("num_qubits")
            if isinstance(mq, int):
                n_qubits = mq
        if isinstance(n_qubits, int) and n_qubits > 0:
            strata["input_size_bucket"] = _bucket_problem_size(n_qubits)
        strata["instance_family"] = "ghz"

    baseline_depth: int | None = None
    baseline_twoq: int | None = None
    for row in graph_rows:
        if row.method != method_name:
            continue
        if perturbation_key(row) != baseline_key:
            continue
        baseline_depth = int(row.transpiled_depth)
        baseline_twoq = int(row.two_qubit_count) if row.two_qubit_count is not None else None
        break
    depth_bucket = _bucket_transpiled_depth(baseline_depth)
    twoq_bucket = _bucket_two_qubit_count(baseline_twoq)
    if depth_bucket is not None:
        strata["transpiled_depth_bucket"] = depth_bucket
    if twoq_bucket is not None:
        strata["two_qubit_count_bucket"] = twoq_bucket
    if not strata:
        strata["instance_family"] = "all"
    return strata


def evaluate_auxiliary_claim_examples(
    *,
    method_scores_by_key: dict[tuple[int, int, str | None, int, int | None], dict[str, float]],
    baseline_key: tuple[int, int, str | None, int, int | None],
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    if baseline_key not in method_scores_by_key:
        return {}

    keys = sorted(method_scores_by_key)
    baseline_scores = method_scores_by_key[baseline_key]
    selected_label = sorted(baseline_scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    accepted_outcomes = []
    for key in keys:
        scores = method_scores_by_key[key]
        accepted_outcomes.append(
            decision_in_top_k(
                selected_label=selected_label,
                scores=scores,
                k=2,
                higher_is_better=True,
            )
        )
    decision_res = evaluate_decision_claim(
        accepted_outcomes,
        stability_threshold=stability_threshold,
        confidence=confidence_level,
    )

    winners: dict[tuple[int, int, str | None, int, int | None], str] = {}
    for key in keys:
        scores = method_scores_by_key[key]
        winners[key] = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    shots_values = sorted({int(k[3]) for k in keys})
    low_keys: list[tuple[int, int, str | None, int, int | None]]
    high_keys: list[tuple[int, int, str | None, int, int | None]]
    if len(shots_values) >= 2:
        low_keys = [k for k in keys if int(k[3]) == shots_values[0]]
        high_keys = [k for k in keys if int(k[3]) == shots_values[-1]]
        observed_group = f"shots={shots_values[0]}"
        reference_group = f"shots={shots_values[-1]}"
    else:
        low_keys = [k for k in keys if (int(k[4]) if k[4] is not None else 0) % 2 == 0]
        high_keys = [k for k in keys if (int(k[4]) if k[4] is not None else 0) % 2 == 1]
        observed_group = "seed_simulator_even"
        reference_group = "seed_simulator_odd"

    observed_counts: dict[str, int] = defaultdict(int)
    reference_counts: dict[str, int] = defaultdict(int)
    for k in low_keys:
        observed_counts[winners[k]] += 1
    for k in high_keys:
        reference_counts[winners[k]] += 1

    distribution_payload: dict[str, object] = {}
    if observed_counts and reference_counts:
        dist_res = evaluate_distribution_claim(
            observed_counts=observed_counts,
            reference_counts=reference_counts,
            epsilon=0.20,
            primary_distance="js",
            sanity_distance="tvd",
        )
        distribution_payload = {
            "observed_group": observed_group,
            "reference_group": reference_group,
            "observed_counts": dict(observed_counts),
            "reference_counts": dict(reference_counts),
            "epsilon": dist_res.epsilon,
            "primary_distance": dist_res.primary_distance,
            "primary_value": dist_res.primary_value,
            "primary_holds": dist_res.primary_holds,
            "sanity_distance": dist_res.sanity_distance,
            "sanity_value": dist_res.sanity_value,
            "sanity_holds": dist_res.sanity_holds,
            "distances_agree": dist_res.distances_agree,
        }

    return {
        "decision_example": {
            "selected_label": selected_label,
            "rule": "selected baseline winner remains in top-2 under perturbation",
            "accepted": decision_res.accepted,
            "total": decision_res.total,
            "acceptance_rate": decision_res.acceptance_rate,
            "ci_low": decision_res.ci_low,
            "ci_high": decision_res.ci_high,
            "decision": decision_res.decision.value,
        },
        "distribution_example": distribution_payload,
    }


def build_robustness_map_artifact(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    by_experiment: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        exp_id = str(exp.get("experiment_id", "unknown"))
        claim = exp.get("claim", {})
        if not isinstance(claim, dict) or str(claim.get("type", "ranking")) != "ranking":
            continue
        overall = exp.get("overall", {})
        if not isinstance(overall, dict):
            continue
        robustness = overall.get("conditional_robustness", {})
        if not isinstance(robustness, dict):
            continue
        by_delta = robustness.get("cells_by_delta", {})
        if not isinstance(by_delta, dict):
            continue
        exp_rows: dict[str, list[dict[str, Any]]] = {}
        for delta, rows in by_delta.items():
            if not isinstance(rows, list):
                continue
            dkey = str(delta)
            mapped_rows: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                out_row = {
                    "experiment_id": exp_id,
                    "delta": dkey,
                    "conditions": row.get("conditions", {}),
                    "n_eval": int(row.get("n_eval", 0)),
                    "flip_rate": float(row.get("flip_rate", 0.0)),
                    "stability_hat": float(row.get("stability_hat", 0.0)),
                    "stability_ci_low": float(row.get("stability_ci_low", 0.0)),
                    "stability_ci_high": float(row.get("stability_ci_high", 0.0)),
                    "decision": str(row.get("decision", "inconclusive")),
                }
                mapped_rows.append(out_row)
                cells.append(out_row)
            mapped_rows.sort(
                key=lambda item: (
                    item["decision"] == "stable",
                    int(item["n_eval"]),
                    float(item["stability_ci_low"]),
                ),
                reverse=True,
            )
            exp_rows[dkey] = mapped_rows
        by_experiment[exp_id] = exp_rows

    cells.sort(
        key=lambda item: (
            str(item["experiment_id"]),
            float(item["delta"]),
            str(item["decision"]) == "stable",
            int(item["n_eval"]),
        ),
        reverse=True,
    )
    return {
        "schema_version": "robustness_map_v1",
        "cell_fields": [
            "experiment_id",
            "delta",
            "conditions",
            "n_eval",
            "stability_hat",
            "stability_ci_low",
            "stability_ci_high",
            "decision",
        ],
        "cells": cells,
        "by_experiment_delta": by_experiment,
    }


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
    direction = HigherIsBetter.YES if higher_is_better else HigherIsBetter.NO
    base_claim = RankingClaim(method_a=method_a, method_b=method_b, delta=0.0, direction=direction)

    paired_scores = collect_paired_scores(rows, method_a, method_b)
    if baseline_key not in paired_scores:
        raise ValueError(f"Baseline key missing from sampled set: {baseline_key}")

    baseline_a, baseline_b = paired_scores[baseline_key]
    perturbed_pairs = [scores for key, scores in paired_scores.items() if key != baseline_key]
    shot_values = sorted({int(key[3]) for key in paired_scores})
    seed_values = sorted({int(key[4]) for key in paired_scores if key[4] is not None})

    by_delta_flip: dict[float, list[float]] = defaultdict(list)
    by_delta_decision: dict[float, list[str]] = defaultdict(list)

    delta_sweep = []
    factor_attribution: dict[str, dict[str, object]] = {}
    lockdown_recommendation: dict[str, dict[str, object]] = {}
    conditional_stability: dict[str, list[dict[str, object]]] = {}
    flip_observations_by_delta: dict[str, list[dict[str, object]]] = {}

    for delta in deltas:
        claim = RankingClaim(
            method_a=base_claim.method_a,
            method_b=base_claim.method_b,
            delta=delta,
            direction=base_claim.direction,
        )
        summary = compute_rank_flip_summary(
            claim=claim,
            baseline_score_a=baseline_a,
            baseline_score_b=baseline_b,
            perturbed_scores=perturbed_pairs,
        )

        stable_count = summary.total - summary.flips
        estimate = estimate_binomial_rate(
            successes=stable_count,
            total=summary.total,
            confidence=confidence_level,
        )
        decision = conservative_stability_decision(
            estimate=estimate,
            stability_threshold=stability_threshold,
        ).value
        baseline_holds = claim.holds(baseline_a, baseline_b)
        baseline_relation = claim.relation(baseline_a, baseline_b)
        baseline_margin = (baseline_a - baseline_b) if higher_is_better else (baseline_b - baseline_a)
        claim_holds_count = sum(1 for pair in paired_scores.values() if claim.holds(*pair))
        claim_holds_rate = claim_holds_count / len(paired_scores) if paired_scores else 0.0

        delta_flip_observations: list[dict[str, object]] = []
        for key, (score_a, score_b) in paired_scores.items():
            if key == baseline_key:
                continue
            perturbed_relation = claim.relation(score_a, score_b)
            margin = (score_a - score_b) if higher_is_better else (score_b - score_a)
            delta_flip_observations.append(
                {
                    "seed_transpiler": int(key[0]),
                    "optimization_level": int(key[1]),
                    "layout_method": key[2],
                    "shots": int(key[3]),
                    "seed_simulator": int(key[4]) if key[4] is not None else None,
                    "baseline_relation": baseline_relation.value,
                    "perturbed_relation": perturbed_relation.value,
                    "is_flip": perturbed_relation != baseline_relation,
                    "margin": margin,
                    "margin_to_threshold": margin - float(delta),
                    "margin_shift_vs_baseline": margin - baseline_margin,
                }
            )
        flip_observations_by_delta[str(delta)] = delta_flip_observations

        delta_record = {
            "delta": delta,
            "total": summary.total,
            "flips": summary.flips,
            "flip_rate": summary.flip_rate,
            "stability_hat": estimate.rate,
            "stability_ci_low": estimate.ci_low,
            "stability_ci_high": estimate.ci_high,
            "decision": decision,
            "baseline_holds": baseline_holds,
            "baseline_relation": baseline_relation.value,
            "claim_holds_count": claim_holds_count,
            "claim_total_count": len(paired_scores),
            "claim_holds_rate": claim_holds_rate,
        }
        delta_sweep.append(delta_record)
        by_delta_flip[delta].append(summary.flip_rate)
        by_delta_decision[delta].append(decision)
        factor_attribution[str(delta)] = rank_flip_root_cause_by_dimension(
            claim=claim,
            baseline_scores=(baseline_a, baseline_b),
            baseline_key=baseline_key,
            paired_scores=paired_scores,
            top_k=top_k_unstable,
        )
        lockdown_recommendation[str(delta)] = single_knob_lockdown_recommendation(
            claim,
            paired_scores=paired_scores,
            baseline_key=baseline_key,
            global_flip_rate=summary.flip_rate,
            stability_threshold=stability_threshold,
            confidence_level=confidence_level,
            top_k=2,
        )

        constraints_to_try: list[dict[str, int | str | None]] = [{}]
        if shot_values:
            constraints_to_try.append({"shots": shot_values[-1]})
            if seed_values:
                constraints_to_try.append({"shots": shot_values[-1], "seed_simulator": seed_values[0]})
        rows_conditional: list[dict[str, object]] = []
        for constraint in constraints_to_try:
            summary_cond = conditional_rank_flip_summary(
                claim,
                paired_scores=paired_scores,
                baseline_key=baseline_key,
                constraints=constraint,
                stability_threshold=stability_threshold,
                confidence_level=confidence_level,
            )
            if summary_cond is None:
                continue
            rows_conditional.append(summary_cond)
        conditional_stability[str(delta)] = rows_conditional

    return {
        "sampled_configurations": len(paired_scores),
        "delta_sweep": delta_sweep,
        "factor_attribution": factor_attribution,
        "lockdown_recommendation": lockdown_recommendation,
        "conditional_stability": conditional_stability,
        "flip_observations_by_delta": flip_observations_by_delta,
        "by_delta_flip": by_delta_flip,
        "by_delta_decision": by_delta_decision,
        "paired_scores": paired_scores,
    }


def evaluate_decision_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method: str,
    top_k: int,
    instance_target_label: str,
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, object]:
    method_rows = [row for row in rows if row.method == method]
    outcomes: list[bool] = []
    failures: list[dict[str, object]] = []
    for row in method_rows:
        counts = row.counts or {}
        try:
            accepted = decision_in_top_k(
                selected_label=instance_target_label,
                scores={str(k): float(v) for k, v in counts.items()},
                k=top_k,
                higher_is_better=True,
            )
        except ValueError:
            accepted = False
        outcomes.append(accepted)
        if not accepted:
            failures.append(
                {
                    "config": {
                        "seed_transpiler": row.seed_transpiler,
                        "optimization_level": row.optimization_level,
                        "layout_method": row.layout_method,
                        "shots": row.shots,
                        "seed_simulator": row.seed_simulator,
                    },
                    "target_label": instance_target_label,
                    "counts": counts,
                }
            )

    result = evaluate_decision_claim(
        outcomes,
        stability_threshold=stability_threshold,
        confidence=confidence_level,
    )
    return {
        "accepted": result.accepted,
        "total": result.total,
        "holds_rate": result.acceptance_rate,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "decision": result.decision.value,
        "top_failures": failures[:5],
    }


def load_rows_from_trace(
    trace_path: Path,
) -> tuple[
    list[tuple[str, str, ScoreRow]],
    dict[str, dict[str, dict[str, list[ScoreRow]]]],
    dict[str, set[tuple[int, int, str | None, int, int | None]]],
]:
    trace_index = TraceIndex.load_jsonl(trace_path)
    all_rows: list[tuple[str, str, ScoreRow]] = []
    rows_by_space_metric_graph: dict[str, dict[str, dict[str, list[ScoreRow]]]] = {}
    keys_by_space: dict[str, set[tuple[int, int, str | None, int, int | None]]] = defaultdict(set)

    for rec in trace_index.records:
        suite_name = str(rec.suite or "replay")
        space_name = str(rec.space_preset or "baseline")
        row = rec.to_score_row()
        all_rows.append((suite_name, space_name, row))
        rows_by_space_metric_graph.setdefault(space_name, {}).setdefault(row.metric_name, {}).setdefault(row.instance_id, []).append(row)
        keys_by_space[space_name].add(perturbation_key(row))

    return all_rows, rows_by_space_metric_graph, keys_by_space


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

    sampling_policy = SamplingPolicy(
        mode=args.sampling_mode,
        sample_size=args.sample_size if args.sampling_mode == "random_k" else args.max_sample_size if args.sampling_mode == "adaptive_ci" else None,
        seed=args.sample_seed,
        target_ci_width=args.target_ci_width if args.sampling_mode == "adaptive_ci" else None,
        max_sample_size=args.max_sample_size if args.sampling_mode == "adaptive_ci" else None,
        min_sample_size=args.min_sample_size,
        step_size=args.step_size,
    )
    runtime_meta = collect_runtime_metadata()
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
                            store_counts=bool(decision_claims),
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
                    claimstab_decision=aggregate_decision,
                    stability_ci_low=stability_estimate.ci_low,
                    stability_ci_high=stability_estimate.ci_high,
                    threshold=args.stability_threshold,
                )
                row["naive_baseline"] = naive
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
                claimstab_decision=aggregate_decision,
                stability_ci_low=stability_estimate.ci_low,
                stability_ci_high=stability_estimate.ci_high,
                threshold=args.stability_threshold,
            )
            summary_row["naive_baseline"] = naive

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
            "generated_by": "examples/claim_stability_demo.py",
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
