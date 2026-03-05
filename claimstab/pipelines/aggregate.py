from __future__ import annotations

from collections import defaultdict
from typing import Any

from claimstab.claims.diagnostics import aggregate_lockdown_recommendations
from claimstab.claims.evaluation import perturbation_key
from claimstab.runners.matrix_runner import ScoreRow


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
