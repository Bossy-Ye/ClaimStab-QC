from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd


CONFIG_COLUMNS = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]

RUN_SPECS = {
    "E1": "E1_maxcut_main",
    "E2": "E2_ghz_structural",
    "E3": "E3_bv_decision",
    "E4": "E4_grover_distribution",
    "QEC": "QEC_portability",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _mkdirs(root: Path) -> dict[str, Path]:
    layout = {
        "rq1": root / "RQ1_necessity",
        "rq2": root / "RQ2_semantics",
        "rq3": root / "RQ3_diagnostics",
        "rq4": root / "RQ4_practicality",
    }
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    return layout


def _load_payloads(runs_root: Path) -> dict[str, dict[str, Any]]:
    payloads = {name: _read_json(runs_root / dirname / "claim_stability.json") for name, dirname in RUN_SPECS.items()}
    payloads["S2"] = _read_json(runs_root / "S2_boundary" / "run" / "claim_stability.json")
    payloads["S2_boundary_summary"] = _read_json(runs_root / "S2_boundary" / "boundary_summary.json")
    return payloads


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(payload.get("comparative", {}).get("space_claim_delta", []))


def _safe_rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _space_order(value: str) -> tuple[int, str]:
    order = {
        "compilation_only_exact": 0,
        "sampling_only_exact": 1,
        "combined_light_exact": 2,
    }
    return (order.get(value, 99), value)


def _delta_order(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return math.inf


def _claim_pair_from_exp(exp: dict[str, Any]) -> str:
    claim = exp.get("claim", {})
    if claim.get("type") == "ranking":
        return f"{claim.get('method_a')}>{claim.get('method_b')}"
    if claim.get("type") == "distribution":
        eps = claim.get("epsilon")
        return f"{claim.get('method')}:dist<={eps}"
    if claim.get("type") == "decision":
        return f"{claim.get('method')}@topk"
    return str(exp.get("experiment_id"))


def _exp_index(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for exp in payload.get("experiments", []):
        out[(exp.get("sampling", {}).get("space_preset"), _claim_pair_from_exp(exp))] = exp
    return out


def _driver_rank_from_diag(diag: dict[str, Any], delta_key: str) -> list[dict[str, Any]]:
    by_delta = diag.get("by_delta_dimension", {})
    raw = by_delta.get(delta_key, {})
    ranked: list[dict[str, Any]] = []
    for dimension, values in raw.items():
        if not isinstance(values, dict):
            continue
        rates = [float(v.get("flip_rate")) for v in values.values() if isinstance(v, dict) and v.get("flip_rate") is not None]
        if not rates:
            continue
        ranked.append(
            {
                "dimension": dimension,
                "score": max(rates) - min(rates),
                "min_flip_rate": min(rates),
                "max_flip_rate": max(rates),
                "n_values": len(rates),
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["dimension"]))
    return ranked


def _top2_set(diag: dict[str, Any], delta_key: str) -> set[str]:
    ranked = _driver_rank_from_diag(diag, delta_key)
    return {row["dimension"] for row in ranked[:2]}


def _varying_dimensions(scores: pd.DataFrame, space_preset: str) -> list[str]:
    subset = scores[scores["space_preset"] == space_preset]
    dims: list[str] = []
    for column in CONFIG_COLUMNS:
        if column in subset.columns and subset[column].nunique(dropna=False) > 1:
            dims.append(column)
    return dims


def _aggregate_rq1(payloads: dict[str, dict[str, Any]], layout: dict[str, Path]) -> dict[str, Any]:
    e1_payload = payloads["E1"]
    e1_rows = _rows(e1_payload)

    single_rows: list[dict[str, Any]] = []
    for row in e1_rows:
        naive = row.get("naive_baseline_realistic") or {}
        strict = row.get("naive_baseline") or {}
        single_rows.append(
            {
                "claim_pair": row.get("claim_pair"),
                "space_preset": row.get("space_preset"),
                "delta": row.get("delta"),
                "decision": row.get("decision"),
                "stability_hat": row.get("stability_hat"),
                "stability_ci_low": row.get("stability_ci_low"),
                "stability_ci_high": row.get("stability_ci_high"),
                "apparently_supported_realistic": bool(naive.get("naive_holds")),
                "baseline_config_realistic": json.dumps(naive.get("baseline_config", {}), sort_keys=True),
                "realistic_policy": naive.get("naive_policy"),
                "apparently_supported_strict": bool(strict.get("naive_holds")),
                "baseline_config_strict": json.dumps(strict.get("baseline_config", {}), sort_keys=True),
                "strict_policy": strict.get("naive_policy"),
            }
        )
    _write_csv(layout["rq1"] / "single_run_miss_rate_table.csv", single_rows)

    nonstable = [row for row in single_rows if row["decision"] in {"unstable", "inconclusive"}]
    realistic_miss = sum(1 for row in nonstable if row["apparently_supported_realistic"])
    strict_miss = sum(1 for row in nonstable if row["apparently_supported_strict"])
    single_summary = {
        "population": {
            "total_claim_space_delta_variants": len(single_rows),
            "nonstable_variants": len(nonstable),
        },
        "realistic_single_run_baseline": {
            "apparently_supported_among_nonstable": realistic_miss,
            "miss_rate_among_nonstable": _safe_rate(realistic_miss, len(nonstable)),
            "apparently_supported_among_all": sum(1 for row in single_rows if row["apparently_supported_realistic"]),
            "share_among_all": _safe_rate(sum(1 for row in single_rows if row["apparently_supported_realistic"]), len(single_rows)),
        },
        "strict_single_run_baseline": {
            "apparently_supported_among_nonstable": strict_miss,
            "miss_rate_among_nonstable": _safe_rate(strict_miss, len(nonstable)),
            "apparently_supported_among_all": sum(1 for row in single_rows if row["apparently_supported_strict"]),
            "share_among_all": _safe_rate(sum(1 for row in single_rows if row["apparently_supported_strict"]), len(single_rows)),
        },
        "note": "Single-run miss rate is computed from the existing single-configuration baseline fields already stored in the E1 artifact.",
    }
    _write_json(layout["rq1"] / "single_run_miss_rate_summary.json", single_summary)

    by_scope: list[dict[str, Any]] = []
    by_space: dict[str, dict[str, int]] = {}
    for row in e1_rows:
        space = str(row.get("space_preset"))
        decision = str(row.get("decision"))
        bucket = by_space.setdefault(space, {"stable": 0, "unstable": 0, "inconclusive": 0, "total": 0})
        bucket[decision] += 1
        bucket["total"] += 1
    for space, counts in sorted(by_space.items(), key=lambda item: _space_order(item[0])):
        by_scope.append({"space_preset": space, **counts})
    _write_csv(layout["rq1"] / "e1_verdicts_by_scope.csv", by_scope)
    _write_json(layout["rq1"] / "e1_verdicts_by_scope.json", {"rows": by_scope})

    by_delta_map: dict[str, dict[str, int]] = {}
    for row in e1_rows:
        delta = str(row.get("delta"))
        decision = str(row.get("decision"))
        bucket = by_delta_map.setdefault(delta, {"stable": 0, "unstable": 0, "inconclusive": 0, "total": 0})
        bucket[decision] += 1
        bucket["total"] += 1
    by_delta = [{"delta": delta, **counts} for delta, counts in sorted(by_delta_map.items(), key=lambda item: _delta_order(item[0]))]
    _write_csv(layout["rq1"] / "e1_verdicts_by_delta.csv", by_delta)
    _write_json(layout["rq1"] / "e1_verdicts_by_delta.json", {"rows": by_delta})

    scores = pd.read_csv(Path(e1_payload["meta"]["artifacts"]["trace_jsonl"]).parent / "scores.csv")
    score_configs: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    selected_config_map: dict[str, list[dict[str, Any]]] = {}
    claim_pairs = sorted({str(row.get("claim_pair")) for row in e1_rows})
    for space in sorted(scores["space_preset"].unique().tolist(), key=_space_order):
        cfg_df = scores[scores["space_preset"] == space][CONFIG_COLUMNS].drop_duplicates().sort_values(CONFIG_COLUMNS).head(5)
        selected = cfg_df.to_dict(orient="records")
        selected_config_map[space] = selected
        for rank, cfg in enumerate(selected, start=1):
            score_configs.append({"space_preset": space, "rank": rank, **cfg})
        subset = scores[scores["space_preset"] == space].copy()
        for column, value in cfg_df.iloc[0:0].to_dict().items():
            _ = column, value
        cfg_merge = pd.DataFrame(selected)
        chosen = subset.merge(cfg_merge, on=CONFIG_COLUMNS, how="inner")
        pivot = chosen.pivot_table(index=["instance_id", *CONFIG_COLUMNS], columns="method", values="score", aggfunc="first").reset_index()
        for claim_pair in claim_pairs:
            method_a, method_b = claim_pair.split(">")
            if method_a not in pivot.columns or method_b not in pivot.columns:
                continue
            diffs = pivot.copy()
            diffs["diff"] = diffs[method_a] - diffs[method_b]
            by_cfg = diffs.groupby(CONFIG_COLUMNS, dropna=False)["diff"].mean().reset_index()
            values = by_cfg["diff"].astype(float).tolist()
            n = len(values)
            mean_diff = float(pd.Series(values).mean()) if values else 0.0
            std_diff = float(pd.Series(values).std(ddof=1)) if len(values) > 1 else 0.0
            half_width = 1.96 * std_diff / math.sqrt(n) if n > 0 else math.nan
            ci_low = mean_diff - half_width if n > 0 else math.nan
            ci_high = mean_diff + half_width if n > 0 else math.nan
            consistent = bool(n > 0 and mean_diff > 0 and ci_low > 0)
            metric_rows.append(
                {
                    "space_preset": space,
                    "claim_pair": claim_pair,
                    "n_configs": n,
                    "mean_diff": mean_diff,
                    "std_diff": std_diff,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "consistent_advantage": consistent,
                }
            )
    _write_csv(layout["rq1"] / "metric_baseline_selected_configs.csv", score_configs)
    _write_csv(layout["rq1"] / "metric_baseline_by_claim_space.csv", metric_rows)

    metric_map = {(row["space_preset"], row["claim_pair"]): row for row in metric_rows}
    expanded_metric_rows: list[dict[str, Any]] = []
    for row in e1_rows:
        metric = metric_map.get((row.get("space_preset"), row.get("claim_pair")), {})
        expanded_metric_rows.append(
            {
                "claim_pair": row.get("claim_pair"),
                "space_preset": row.get("space_preset"),
                "delta": row.get("delta"),
                "decision": row.get("decision"),
                "stability_hat": row.get("stability_hat"),
                "stability_ci_low": row.get("stability_ci_low"),
                "stability_ci_high": row.get("stability_ci_high"),
                "metric_mean_diff": metric.get("mean_diff"),
                "metric_ci_low": metric.get("ci_low"),
                "metric_ci_high": metric.get("ci_high"),
                "metric_consistent_advantage": bool(metric.get("consistent_advantage")),
                "metric_false_reassurance": bool(metric.get("consistent_advantage") and row.get("decision") == "unstable"),
                "metric_nonstable_conflict": bool(metric.get("consistent_advantage") and row.get("decision") in {"unstable", "inconclusive"}),
            }
        )
    _write_csv(layout["rq1"] / "metric_false_reassurance_table.csv", expanded_metric_rows)
    consistent_variants = [row for row in expanded_metric_rows if row["metric_consistent_advantage"]]
    false_reassurance_variants = [row for row in consistent_variants if row["metric_false_reassurance"]]
    metric_summary = {
        "selection_rule": "Fixed lexicographic five-config slice per space, using the first five configurations under sorted exposed-factor values.",
        "criterion": "consistent advantage iff mean_diff > 0 and mean +/- 1.96 * std/sqrt(5) excludes zero on the positive side",
        "counts": {
            "variants_total": len(expanded_metric_rows),
            "variants_with_consistent_advantage": len(consistent_variants),
            "false_reassurance_variants": len(false_reassurance_variants),
            "false_reassurance_rate": _safe_rate(len(false_reassurance_variants), len(consistent_variants)),
        },
    }
    _write_json(layout["rq1"] / "metric_false_reassurance_summary.json", metric_summary)

    mismatch_candidates = sorted(
        [row for row in expanded_metric_rows if row["metric_nonstable_conflict"]],
        key=lambda row: (row["metric_ci_low"], row["metric_mean_diff"], -row["stability_hat"]),
        reverse=True,
    )
    selected_case = mismatch_candidates[0] if mismatch_candidates else max(
        expanded_metric_rows,
        key=lambda row: (row["metric_mean_diff"], row["metric_ci_low"]),
    )
    sibling_rows = [row for row in expanded_metric_rows if row["claim_pair"] == selected_case["claim_pair"] and row["space_preset"] == selected_case["space_preset"]]
    mismatch_case = {
        "selected_case": selected_case,
        "all_delta_variants_for_same_claim_space": sorted(sibling_rows, key=lambda row: _delta_order(row["delta"])),
        "selection_reason": (
            "Highest-confidence metric-based apparent advantage that still conflicts with the ClaimStab verdict."
            if mismatch_candidates
            else "No direct false-reassurance case was found under the current five-config metric baseline; selected the strongest positive-metric case instead."
        ),
    }
    _write_json(layout["rq1"] / "claim_metric_mismatch_case.json", mismatch_case)

    return {
        "single_run": single_summary,
        "metric_baseline": metric_summary,
        "mismatch_case": mismatch_case,
    }


def _aggregate_rq2(payloads: dict[str, dict[str, Any]], layout: dict[str, Path]) -> dict[str, Any]:
    family_rows: list[dict[str, Any]] = []
    counts_by_family: dict[str, dict[str, int]] = {}
    for run_id in ["E1", "E2", "E3", "E4", "S2", "QEC"]:
        for row in _rows(payloads[run_id]):
            family = str(row.get("claim_type"))
            decision = str(row.get("decision"))
            bucket = counts_by_family.setdefault(family, {"stable": 0, "unstable": 0, "inconclusive": 0, "total": 0})
            bucket[decision] += 1
            bucket["total"] += 1
    for family, counts in sorted(counts_by_family.items()):
        family_rows.append({"claim_family": family, **counts})
    _write_csv(layout["rq2"] / "verdicts_by_claim_family.csv", family_rows)
    _write_json(layout["rq2"] / "verdicts_by_claim_family.json", {"rows": family_rows})

    e2_rows = sorted(
        [
            {
                "claim_pair": row.get("claim_pair"),
                "metric_name": row.get("metric_name"),
                "space_preset": row.get("space_preset"),
                "delta": row.get("delta"),
                "decision": row.get("decision"),
                "stability_hat": row.get("stability_hat"),
                "stability_ci_low": row.get("stability_ci_low"),
                "stability_ci_high": row.get("stability_ci_high"),
                "inconclusive_reason": row.get("inconclusive_reason"),
            }
            for row in _rows(payloads["E2"])
        ],
        key=lambda row: (row["metric_name"], _space_order(row["space_preset"]), _delta_order(row["delta"])),
    )
    _write_csv(layout["rq2"] / "e2_breakdown.csv", e2_rows)
    _write_json(layout["rq2"] / "e2_breakdown.json", {"rows": e2_rows})

    s2_rows = sorted(
        [
            {
                "claim_pair": row.get("claim_pair"),
                "space_preset": row.get("space_preset"),
                "delta": row.get("delta"),
                "decision": row.get("decision"),
                "stability_hat": row.get("stability_hat"),
                "stability_ci_low": row.get("stability_ci_low"),
                "stability_ci_high": row.get("stability_ci_high"),
            }
            for row in _rows(payloads["S2"])
        ],
        key=lambda row: (row["claim_pair"], _space_order(row["space_preset"]), _delta_order(row["delta"])),
    )
    _write_csv(layout["rq2"] / "s2_breakdown.csv", s2_rows)
    _write_json(layout["rq2"] / "s2_breakdown.json", {"rows": s2_rows})

    return {
        "family_distribution": family_rows,
        "e2_breakdown_rows": len(e2_rows),
        "s2_breakdown_rows": len(s2_rows),
    }


def _summarize_lockdown_proxy(run_id: str, payload: dict[str, Any], scores: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    available = False
    for exp in payload.get("experiments", []):
        space = str(exp.get("sampling", {}).get("space_preset"))
        full_dims = _varying_dimensions(scores, space)
        full_dim_count = len(full_dims)
        claim_pair = _claim_pair_from_exp(exp)
        for graph_id, graph in exp.get("per_graph", {}).items():
            for delta_key, rec in graph.get("lockdown_recommendation", {}).items():
                tops = rec.get("top_recommendations", []) if isinstance(rec, dict) else []
                if not tops:
                    continue
                top = tops[0]
                constraint_count = len(top.get("constraints", {}))
                available = True
                rows.append(
                    {
                        "run_id": run_id,
                        "claim_pair": claim_pair,
                        "space_preset": space,
                        "graph_id": graph_id,
                        "delta": delta_key,
                        "constraint_count_proxy": constraint_count,
                        "exposed_factor_count": full_dim_count,
                        "reduction_ratio_proxy": (constraint_count / full_dim_count) if full_dim_count else None,
                        "top_dimension": top.get("dimension"),
                        "top_value": top.get("value"),
                        "flip_rate_improvement": top.get("flip_rate_improvement"),
                        "subset_size": top.get("subset_size"),
                    }
                )
    summary = {
        "run_id": run_id,
        "exact_mos_available": False,
        "proxy_name": "lockdown_recommendation_top_constraint_count",
        "proxy_available": available,
        "median_constraint_count_proxy": median([row["constraint_count_proxy"] for row in rows]) if rows else None,
        "median_reduction_ratio_proxy": median([row["reduction_ratio_proxy"] for row in rows if row["reduction_ratio_proxy"] is not None]) if rows else None,
        "rows": len(rows),
    }
    return rows, summary


def _aggregate_rq3(payloads: dict[str, dict[str, Any]], layout: dict[str, Path]) -> dict[str, Any]:
    e1_payload = payloads["E1"]
    s2_payload = payloads["S2"]
    e4_payload = payloads["E4"]

    e1_scores = pd.read_csv(Path(e1_payload["meta"]["artifacts"]["trace_jsonl"]).parent / "scores.csv")
    s2_scores = pd.read_csv(Path(s2_payload["meta"]["artifacts"]["trace_jsonl"]).parent / "scores.csv")
    e4_scores = pd.read_csv(Path(e4_payload["meta"]["artifacts"]["trace_jsonl"]).parent / "scores.csv")

    proxy_rows: list[dict[str, Any]] = []
    proxy_summaries: list[dict[str, Any]] = []
    for run_id, payload, scores in [("E1", e1_payload, e1_scores), ("S2", s2_payload, s2_scores), ("E4", e4_payload, e4_scores)]:
        rows, summary = _summarize_lockdown_proxy(run_id, payload, scores)
        proxy_rows.extend(rows)
        proxy_summaries.append(summary)
    _write_csv(layout["rq3"] / "mos_proxy_table.csv", proxy_rows)
    _write_json(layout["rq3"] / "mos_summary.json", {"runs": proxy_summaries})

    driver_rows: list[dict[str, Any]] = []
    interaction_rows: list[dict[str, Any]] = []
    for run_id in ["E1", "S2"]:
        rq = payloads[run_id].get("rq_summary", {})
        drivers = rq.get("rq2_drivers", {})
        for space, entries in (drivers.get("top_dimensions_by_space") or {}).items():
            for rank, entry in enumerate(entries, start=1):
                driver_rows.append(
                    {
                        "run_id": run_id,
                        "space_preset": space,
                        "rank": rank,
                        "dimension": entry.get("dimension"),
                        "driver_score": entry.get("driver_score"),
                        "avg_contrast": entry.get("avg_contrast"),
                        "avg_improvement_from_best_value": entry.get("avg_improvement_from_best_value"),
                        "flip_rate": entry.get("flip_rate"),
                    }
                )
        interactions = rq.get("rq7_effect_diagnostics", {})
        for space, entries in (interactions.get("top_interactions_by_space") or {}).items():
            for rank, entry in enumerate(entries, start=1):
                interaction_rows.append(
                    {
                        "run_id": run_id,
                        "space_preset": space,
                        "rank": rank,
                        "dimensions": "+".join(entry.get("dimensions", [])),
                        "interaction_score": entry.get("interaction_score"),
                        "joint_spread": entry.get("joint_spread"),
                        "reference_main_effect": entry.get("reference_main_effect"),
                        "n_cells": entry.get("n_cells"),
                    }
                )
    if not any(row["run_id"] == "E4" for row in driver_rows):
        driver_rows.append(
            {
                "run_id": "E4",
                "space_preset": "all",
                "rank": None,
                "dimension": None,
                "driver_score": None,
                "avg_contrast": None,
                "avg_improvement_from_best_value": None,
                "flip_rate": None,
                "status": "driver_diagnostics_not_materialized_in_current_E4_run",
            }
        )
    if not any(row.get("run_id") == "E4" for row in interaction_rows):
        interaction_rows.append(
            {
                "run_id": "E4",
                "space_preset": "all",
                "rank": None,
                "dimensions": None,
                "interaction_score": None,
                "joint_spread": None,
                "reference_main_effect": None,
                "n_cells": None,
                "status": "interaction_diagnostics_not_materialized_in_current_E4_run",
            }
        )
    _write_csv(layout["rq3"] / "top_drivers.csv", driver_rows)
    _write_csv(layout["rq3"] / "top_interactions.csv", interaction_rows)

    consistency_rows: list[dict[str, Any]] = []
    consistency_summary: list[dict[str, Any]] = []
    for run_id in ["E1", "S2"]:
        payload = payloads[run_id]
        exp_map = []
        for exp in payload.get("experiments", []):
            diag = exp.get("overall", {}).get("diagnostics", {})
            claim_pair = _claim_pair_from_exp(exp)
            space = exp.get("sampling", {}).get("space_preset")
            for delta_row in exp.get("overall", {}).get("delta_sweep", []):
                if delta_row.get("decision") != "unstable":
                    continue
                delta_key = str(delta_row.get("delta"))
                exp_map.append(
                    {
                        "claim_pair": claim_pair,
                        "space_preset": space,
                        "delta": float(delta_row.get("delta")),
                        "top2": _top2_set(diag, delta_key),
                    }
                )
        overlaps: list[float] = []
        for claim_pair in sorted({row["claim_pair"] for row in exp_map}):
            subset = sorted([row for row in exp_map if row["claim_pair"] == claim_pair], key=lambda row: (_space_order(str(row["space_preset"])), row["delta"]))
            for a, b in zip(subset, subset[1:]):
                if a["space_preset"] != b["space_preset"]:
                    continue
                union = a["top2"] | b["top2"]
                overlap = len(a["top2"] & b["top2"]) / len(union) if union else None
                overlaps.append(overlap if overlap is not None else 0.0)
                consistency_rows.append(
                    {
                        "run_id": run_id,
                        "claim_pair": claim_pair,
                        "space_preset": a["space_preset"],
                        "delta_a": a["delta"],
                        "delta_b": b["delta"],
                        "top2_a": ",".join(sorted(a["top2"])),
                        "top2_b": ",".join(sorted(b["top2"])),
                        "jaccard_overlap": overlap,
                    }
                )
        consistency_summary.append(
            {
                "run_id": run_id,
                "neighbor_pairs": len(overlaps),
                "mean_top2_jaccard_overlap": sum(overlaps) / len(overlaps) if overlaps else None,
            }
        )
    _write_csv(layout["rq3"] / "top_driver_consistency.csv", consistency_rows)
    _write_json(layout["rq3"] / "top_driver_consistency.json", {"runs": consistency_summary, "pairs": consistency_rows})

    e1_exp_index = _exp_index(e1_payload)
    e1_metric_table = pd.read_csv(layout["rq1"] / "metric_false_reassurance_table.csv")
    mismatch_rows = e1_metric_table[e1_metric_table["metric_nonstable_conflict"] == True]
    if mismatch_rows.empty:
        e1_case_row = e1_metric_table.sort_values(["metric_mean_diff", "metric_ci_low"], ascending=False).iloc[0].to_dict()
    else:
        e1_case_row = mismatch_rows.sort_values(["metric_ci_low", "metric_mean_diff", "stability_hat"], ascending=[False, False, True]).iloc[0].to_dict()
    e1_exp = e1_exp_index[(e1_case_row["space_preset"], e1_case_row["claim_pair"])]
    e1_delta_key = str(e1_case_row["delta"])
    e1_ranked = _driver_rank_from_diag(e1_exp.get("overall", {}).get("diagnostics", {}), e1_delta_key)[:3]
    e1_violation = (e1_exp.get("overall", {}).get("diagnostics", {}).get("top_unstable_configs_by_delta", {}) or {}).get(e1_delta_key, [None])[0]
    e1_lockdown = None
    if e1_violation and e1_violation.get("graph_id") in e1_exp.get("per_graph", {}):
        graph = e1_exp["per_graph"][e1_violation["graph_id"]]
        e1_lockdown = ((graph.get("lockdown_recommendation", {}) or {}).get(e1_delta_key, {}) or {}).get("top_recommendations", [None])[0]
    e1_case = {
        "case_id": "E1_ranking_fragility",
        "claim_pair": e1_case_row["claim_pair"],
        "space_preset": e1_case_row["space_preset"],
        "delta": e1_case_row["delta"],
        "decision": e1_case_row["decision"],
        "stability_hat": e1_case_row["stability_hat"],
        "stability_ci_low": e1_case_row["stability_ci_low"],
        "stability_ci_high": e1_case_row["stability_ci_high"],
        "metric_mean_diff": e1_case_row["metric_mean_diff"],
        "metric_ci_low": e1_case_row["metric_ci_low"],
        "metric_ci_high": e1_case_row["metric_ci_high"],
        "top_factors": e1_ranked,
        "representative_unstable_config": e1_violation,
        "lockdown_proxy": {
            "available": e1_lockdown is not None,
            "constraint_count_proxy": len((e1_lockdown or {}).get("constraints", {})) if e1_lockdown else None,
            "top_recommendation": e1_lockdown,
        },
        "explanation": "Fragility is most associated with the leading perturbation dimensions in the ranking diagnostic, while the representative violation shows the claim flipping sign under an admissible configuration.",
    }

    e4_exp = next(iter(e4_payload.get("experiments", [])), {})
    e4_delta_row = next(iter(e4_exp.get("overall", {}).get("delta_sweep", [])), {})
    e4_graph_id, e4_graph = next(iter(e4_exp.get("per_graph", {}).items()))
    dist_driver_rows: list[dict[str, Any]] = []
    for dimension in ("shots", "seed_simulator", "layout_method", "optimization_level"):
        vals: dict[Any, list[float]] = {}
        for obs in e4_graph.get("distance_observations", []):
            vals.setdefault(obs.get(dimension), []).append(float(obs.get("primary_value", 0.0)))
        vals = {k: v for k, v in vals.items() if k is not None and len(v) > 0}
        if len(vals) <= 1:
            continue
        means = {k: sum(v) / len(v) for k, v in vals.items()}
        dist_driver_rows.append(
            {
                "dimension": dimension,
                "score": max(means.values()) - min(means.values()),
                "mean_primary_distance_by_value": means,
            }
        )
    dist_driver_rows.sort(key=lambda row: (-row["score"], row["dimension"]))
    e4_case = {
        "case_id": "E4_distribution_fragility",
        "claim_pair": _claim_pair_from_exp(e4_exp),
        "space_preset": e4_exp.get("sampling", {}).get("space_preset"),
        "delta": None,
        "decision": e4_delta_row.get("decision"),
        "stability_hat": e4_delta_row.get("stability_hat"),
        "stability_ci_low": e4_delta_row.get("stability_ci_low"),
        "stability_ci_high": e4_delta_row.get("stability_ci_high"),
        "top_factors_proxy_from_distance_observations": dist_driver_rows[:3],
        "representative_violation": (e4_graph.get("top_violations") or [None])[0],
        "graph_id": e4_graph_id,
        "explanation": "The distribution claim fails because low-shot observations produce large JS/TVD distances that exceed the declared tolerance, indicating sampling-sensitive distribution fragility.",
    }

    case_studies = {"cases": [e1_case, e4_case]}
    _write_json(layout["rq3"] / "case_studies.json", case_studies)

    runtime_rows: list[dict[str, Any]] = []
    for run_id in ["E1", "E2", "E3", "E4", "S2", "QEC"]:
        payload = payloads[run_id]
        practicality = payload.get("meta", {}).get("practicality", {})
        runtime_rows.append(
            {
                "run_id": run_id,
                "rows_processed": practicality.get("rows_processed"),
                "total_wall_time_sec": practicality.get("total_wall_time"),
                "throughput_runs_per_sec": practicality.get("throughput_runs_per_sec"),
                "runner_wall_time_ms_mean": (practicality.get("runner_timing") or {}).get("wall_time_ms_mean"),
            }
        )
    _write_csv(layout["rq3"] / "runtime_summary_available_runs.csv", runtime_rows)

    return {
        "mos": proxy_summaries,
        "drivers_rows": len(driver_rows),
        "interaction_rows": len(interaction_rows),
        "consistency": consistency_summary,
    }


def _aggregate_rq4(payloads: dict[str, dict[str, Any]], layout: dict[str, Path], root: Path) -> dict[str, Any]:
    status = _read_json(root / "manifests" / "evaluation_status.json")
    pending = status.get("pending", [])
    available_outputs: dict[str, Any] = {}

    e5_summary_path = root / "runs" / "E5_policy_comparison" / "rq4_policy_summary.json"
    if e5_summary_path.exists():
        e5_summary = _read_json(e5_summary_path)
        strategy_rows: list[dict[str, Any]] = []
        band_rows: list[dict[str, Any]] = []
        for strategy in e5_summary.get("strategies", []):
            if not isinstance(strategy, dict):
                continue
            agreement = strategy.get("agreement_with_factorial") or {}
            adaptive = strategy.get("adaptive_stopping") or {}
            strategy_rows.append(
                {
                    "strategy": strategy.get("strategy"),
                    "strategy_group": strategy.get("strategy_group"),
                    "sampling_mode": strategy.get("sampling_mode"),
                    "k_used": strategy.get("k_used"),
                    "k_budget": strategy.get("k_budget"),
                    "perturbation_space_size": strategy.get("perturbation_space_size"),
                    "agreement_rate": agreement.get("rate"),
                    "adaptive_enabled": adaptive.get("enabled"),
                    "adaptive_target_ci_width": adaptive.get("target_ci_width"),
                    "adaptive_stop_reason": adaptive.get("stop_reason"),
                }
            )
            by_band = strategy.get("agreement_by_source_band") or {}
            for band, rec in by_band.items():
                if not isinstance(rec, dict):
                    continue
                band_rows.append(
                    {
                        "strategy": strategy.get("strategy"),
                        "source_band": band,
                        "n": rec.get("n"),
                        "agreement_rate": rec.get("rate"),
                    }
                )
        _write_csv(layout["rq4"] / "e5_policy_summary.csv", strategy_rows)
        _write_csv(layout["rq4"] / "e5_policy_agreement_by_source_band.csv", band_rows)
        _write_json(
            layout["rq4"] / "e5_policy_summary.json",
            {
                "summary_path": str(e5_summary_path.resolve()),
                "figures": e5_summary.get("figures", {}),
                "strategies": strategy_rows,
                "agreement_by_source_band": band_rows,
            },
        )
        available_outputs["E5"] = {
            "available": True,
            "summary_path": str(e5_summary_path.resolve()),
            "n_strategies": len(strategy_rows),
        }

    s1_summary_path = root / "runs" / "S1_multidevice_portability" / "combined_summary.json"
    if s1_summary_path.exists():
        s1_summary = _read_json(s1_summary_path)
        device_rows = [row for row in s1_summary.get("device_summary", []) if isinstance(row, dict)]
        by_device_metric: dict[tuple[str, str], dict[str, Any]] = {}
        for row in device_rows:
            key = (str(row.get("device_name")), str(row.get("metric_name")))
            bucket = by_device_metric.setdefault(
                key,
                {
                    "device_name": key[0],
                    "metric_name": key[1],
                    "rows": 0,
                    "stable": 0,
                    "unstable": 0,
                    "inconclusive": 0,
                    "mean_stability_hat": [],
                },
            )
            bucket["rows"] += 1
            decision = str(row.get("decision"))
            if decision in {"stable", "unstable", "inconclusive"}:
                bucket[decision] += 1
            if row.get("stability_hat") is not None:
                bucket["mean_stability_hat"].append(float(row["stability_hat"]))
        device_metric_rows: list[dict[str, Any]] = []
        for (_, _), bucket in sorted(by_device_metric.items()):
            hats = bucket.pop("mean_stability_hat")
            bucket["mean_stability_hat"] = (sum(hats) / len(hats)) if hats else None
            device_metric_rows.append(bucket)
        _write_csv(layout["rq4"] / "s1_backend_portability_by_device_metric.csv", device_metric_rows)
        _write_json(
            layout["rq4"] / "s1_backend_portability_summary.json",
            {
                "summary_path": str(s1_summary_path.resolve()),
                "meta": s1_summary.get("meta", {}),
                "overall_counts": {
                    "rows": len(device_rows),
                    "stable": sum(1 for row in device_rows if row.get("decision") == "stable"),
                    "unstable": sum(1 for row in device_rows if row.get("decision") == "unstable"),
                    "inconclusive": sum(1 for row in device_rows if row.get("decision") == "inconclusive"),
                },
                "by_device_metric": device_metric_rows,
                "note": (
                    "Current S1 output is a backend-conditioned transpile-only structural portability study "
                    "over circuit_depth and two_qubit_count, not a full claim-centric noisy-device rerun."
                ),
            },
        )
        available_outputs["S1"] = {
            "available": True,
            "summary_path": str(s1_summary_path.resolve()),
            "rows": len(device_rows),
        }

    replay_status = {
        "available": False,
        "reason": "Replay consistency requires repeated executions; the current evaluation_v2 directory contains single completed runs only.",
    }
    _write_json(
        layout["rq4"] / "pending_status.json",
        {
            "pending": pending,
            "available_outputs": available_outputs,
            "replay_consistency": replay_status,
        },
    )
    return {
        "pending_items": pending,
        "available_outputs": available_outputs,
        "replay_consistency": replay_status,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Derive paper-facing evaluation summaries from evaluation_v2 runs.")
    ap.add_argument("--root", default="output/paper/evaluation_v2")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    derived_root = root / "derived_paper_evaluation"
    layout = _mkdirs(derived_root)
    payloads = _load_payloads(root / "runs")

    manifest = {
        "root": str(root.resolve()),
        "derived_root": str(derived_root.resolve()),
        "rq1": _aggregate_rq1(payloads, layout),
        "rq2": _aggregate_rq2(payloads, layout),
        "rq3": _aggregate_rq3(payloads, layout),
        "rq4": _aggregate_rq4(payloads, layout, root),
    }
    _write_json(derived_root / "manifest.json", manifest)
    print(f"Wrote derived paper evaluation outputs to: {derived_root}")


if __name__ == "__main__":
    main()
