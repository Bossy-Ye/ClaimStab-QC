from __future__ import annotations

import math
from typing import Any, Callable

from qiskit.transpiler import CouplingMap

from claimstab.claims.ranking import RankingClaim
from claimstab.claims.stability import ci_width, estimate_binomial_rate
from claimstab.methods.spec import MethodSpec
from claimstab.pipelines.common import config_key
from claimstab.perturbations.sampling import adaptive_sample_configs
from claimstab.perturbations.space import PerturbationConfig
from claimstab.tasks.base import BuiltWorkflow


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


def filter_rows_by_keys(
    rows,
    allowed_keys: set[tuple[int, int, str | None, int, int | None]],
):
    from claimstab.claims.evaluation import perturbation_key

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


def select_adaptive_keys_with_width_evaluator(
    *,
    sampled_configs: list[PerturbationConfig],
    baseline_key: tuple[int, int, str | None, int, int | None],
    evaluate_ci_width_for_keys: Callable[[set[tuple[int, int, str | None, int, int | None]]], float],
    target_ci_width: float,
    min_sample_size: int,
    step_size: int,
) -> tuple[set[tuple[int, int, str | None, int, int | None]], dict[str, object]]:
    """Select adaptive perturbation keys for any claim type via CI-width callback."""

    ordered_non_baseline = [pc for pc in sampled_configs if config_key(pc) != baseline_key]
    if not ordered_non_baseline:
        return {baseline_key}, {
            "enabled": True,
            "target_ci_width": target_ci_width,
            "achieved_ci_width": None,
            "stop_reason": "no_candidate_configs",
            "selected_configurations_without_baseline": 0,
            "selected_configurations_with_baseline": 1,
            "evaluated_configurations_without_baseline": 0,
            "min_sample_size": min_sample_size,
            "step_size": step_size,
        }

    def eval_prefix(prefix_cfgs: list[PerturbationConfig]) -> tuple[float, float]:
        prefix_keys = {config_key(pc) for pc in prefix_cfgs}
        width = float(evaluate_ci_width_for_keys(prefix_keys))
        if not math.isfinite(width) or width < 0.0:
            width = 1.0
        return 0.0, width

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
