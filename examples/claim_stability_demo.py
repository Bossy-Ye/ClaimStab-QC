from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List

from qiskit.transpiler import CouplingMap

from claimstab.claims.decision import decision_in_top_k, evaluate_decision_claim
from claimstab.claims.diagnostics import (
    aggregate_lockdown_recommendations,
    conditional_rank_flip_summary,
    rank_flip_root_cause_by_dimension,
    single_knob_lockdown_recommendation,
)
from claimstab.claims.distribution import evaluate_distribution_claim
from claimstab.claims.evaluation import collect_paired_scores, perturbation_key
from claimstab.claims.ranking import RankingClaim, compute_rank_flip_summary
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.sampling import SamplingPolicy, ensure_config_included, sample_configs
from claimstab.perturbations.space import CompilationPerturbation, ExecutionPerturbation, PerturbationConfig, PerturbationSpace
from claimstab.runners.matrix_runner import MatrixRunner, ScoreRow
from claimstab.runners.qiskit_aer import QiskitAerRunner
from claimstab.tasks.graphs import core_suite, large_suite, standard_suite
from claimstab.tasks.maxcut import MaxCutTask


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
    ap = argparse.ArgumentParser(description="ClaimStab MaxCut demo with batch claim/space evaluation")
    ap.add_argument(
        "--suite",
        default="core",
        help="Suite preset: core | standard | large.",
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
    ap.add_argument("--sampling-mode", choices=["full_factorial", "random_k"], default="full_factorial")
    ap.add_argument("--sample-size", type=int, default=40, help="Used when --sampling-mode random_k")
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--stability-threshold", type=float, default=0.95)
    ap.add_argument("--confidence-level", type=float, default=0.95)
    ap.add_argument("--deltas", default="0.0,0.01,0.05", help="Comma-separated delta values")
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


def parse_csv_tokens(raw: str) -> list[str]:
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items


def try_load_spec(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("YAML spec parsing requires pyyaml. Install with: pip install pyyaml") from exc
    return yaml.safe_load(text) or {}


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
        raise ValueError(f"Unknown space preset '{name}'. Use one of: {valid}.")
    return canonical


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
        return PerturbationSpace.combined_light()
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


def get_suite(name: str):
    if name == "core":
        return core_suite()
    if name == "standard":
        return standard_suite()
    if name == "large":
        return large_suite()
    raise ValueError(f"Unknown suite: {name}")


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


def evaluate_claim_on_rows(
    rows: list[ScoreRow],
    *,
    method_a: str,
    method_b: str,
    deltas: list[float],
    baseline_key: tuple[int, int, str | None, int, int | None],
    stability_threshold: float,
    confidence_level: float,
    top_k_unstable: int,
) -> dict[str, object]:
    base_claim = RankingClaim(method_a=method_a, method_b=method_b, delta=0.0)

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
        claim_holds_count = sum(1 for pair in paired_scores.values() if claim.holds(*pair))
        claim_holds_rate = claim_holds_count / len(paired_scores) if paired_scores else 0.0

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
        "by_delta_flip": by_delta_flip,
        "by_delta_decision": by_delta_decision,
        "paired_scores": paired_scores,
    }


def main() -> None:
    args = parse_args()
    deltas = parse_deltas(args.deltas)
    suite_name = canonical_suite_name(args.suite)
    selected_space_inputs = parse_csv_tokens(args.space_presets) if args.space_presets.strip() else [args.space_preset]
    selected_spaces = [canonical_space_name(name) for name in selected_space_inputs]
    spec_payload = try_load_spec(args.spec)

    out_dir = Path(args.out_dir)
    out_csv = out_dir / "scores.csv"
    out_json = out_dir / "claim_stability.json"

    methods = [
        MethodSpec(name="QAOA_p1", kind="qaoa", p=1),
        MethodSpec(name="QAOA_p2", kind="qaoa", p=2),
        MethodSpec(name="RandomBaseline", kind="random"),
    ]
    method_names = {m.name for m in methods}
    claim_pairs = parse_claim_pairs(args.claim_pairs, (args.method_a, args.method_b))
    for method_a, method_b in claim_pairs:
        if method_a not in method_names or method_b not in method_names:
            raise ValueError(
                f"Unknown claim methods: {method_a}, {method_b}. Available: {sorted(method_names)}"
            )
        if method_a == method_b:
            raise ValueError("Claim pair must compare two different methods.")

    sampling_policy = SamplingPolicy(
        mode=args.sampling_mode,
        sample_size=args.sample_size if args.sampling_mode == "random_k" else None,
        seed=args.sample_seed,
    )
    device_profile = parse_device_profile(spec_payload.get("device_profile") if isinstance(spec_payload, dict) else None)
    resolved_device = resolve_device_profile(device_profile)
    noise_model_mode = parse_noise_model_mode(spec_payload.get("backend") if isinstance(spec_payload, dict) else None)

    suite = get_suite(suite_name)
    runner = MatrixRunner(
        backend=QiskitAerRunner(
            engine=args.backend_engine,
            spot_check_noise=args.spot_check_noise,
            one_qubit_error=args.one_qubit_error,
            two_qubit_error=args.two_qubit_error,
        )
    )

    all_rows: list[tuple[str, str, ScoreRow]] = []
    rows_by_space_and_graph: dict[str, dict[str, list[ScoreRow]]] = {}
    sampling_by_space: dict[str, dict[str, object]] = {}
    baseline_by_space: dict[str, dict[str, int | str]] = {}
    baseline_key_by_space: dict[str, tuple[int, int, str | None, int, int | None]] = {}

    for space_name in selected_spaces:
        space = make_space(space_name)
        baseline_cfg, baseline_pc, baseline_key = build_baseline_config(space)
        sampled_configs = sample_configs(space, sampling_policy)
        sampled_configs = ensure_config_included(sampled_configs, baseline_pc)

        rows_by_graph: dict[str, list[ScoreRow]] = {}
        for inst in suite:
            task = MaxCutTask(instance=inst)
            coupling_map = build_coupling_map(task.graph.num_nodes)
            rows = runner.run(
                task=task,
                methods=methods,
                space=space,
                configs=sampled_configs,
                coupling_map=coupling_map,
                device_profile=resolved_device.profile,
                device_backend=resolved_device.backend,
                noise_model_mode=noise_model_mode,
                device_snapshot_fingerprint=resolved_device.snapshot_fingerprint,
                device_snapshot_summary=resolved_device.snapshot,
            )
            rows_by_graph[task.graph.graph_id] = rows
            all_rows.extend((suite_name, space_name, row) for row in rows)

        rows_by_space_and_graph[space_name] = rows_by_graph
        baseline_by_space[space_name] = baseline_cfg
        baseline_key_by_space[space_name] = baseline_key
        sampling_by_space[space_name] = {
            "suite": suite_name,
            "space_preset": space_name,
            "mode": sampling_policy.mode,
            "sample_size": sampling_policy.sample_size,
            "seed": sampling_policy.seed,
            "sampled_configurations_with_baseline": len(sampled_configs),
            "perturbation_space_size": space.size(),
        }

    experiments: list[dict[str, object]] = []
    comparative_rows: list[dict[str, object]] = []

    for space_name in selected_spaces:
        space_rows = rows_by_space_and_graph[space_name]
        baseline_key = baseline_key_by_space[space_name]

        for method_a, method_b in claim_pairs:
            per_graph_summary: dict[str, dict[str, object]] = {}
            by_delta_flip: dict[float, list[float]] = defaultdict(list)
            by_delta_decision: dict[float, list[str]] = defaultdict(list)
            by_delta_stability_successes: dict[float, int] = defaultdict(int)
            by_delta_stability_totals: dict[float, int] = defaultdict(int)
            by_delta_claim_holds_successes: dict[float, int] = defaultdict(int)
            by_delta_claim_holds_totals: dict[float, int] = defaultdict(int)
            paired_scores_by_graph: dict[str, dict[tuple[int, int, str | None, int, int | None], tuple[float, float]]] = {}
            method_scores_by_graph: dict[str, dict[tuple[int, int, str | None, int, int | None], dict[str, float]]] = {}

            for graph_id, graph_rows in space_rows.items():
                graph_eval = evaluate_claim_on_rows(
                    graph_rows,
                    method_a=method_a,
                    method_b=method_b,
                    deltas=deltas,
                    baseline_key=baseline_key,
                    stability_threshold=args.stability_threshold,
                    confidence_level=args.confidence_level,
                    top_k_unstable=args.top_k_unstable,
                )
                method_scores_by_graph[graph_id] = build_method_scores_by_key(graph_rows)
                paired_scores_by_graph[graph_id] = graph_eval["paired_scores"]
                per_graph_summary[graph_id] = {
                    "sampled_configurations": graph_eval["sampled_configurations"],
                    "delta_sweep": graph_eval["delta_sweep"],
                    "factor_attribution": graph_eval["factor_attribution"],
                    "lockdown_recommendation": graph_eval["lockdown_recommendation"],
                    "conditional_stability": graph_eval["conditional_stability"],
                }
                for delta in deltas:
                    by_delta_flip[delta].extend(graph_eval["by_delta_flip"][delta])
                    by_delta_decision[delta].extend(graph_eval["by_delta_decision"][delta])
                for record in graph_eval["delta_sweep"]:
                    delta_key = float(record["delta"])
                    by_delta_stability_successes[delta_key] += int(record["total"]) - int(record["flips"])
                    by_delta_stability_totals[delta_key] += int(record["total"])
                    by_delta_claim_holds_successes[delta_key] += int(record["claim_holds_count"])
                    by_delta_claim_holds_totals[delta_key] += int(record["claim_total_count"])

            overall_delta = []
            for delta in deltas:
                flips = by_delta_flip[delta]
                decisions = by_delta_decision[delta]
                n = len(flips)
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
                    "n_instances": len(suite),
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
                    "decision_counts": {
                        "stable": sum(1 for d in decisions if d == "stable"),
                        "unstable": sum(1 for d in decisions if d == "unstable"),
                        "inconclusive": sum(1 for d in decisions if d == "inconclusive"),
                    },
                }
                overall_delta.append(row)
                comparative_rows.append(
                    {
                        "space_preset": space_name,
                        "claim_pair": f"{method_a}>{method_b}",
                        **row,
                    }
                )

            diagnostics_summary = aggregate_factor_attribution(
                per_graph_summary=per_graph_summary,
                deltas=deltas,
                top_k=args.top_k_unstable,
            )

            shots_values = sorted({int(k[3]) for paired in paired_scores_by_graph.values() for k in paired.keys()})
            stability_vs_cost_by_delta: dict[str, list[dict[str, object]]] = {}
            minimum_shots_for_stable: dict[str, int | None] = {}
            for delta in deltas:
                claim = RankingClaim(method_a=method_a, method_b=method_b, delta=delta)
                shot_rows: list[dict[str, object]] = []
                for shots in shots_values:
                    agg_flips = 0
                    agg_total = 0
                    for graph_id, paired in paired_scores_by_graph.items():
                        cond = conditional_rank_flip_summary(
                            claim,
                            paired_scores=paired,
                            baseline_key=baseline_key,
                            constraints={"shots": shots},
                            stability_threshold=args.stability_threshold,
                            confidence_level=args.confidence_level,
                        )
                        if cond is None:
                            continue
                        agg_flips += int(cond["flips"])
                        agg_total += int(cond["total"])
                    if agg_total == 0:
                        continue
                    stab_est = estimate_binomial_rate(
                        successes=agg_total - agg_flips,
                        total=agg_total,
                        confidence=args.confidence_level,
                    )
                    shot_rows.append(
                        {
                            "shots": shots,
                            "n_eval": agg_total,
                            "flip_rate": agg_flips / agg_total,
                            "stability_hat": stab_est.rate,
                            "stability_ci_low": stab_est.ci_low,
                            "stability_ci_high": stab_est.ci_high,
                            "decision": conservative_stability_decision(
                                estimate=stab_est,
                                stability_threshold=args.stability_threshold,
                            ).value,
                        }
                    )
                stability_vs_cost_by_delta[str(delta)] = shot_rows
                stable_shots = [int(r["shots"]) for r in shot_rows if r["decision"] == "stable"]
                minimum_shots_for_stable[str(delta)] = min(stable_shots) if stable_shots else None

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

            experiment = {
                "experiment_id": f"{space_name}:{method_a}>{method_b}",
                "claim": {
                    "type": "ranking",
                    "method_a": method_a,
                    "method_b": method_b,
                    "deltas": deltas,
                    "delta_interpretation": "delta is a practical significance threshold; increasing delta makes the claim stricter and may change both holds rate and stability.",
                },
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
                    "graphs": len(suite),
                    "delta_sweep": overall_delta,
                    "diagnostics": diagnostics_summary,
                    "stability_vs_cost": {
                        "cost_metric": "shots",
                        "by_delta": stability_vs_cost_by_delta,
                        "minimum_shots_for_stable": minimum_shots_for_stable,
                    },
                },
                "auxiliary_claims": auxiliary_claims,
            }
            experiments.append(experiment)

    write_scores_csv(all_rows, out_csv)

    payload = {
        "meta": {
            "suite": suite_name,
            "deltas": deltas,
            "methods_available": sorted(method_names),
            "generated_by": "examples/claim_stability_demo.py",
            "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
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
            "claim_pairs": [f"{a}>{b}" for a, b in claim_pairs],
            "num_experiments": len(experiments),
        },
        "experiments": experiments,
        "comparative": {
            "space_claim_delta": comparative_rows,
        },
    }

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

    print("Wrote:")
    print(" ", out_csv.resolve())
    print(" ", out_json.resolve())
    print("Batch:", payload["batch"])


if __name__ == "__main__":
    main()
