from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any

import pandas as pd


CONFIG_COLUMNS = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]

CLAIM_PAIRS = [
    ("QAOA_p2", "QAOA_p1"),
    ("QAOA_p2", "RandomBaseline"),
    ("QAOA_p1", "RandomBaseline"),
]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping/object JSON at {path}")
    return payload


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


def _safe_rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _metric_ci(values: list[float]) -> tuple[float, float, float]:
    if not values:
        return (0.0, math.nan, math.nan)
    mean = float(sum(values) / len(values))
    if len(values) == 1:
        return (mean, mean, mean)
    std = float(statistics.stdev(values))
    half_width = 1.96 * std / math.sqrt(len(values))
    return (mean, mean - half_width, mean + half_width)


def _prepare_pivot(scores_csv: Path) -> pd.DataFrame:
    scores = pd.read_csv(scores_csv)
    pivot = (
        scores.pivot_table(
            index=["instance_id", *CONFIG_COLUMNS],
            columns="method",
            values="score",
            aggfunc="first",
        )
        .reset_index()
        .copy()
    )
    return pivot


def _metric_rows_for_space(
    pivot: pd.DataFrame,
    claim_rows: list[dict[str, Any]],
    *,
    key_cols: list[str],
    scope_name: str,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    metric_map: dict[tuple[str, str], dict[str, Any]] = {}
    for method_a, method_b in CLAIM_PAIRS:
        claim_pair = f"{method_a}>{method_b}"
        diffs = pivot.copy()
        diffs["diff"] = diffs[method_a] - diffs[method_b]
        grouped = diffs.groupby(key_cols, dropna=False)["diff"].mean().reset_index()
        values = grouped["diff"].astype(float).tolist()
        mean_diff, ci_low, ci_high = _metric_ci(values)
        record = {
            "space_preset": scope_name,
            "claim_pair": claim_pair,
            "n_configurations": len(values),
            "metric_mean_diff": mean_diff,
            "metric_ci_low": ci_low,
            "metric_ci_high": ci_high,
            "metric_verdict": "consistent_advantage" if (mean_diff > 0 and ci_low > 0) else "no_consistent_advantage",
            "metric_consistent_advantage": bool(mean_diff > 0 and ci_low > 0),
        }
        rows.append(record)
        metric_map[(scope_name, claim_pair)] = record
    expanded: list[dict[str, Any]] = []
    for row in claim_rows:
        metric = metric_map[(scope_name, str(row["claim_pair"]))]
        expanded.append(
            {
                "claim_pair": row["claim_pair"],
                "space_preset": scope_name,
                "delta": row["delta"],
                "metric_mean_diff": metric["metric_mean_diff"],
                "metric_ci_low": metric["metric_ci_low"],
                "metric_ci_high": metric["metric_ci_high"],
                "metric_verdict": metric["metric_verdict"],
                "metric_consistent_advantage": metric["metric_consistent_advantage"],
                "stability_hat": row["stability_hat"],
                "stability_ci_low": row["stability_ci_low"],
                "stability_ci_high": row["stability_ci_high"],
                "claimstab_decision": row["decision"],
                "metric_false_reassurance": bool(metric["metric_consistent_advantage"] and row["decision"] == "unstable"),
            }
        )
    return rows, {(r["space_preset"], r["claim_pair"], str(r["delta"])): r for r in expanded}


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _aggregate_e1_matched_scope(e1_root: Path, out_dir: Path) -> dict[str, Any]:
    claim_json = e1_root / "claim_stability.json"
    scores_csv = e1_root / "scores.csv"
    payload = _read_json(claim_json)
    rows = _extract_rows(payload)
    pivot = _prepare_pivot(scores_csv)

    metric_summary_rows: list[dict[str, Any]] = []
    expanded_rows: list[dict[str, Any]] = []
    by_space = sorted({str(row["space_preset"]) for row in rows})
    for space in by_space:
        space_claim_rows = [row for row in rows if str(row["space_preset"]) == space]
        space_pivot = pivot.merge(
            pd.DataFrame(space_claim_rows[:1])[[]],
            how="left",
            left_index=True,
            right_index=True,
        )
        scoped_scores = pd.read_csv(scores_csv)
        scoped_pivot = _prepare_pivot(scores_csv)
        scoped_pivot = scoped_pivot.merge(
            scoped_scores[scoped_scores["space_preset"] == space][["instance_id", *CONFIG_COLUMNS]].drop_duplicates(),
            on=["instance_id", *CONFIG_COLUMNS],
            how="inner",
        )
        summary_rows, expanded_map = _metric_rows_for_space(
            scoped_pivot,
            space_claim_rows,
            key_cols=CONFIG_COLUMNS,
            scope_name=space,
        )
        metric_summary_rows.extend(summary_rows)
        expanded_rows.extend(expanded_map.values())

    expanded_rows.sort(key=lambda row: (row["space_preset"], row["claim_pair"], float(row["delta"])))
    _write_csv(out_dir / "e1_metric_matched_scope_summary.csv", metric_summary_rows)
    _write_csv(out_dir / "e1_metric_matched_scope_table.csv", expanded_rows)

    supportive = [row for row in expanded_rows if row["metric_consistent_advantage"]]
    false_reassurance = [row for row in supportive if row["metric_false_reassurance"]]
    summary = {
        "source": str(claim_json.resolve()),
        "scores_csv": str(scores_csv.resolve()),
        "total_variants": len(expanded_rows),
        "metric_supportive_variants": len(supportive),
        "metric_false_reassurance_variants": len(false_reassurance),
        "metric_false_reassurance_rate_conditional": _safe_rate(len(false_reassurance), len(supportive)),
        "metric_false_reassurance_share_all": _safe_rate(len(false_reassurance), len(expanded_rows)),
        "note": "Matched-scope baseline uses all configurations in each declared E1 perturbation space.",
    }
    _write_json(out_dir / "e1_metric_matched_scope_summary.json", summary)
    return summary


def _aggregate_e5_full_grid(e5_root: Path, out_dir: Path) -> dict[str, Any]:
    claim_json = e5_root / "claim_stability.json"
    scores_csv = e5_root / "scores.csv"
    payload = _read_json(claim_json)
    rows = _extract_rows(payload)
    pivot = _prepare_pivot(scores_csv)

    metric_summary_rows, expanded_map = _metric_rows_for_space(
        pivot,
        rows,
        key_cols=CONFIG_COLUMNS,
        scope_name="sampling_policy_eval",
    )
    expanded_rows = list(expanded_map.values())
    expanded_rows.sort(key=lambda row: (row["claim_pair"], float(row["delta"])))

    _write_csv(out_dir / "e5_metric_fullgrid_summary.csv", metric_summary_rows)
    _write_csv(out_dir / "e5_metric_fullgrid_table.csv", expanded_rows)

    supportive = [row for row in expanded_rows if row["metric_consistent_advantage"]]
    false_reassurance = [row for row in supportive if row["metric_false_reassurance"]]
    summary = {
        "source": str(claim_json.resolve()),
        "scores_csv": str(scores_csv.resolve()),
        "total_variants": len(expanded_rows),
        "metric_supportive_variants": len(supportive),
        "metric_false_reassurance_variants": len(false_reassurance),
        "metric_false_reassurance_rate_conditional": _safe_rate(len(false_reassurance), len(supportive)),
        "metric_false_reassurance_share_all": _safe_rate(len(false_reassurance), len(expanded_rows)),
        "note": "Full-information metric baseline on the 495-configuration expanded sampling grid used by E5.",
    }
    _write_json(out_dir / "e5_metric_fullgrid_summary.json", summary)
    return summary


def _aggregate_sensitivity(e5_root: Path, out_dir: Path, *, repeats: int, seed: int) -> dict[str, Any]:
    claim_json = e5_root / "claim_stability.json"
    scores_csv = e5_root / "scores.csv"
    payload = _read_json(claim_json)
    rows = _extract_rows(payload)
    claim_decisions = {(str(row["claim_pair"]), float(row["delta"])): str(row["decision"]) for row in rows}
    pivot = _prepare_pivot(scores_csv)

    unique_configs = (
        pivot[CONFIG_COLUMNS]
        .drop_duplicates()
        .sort_values(CONFIG_COLUMNS)
        .reset_index(drop=True)
    )
    config_records = unique_configs.to_dict(orient="records")
    sample_sizes = [5, 10, 20, 50, 100, len(config_records)]
    rng = random.Random(seed)

    per_repeat_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []

    for sample_size in sample_sizes:
        n_repeats = repeats if sample_size < len(config_records) else 1
        cond_rates: list[float] = []
        share_all_rates: list[float] = []
        support_counts: list[int] = []
        for rep in range(n_repeats):
            chosen = config_records if sample_size == len(config_records) else rng.sample(config_records, sample_size)
            chosen_df = pd.DataFrame(chosen)
            sampled = pivot.merge(chosen_df, on=CONFIG_COLUMNS, how="inner")

            false_count = 0
            supportive_count = 0
            for method_a, method_b in CLAIM_PAIRS:
                claim_pair = f"{method_a}>{method_b}"
                diffs = sampled.copy()
                diffs["diff"] = diffs[method_a] - diffs[method_b]
                grouped = diffs.groupby(CONFIG_COLUMNS, dropna=False)["diff"].mean().reset_index()
                values = grouped["diff"].astype(float).tolist()
                mean_diff, ci_low, ci_high = _metric_ci(values)
                consistent = bool(mean_diff > 0 and ci_low > 0)
                for delta in [0.0, 0.01, 0.05]:
                    decision = claim_decisions[(claim_pair, delta)]
                    if consistent:
                        supportive_count += 1
                        if decision == "unstable":
                            false_count += 1
                    per_repeat_rows.append(
                        {
                            "sample_size": sample_size,
                            "repeat": rep,
                            "claim_pair": claim_pair,
                            "delta": delta,
                            "metric_mean_diff": mean_diff,
                            "metric_ci_low": ci_low,
                            "metric_ci_high": ci_high,
                            "metric_consistent_advantage": consistent,
                            "claimstab_decision": decision,
                            "metric_false_reassurance": bool(consistent and decision == "unstable"),
                        }
                    )

            cond_rate = false_count / supportive_count if supportive_count else 0.0
            cond_rates.append(cond_rate)
            share_all_rates.append(false_count / len(rows))
            support_counts.append(supportive_count)

        aggregate_rows.append(
            {
                "sample_size": sample_size,
                "repeats": n_repeats,
                "conditional_false_reassurance_rate_mean": statistics.mean(cond_rates),
                "conditional_false_reassurance_rate_min": min(cond_rates),
                "conditional_false_reassurance_rate_max": max(cond_rates),
                "share_of_all_variants_falsely_reassured_mean": statistics.mean(share_all_rates),
                "metric_supportive_variants_mean": statistics.mean(support_counts),
            }
        )

    _write_csv(out_dir / "metric_baseline_sensitivity_per_repeat.csv", per_repeat_rows)
    _write_csv(out_dir / "metric_baseline_sensitivity_summary.csv", aggregate_rows)
    summary = {
        "source": str(claim_json.resolve()),
        "scores_csv": str(scores_csv.resolve()),
        "sample_sizes": sample_sizes,
        "repeats": repeats,
        "seed": seed,
        "note": "Sensitivity analysis resamples the E5 495-configuration grid without replacement for each sample size.",
    }
    _write_json(out_dir / "metric_baseline_sensitivity_summary.json", {"meta": summary, "rows": aggregate_rows})
    return {"meta": summary, "rows": aggregate_rows}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Derive W3 metric-centric baselines for evaluation_v3.")
    ap.add_argument("--source-root", default="output/paper/evaluation_v2")
    ap.add_argument("--out-root", default="output/paper/evaluation_v3")
    ap.add_argument("--repeats", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20260321)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    source_root = Path(args.source_root)
    out_root = Path(args.out_root)
    out_dir = out_root / "derived_paper_evaluation" / "RQ1_necessity"
    out_dir.mkdir(parents=True, exist_ok=True)

    e1_summary = _aggregate_e1_matched_scope(source_root / "runs" / "E1_maxcut_main", out_dir)
    e5_summary = _aggregate_e5_full_grid(
        source_root / "runs" / "E5_policy_comparison" / "runs" / "full_factorial",
        out_dir,
    )
    sensitivity = _aggregate_sensitivity(
        source_root / "runs" / "E5_policy_comparison" / "runs" / "full_factorial",
        out_dir,
        repeats=int(args.repeats),
        seed=int(args.seed),
    )

    manifest = {
        "schema_version": "rq1_metric_baselines_v3_v1",
        "source_root": str(source_root.resolve()),
        "out_root": str(out_root.resolve()),
        "outputs": {
            "e1_metric_matched_scope_summary": str((out_dir / "e1_metric_matched_scope_summary.json").resolve()),
            "e5_metric_fullgrid_summary": str((out_dir / "e5_metric_fullgrid_summary.json").resolve()),
            "metric_baseline_sensitivity_summary": str((out_dir / "metric_baseline_sensitivity_summary.json").resolve()),
        },
        "summaries": {
            "e1_metric_matched_scope": e1_summary,
            "e5_metric_fullgrid": e5_summary,
            "metric_baseline_sensitivity": sensitivity["meta"],
        },
    }
    _write_json(out_dir / "manifest_rq1_metric_baselines.json", manifest)
    print("Wrote RQ1 metric baseline outputs to:", out_dir.resolve())


if __name__ == "__main__":
    main()
