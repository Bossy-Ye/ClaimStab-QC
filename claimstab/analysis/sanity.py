from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from claimstab.claims.evaluation import collect_paired_scores, perturbation_key
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.pipelines.common import PerturbationKey
from claimstab.pipelines.evaluate import evaluate_claim_on_rows
from claimstab.runners.matrix_runner import ScoreRow


@dataclass(frozen=True)
class LoadedScoreRow:
    suite: str
    space_preset: str
    row: ScoreRow


def _parse_optional_int(value: str | None) -> int | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return int(text)


def _parse_optional_float(value: str | None) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return float(text)


def _parse_optional_str(value: str | None) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def load_score_rows_csv(path: str | Path) -> list[LoadedScoreRow]:
    rows: list[LoadedScoreRow] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                LoadedScoreRow(
                    suite=str(raw.get("suite") or ""),
                    space_preset=str(raw.get("space_preset") or ""),
                    row=ScoreRow(
                        instance_id=str(raw["instance_id"]),
                        seed_transpiler=int(raw["seed_transpiler"]),
                        optimization_level=int(raw["optimization_level"]),
                        layout_method=_parse_optional_str(raw.get("layout_method")),
                        seed_simulator=_parse_optional_int(raw.get("seed_simulator")),
                        shots=int(raw["shots"]),
                        method=str(raw["method"]),
                        metric_name=str(raw.get("metric_name") or "objective"),
                        score=float(raw["score"]),
                        transpiled_depth=int(raw.get("transpiled_depth") or 0),
                        transpiled_size=int(raw.get("transpiled_size") or 0),
                        device_provider=_parse_optional_str(raw.get("device_provider")),
                        device_name=_parse_optional_str(raw.get("device_name")),
                        device_mode=_parse_optional_str(raw.get("device_mode")),
                        device_snapshot_fingerprint=_parse_optional_str(raw.get("device_snapshot_fingerprint")),
                        circuit_depth=_parse_optional_int(raw.get("circuit_depth")),
                        two_qubit_count=_parse_optional_int(raw.get("two_qubit_count")),
                        swap_count=_parse_optional_int(raw.get("swap_count")),
                        transpile_time_ms=_parse_optional_float(raw.get("transpile_time_ms")),
                        execute_time_ms=_parse_optional_float(raw.get("execute_time_ms")),
                        wall_time_ms=_parse_optional_float(raw.get("wall_time_ms")),
                    ),
                )
            )
    return rows


def _baseline_key_from_config(config: Mapping[str, Any]) -> PerturbationKey:
    return (
        int(config["seed_transpiler"]),
        int(config["optimization_level"]),
        _parse_optional_str(config.get("layout_method")),
        int(config["shots"]),
        _parse_optional_int(None if config.get("seed_simulator") is None else str(config.get("seed_simulator"))),
        _parse_optional_str(config.get("init_strategy")),
        _parse_optional_int(None if config.get("init_seed") is None else str(config.get("init_seed"))),
    )


def _group_rows_for_ranking_experiment(
    *,
    rows: list[LoadedScoreRow],
    space_preset: str,
    metric_name: str,
    method_a: str,
    method_b: str,
) -> dict[str, list[ScoreRow]]:
    grouped: dict[str, list[ScoreRow]] = defaultdict(list)
    for loaded in rows:
        if loaded.space_preset != space_preset:
            continue
        row = loaded.row
        if row.metric_name != metric_name:
            continue
        if row.method not in {method_a, method_b}:
            continue
        grouped[row.instance_id].append(row)
    return dict(grouped)


def _decision_reason(*, ci_low: float, ci_high: float, threshold: float) -> str:
    if ci_low >= threshold:
        return "ci_low_meets_threshold"
    if ci_high < threshold:
        return "ci_high_below_threshold"
    return "ci_overlaps_threshold"


def _delta_row_decision_explanation(row: Mapping[str, Any], *, threshold: float) -> dict[str, Any]:
    ci_low = float(row.get("stability_ci_low", 0.0))
    ci_high = float(row.get("stability_ci_high", 0.0))
    return {
        "threshold": threshold,
        "estimate": float(row.get("stability_hat", 0.0)),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "decision": str(row.get("decision", "inconclusive")),
        "reason": _decision_reason(ci_low=ci_low, ci_high=ci_high, threshold=threshold),
    }


def _delta_row_inconclusive_reason(row: Mapping[str, Any], *, threshold: float) -> str | None:
    decision = str(row.get("decision", "inconclusive"))
    if decision != "inconclusive":
        return None
    total = int(row.get("n_claim_evals", 0))
    if total <= 0:
        return "no_candidate_configs"
    return _decision_reason(
        ci_low=float(row.get("stability_ci_low", 0.0)),
        ci_high=float(row.get("stability_ci_high", 0.0)),
        threshold=threshold,
    ).replace("ci_", "ci_")


def _offset_for_baseline_flip(
    *,
    baseline_score_a: float,
    baseline_score_b: float,
    higher_is_better: bool,
    delta_max: float,
    epsilon: float = 1e-6,
) -> float:
    if higher_is_better:
        return (baseline_score_b - delta_max - epsilon) - baseline_score_a
    return (baseline_score_b + delta_max + epsilon) - baseline_score_a


def mutate_ranking_rows(
    *,
    rows_by_graph: Mapping[str, list[ScoreRow]],
    method_a: str,
    method_b: str,
    baseline_key: PerturbationKey,
    deltas: list[float],
    higher_is_better: bool,
    mutation_kind: str,
    offset: float | None = None,
) -> tuple[dict[str, list[ScoreRow]], dict[str, Any]]:
    if mutation_kind not in {"baseline_relation_flip", "swap_methods", "global_score_offset"}:
        raise ValueError(
            "mutation_kind must be one of: baseline_relation_flip, swap_methods, global_score_offset"
        )

    out: dict[str, list[ScoreRow]] = {}
    delta_max = max((float(v) for v in deltas), default=0.0)
    offset_by_graph: dict[str, float] = {}

    for graph_id, graph_rows in rows_by_graph.items():
        if mutation_kind == "swap_methods":
            mutated_rows = []
            for row in graph_rows:
                if row.method == method_a:
                    mutated_rows.append(replace(row, method=method_b))
                elif row.method == method_b:
                    mutated_rows.append(replace(row, method=method_a))
                else:
                    mutated_rows.append(row)
            out[graph_id] = mutated_rows
            continue

        graph_offset = offset
        if mutation_kind == "baseline_relation_flip":
            paired = collect_paired_scores(graph_rows, method_a, method_b)
            if baseline_key not in paired:
                raise ValueError(f"Baseline key missing for graph '{graph_id}'")
            baseline_score_a, baseline_score_b = paired[baseline_key]
            graph_offset = _offset_for_baseline_flip(
                baseline_score_a=baseline_score_a,
                baseline_score_b=baseline_score_b,
                higher_is_better=higher_is_better,
                delta_max=delta_max,
            )
        if graph_offset is None:
            raise ValueError("offset must be provided for mutation_kind='global_score_offset'")

        offset_by_graph[graph_id] = float(graph_offset)
        mutated_rows = []
        for row in graph_rows:
            apply_here = row.method == method_a
            if mutation_kind == "baseline_relation_flip":
                apply_here = apply_here and perturbation_key(row) == baseline_key
            if apply_here:
                mutated_rows.append(replace(row, score=float(row.score) + float(graph_offset)))
            else:
                mutated_rows.append(row)
        out[graph_id] = mutated_rows

    metadata: dict[str, Any] = {"kind": mutation_kind}
    if mutation_kind == "swap_methods":
        metadata["description"] = "swap compared method labels for the ranking claim"
    elif mutation_kind == "baseline_relation_flip":
        metadata["description"] = "flip the baseline relation only, leaving perturbed rows unchanged"
        if offset_by_graph:
            offsets = list(offset_by_graph.values())
            metadata["offset_stats"] = {
                "min": min(offsets),
                "max": max(offsets),
                "mean": sum(offsets) / float(len(offsets)),
            }
            metadata["delta_max"] = delta_max
    else:
        metadata["description"] = "apply a uniform score offset to method_a across all configurations"
        metadata["offset"] = offset

    return out, metadata


def summarize_ranking_rows_by_graph(
    *,
    rows_by_graph: Mapping[str, list[ScoreRow]],
    method_a: str,
    method_b: str,
    deltas: list[float],
    higher_is_better: bool,
    baseline_key: PerturbationKey,
    stability_threshold: float,
    confidence_level: float,
) -> dict[str, Any]:
    per_graph_summary: dict[str, dict[str, Any]] = {}
    by_delta_flip: dict[float, list[float]] = defaultdict(list)
    by_delta_decision: dict[float, list[str]] = defaultdict(list)
    by_delta_stability_successes: dict[float, int] = defaultdict(int)
    by_delta_stability_totals: dict[float, int] = defaultdict(int)
    by_delta_claim_holds_successes: dict[float, int] = defaultdict(int)
    by_delta_claim_holds_totals: dict[float, int] = defaultdict(int)

    for graph_id, graph_rows in rows_by_graph.items():
        graph_eval = evaluate_claim_on_rows(
            graph_rows,
            method_a=method_a,
            method_b=method_b,
            deltas=deltas,
            higher_is_better=higher_is_better,
            baseline_key=baseline_key,
            stability_threshold=stability_threshold,
            confidence_level=confidence_level,
            top_k_unstable=3,
        )
        per_graph_summary[graph_id] = {
            "sampled_configurations": graph_eval["sampled_configurations"],
            "delta_sweep": graph_eval["delta_sweep"],
        }
        for delta in deltas:
            by_delta_flip[delta].extend(graph_eval["by_delta_flip"][delta])
            by_delta_decision[delta].extend(graph_eval["by_delta_decision"][delta])
        for record in graph_eval["delta_sweep"]:
            delta = float(record["delta"])
            by_delta_stability_successes[delta] += int(record["total"]) - int(record["flips"])
            by_delta_stability_totals[delta] += int(record["total"])
            by_delta_claim_holds_successes[delta] += int(record["claim_holds_count"])
            by_delta_claim_holds_totals[delta] += int(record["claim_total_count"])

    overall_delta: list[dict[str, Any]] = []
    for delta in deltas:
        flips = by_delta_flip[delta]
        decisions = by_delta_decision[delta]
        n = len(flips)
        holds_estimate = estimate_binomial_rate(
            successes=by_delta_claim_holds_successes[delta],
            total=by_delta_claim_holds_totals[delta],
            confidence=confidence_level,
        )
        stability_estimate = estimate_binomial_rate(
            successes=by_delta_stability_successes[delta],
            total=by_delta_stability_totals[delta],
            confidence=confidence_level,
        )
        aggregate_decision = conservative_stability_decision(
            estimate=stability_estimate,
            stability_threshold=stability_threshold,
        ).value
        row = {
            "delta": delta,
            "n_instances": len(per_graph_summary),
            "n_claim_evals": by_delta_stability_totals[delta],
            "flip_rate_mean": sum(flips) / float(n) if n else 0.0,
            "flip_rate_max": max(flips) if n else 0.0,
            "flip_rate_min": min(flips) if n else 0.0,
            "holds_rate_mean": holds_estimate.rate,
            "holds_rate_ci_low": holds_estimate.ci_low,
            "holds_rate_ci_high": holds_estimate.ci_high,
            "stability_hat": stability_estimate.rate,
            "stability_ci_low": stability_estimate.ci_low,
            "stability_ci_high": stability_estimate.ci_high,
            "stability_ci_width": max(0.0, stability_estimate.ci_high - stability_estimate.ci_low),
            "decision": aggregate_decision,
            "decision_counts": {
                "stable": sum(1 for value in decisions if value == "stable"),
                "unstable": sum(1 for value in decisions if value == "unstable"),
                "inconclusive": sum(1 for value in decisions if value == "inconclusive"),
            },
        }
        row["decision_explanation"] = _delta_row_decision_explanation(row, threshold=stability_threshold)
        row["inconclusive_reason"] = (
            None
            if aggregate_decision != "inconclusive"
            else "ci_overlaps_threshold"
        )
        overall_delta.append(row)

    return {
        "graphs": len(per_graph_summary),
        "per_graph": per_graph_summary,
        "delta_sweep": overall_delta,
    }


def compare_delta_sweeps(
    original: list[dict[str, Any]],
    mutated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    original_by_delta = {str(row.get("delta")): row for row in original if isinstance(row, dict)}
    mutated_by_delta = {str(row.get("delta")): row for row in mutated if isinstance(row, dict)}
    deltas = sorted(set(original_by_delta) | set(mutated_by_delta), key=lambda value: float(value))
    transitions: list[dict[str, Any]] = []
    severity = {"stable": 2, "inconclusive": 1, "unstable": 0}
    for delta in deltas:
        left = original_by_delta.get(delta, {})
        right = mutated_by_delta.get(delta, {})
        left_decision = str(left.get("decision", "inconclusive"))
        right_decision = str(right.get("decision", "inconclusive"))
        left_hat = float(left.get("stability_hat", 0.0))
        right_hat = float(right.get("stability_hat", 0.0))
        transitions.append(
            {
                "delta": float(delta),
                "original_decision": left_decision,
                "mutated_decision": right_decision,
                "decision_changed": left_decision != right_decision,
                "stability_hat_drop": left_hat - right_hat,
                "mutated_less_stable": severity.get(right_decision, 1) < severity.get(left_decision, 1)
                or right_hat < left_hat,
            }
        )
    return transitions


def build_mutation_sanity_case(
    *,
    experiment: Mapping[str, Any],
    rows: list[LoadedScoreRow],
    mutation_kind: str,
    mutation_offset: float | None = None,
) -> dict[str, Any]:
    claim = experiment.get("claim", {})
    if not isinstance(claim, Mapping) or str(claim.get("type")) != "ranking":
        raise ValueError("build_mutation_sanity_case only supports ranking experiments")

    sampling = experiment.get("sampling", {})
    if not isinstance(sampling, Mapping):
        raise ValueError("experiment.sampling must be a mapping")

    rule = experiment.get("stability_rule", {})
    if not isinstance(rule, Mapping):
        raise ValueError("experiment.stability_rule must be a mapping")

    space_preset = str(sampling.get("space_preset", "unknown"))
    metric_name = str(claim.get("metric_name", "objective"))
    method_a = str(claim.get("method_a"))
    method_b = str(claim.get("method_b"))
    higher_is_better = bool(claim.get("higher_is_better", True))
    deltas = [float(value) for value in claim.get("deltas", [])]
    baseline_key = _baseline_key_from_config(experiment.get("baseline", {}))
    threshold = float(rule.get("threshold", 0.95))
    confidence_level = float(rule.get("confidence_level", 0.95))

    grouped_rows = _group_rows_for_ranking_experiment(
        rows=rows,
        space_preset=space_preset,
        metric_name=metric_name,
        method_a=method_a,
        method_b=method_b,
    )
    original = summarize_ranking_rows_by_graph(
        rows_by_graph=grouped_rows,
        method_a=method_a,
        method_b=method_b,
        deltas=deltas,
        higher_is_better=higher_is_better,
        baseline_key=baseline_key,
        stability_threshold=threshold,
        confidence_level=confidence_level,
    )
    mutated_rows, mutation_meta = mutate_ranking_rows(
        rows_by_graph=grouped_rows,
        method_a=method_a,
        method_b=method_b,
        baseline_key=baseline_key,
        deltas=deltas,
        higher_is_better=higher_is_better,
        mutation_kind=mutation_kind,
        offset=mutation_offset,
    )
    mutated = summarize_ranking_rows_by_graph(
        rows_by_graph=mutated_rows,
        method_a=method_a,
        method_b=method_b,
        deltas=deltas,
        higher_is_better=higher_is_better,
        baseline_key=baseline_key,
        stability_threshold=threshold,
        confidence_level=confidence_level,
    )
    transitions = compare_delta_sweeps(original["delta_sweep"], mutated["delta_sweep"])
    return {
        "experiment_id": str(experiment.get("experiment_id", "unknown")),
        "claim_pair": f"{method_a}>{method_b}",
        "space_preset": space_preset,
        "metric_name": metric_name,
        "mutation": mutation_meta,
        "original": original,
        "mutated": mutated,
        "delta_transitions": transitions,
        "fragility_signal_detected": any(bool(row.get("mutated_less_stable")) for row in transitions),
    }


def summarize_mutation_sanity_run(
    *,
    payload: Mapping[str, Any],
    rows: list[LoadedScoreRow],
    mutation_kinds: list[str],
) -> dict[str, Any]:
    experiments = payload.get("experiments", [])
    ranking_experiments = [
        exp for exp in experiments if isinstance(exp, Mapping) and str(exp.get("claim", {}).get("type")) == "ranking"
    ]
    cases: list[dict[str, Any]] = []
    for exp in ranking_experiments:
        for mutation_kind in mutation_kinds:
            cases.append(
                build_mutation_sanity_case(
                    experiment=exp,
                    rows=rows,
                    mutation_kind=mutation_kind,
                )
            )
    return {
        "schema_version": "mutation_sanity_v1",
        "ranking_experiments_evaluated": len(ranking_experiments),
        "mutation_kinds": list(mutation_kinds),
        "case_count": len(cases),
        "fragility_signal_detected": any(bool(case.get("fragility_signal_detected")) for case in cases),
        "cases": cases,
    }


def load_claim_payload(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload
