from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


CONFIG_COLUMNS = [
    "seed_transpiler",
    "optimization_level",
    "layout_method",
    "shots",
    "seed_simulator",
]

FAMILY_SOURCES = [
    {
        "family": "MaxCut QAOA",
        "run_id": "E1",
        "run_root": Path("output/paper/evaluation_v2/runs/E1_maxcut_main"),
    },
    {
        "family": "Max-2-SAT QAOA",
        "run_id": "W1_max2sat",
        "run_root": Path("output/paper/evaluation_v3/runs/W1_max2sat_second_family"),
    },
    {
        "family": "VQE/H2",
        "run_id": "W1_vqe",
        "run_root": Path("output/paper/evaluation_v3/runs/W1_vqe_pilot"),
    },
]

SCOPE_LABELS = {
    "compilation_only_exact": "Compilation",
    "sampling_only_exact": "Sampling",
    "combined_light_exact": "Combined",
}
SCOPE_ORDER = ["compilation_only_exact", "sampling_only_exact", "combined_light_exact"]
VERDICT_COLORS = {
    "stable": "#2ca02c",
    "inconclusive": "#8c8c8c",
    "unstable": "#d62728",
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
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
        writer.writerows(rows)


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
    return (
        scores.pivot_table(
            index=["instance_id", "space_preset", *CONFIG_COLUMNS],
            columns="method",
            values="score",
            aggfunc="first",
        )
        .reset_index()
        .copy()
    )


def _parse_claim_pair(claim_pair: str) -> tuple[str, str]:
    left, right = claim_pair.split(">", 1)
    return left, right


def _claim_validation_outcome(*, baseline_claim_holds: bool | None, stability_decision: str) -> str:
    if stability_decision == "stable":
        return "validated" if baseline_claim_holds else "refuted"
    if stability_decision == "unstable":
        return "unstable"
    return "inconclusive"


def _extract_comparative_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    return [row for row in rows if isinstance(row, dict)]


def _derive_cross_family_metric_baselines(out_root: Path) -> dict[str, Any]:
    rq1_dir = out_root / "derived_paper_evaluation" / "RQ1_necessity"
    tables_dir = out_root / "pack" / "tables"
    figures_dir = out_root / "pack" / "figures" / "main"
    rq1_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    expanded_rows: list[dict[str, Any]] = []
    family_summary_rows: list[dict[str, Any]] = []
    verdict_rows_for_figure: list[dict[str, Any]] = []

    for source in FAMILY_SOURCES:
        family = str(source["family"])
        run_root = Path(source["run_root"])
        payload = _read_json(run_root / "claim_stability.json")
        pivot = _prepare_pivot(run_root / "scores.csv")
        claim_rows = _extract_comparative_rows(payload)
        claim_rows.sort(key=lambda row: (str(row["space_preset"]), str(row["claim_pair"]), float(row["delta"])))

        verdict_counts = {"stable": 0, "unstable": 0, "inconclusive": 0}
        for row in claim_rows:
            decision = str(row["decision"])
            if decision in verdict_counts:
                verdict_counts[decision] += 1

        for space in sorted({str(row["space_preset"]) for row in claim_rows}, key=lambda x: SCOPE_ORDER.index(x) if x in SCOPE_ORDER else 99):
            space_claim_rows = [row for row in claim_rows if str(row["space_preset"]) == space]
            scoped = pivot[pivot["space_preset"] == space].copy()
            for claim_pair in sorted({str(row["claim_pair"]) for row in space_claim_rows}):
                method_a, method_b = _parse_claim_pair(claim_pair)
                pair_claim_rows = [r for r in space_claim_rows if str(r["claim_pair"]) == claim_pair]
                representative = pair_claim_rows[0]
                higher_is_better = bool(representative.get("higher_is_better", True))
                diffs = scoped.copy()
                if higher_is_better:
                    diffs["diff"] = diffs[method_a] - diffs[method_b]
                else:
                    diffs["diff"] = diffs[method_b] - diffs[method_a]
                grouped = diffs.groupby(CONFIG_COLUMNS, dropna=False)["diff"].mean().reset_index()
                values = grouped["diff"].astype(float).tolist()
                mean_diff, ci_low, ci_high = _metric_ci(values)
                consistent = bool(mean_diff > 0 and ci_low > 0)

                for row in pair_claim_rows:
                    decision = str(row["decision"])
                    baseline_claim_holds = row.get("naive_baseline_realistic", {}).get("naive_holds")
                    claim_outcome = _claim_validation_outcome(
                        baseline_claim_holds=bool(baseline_claim_holds) if baseline_claim_holds is not None else None,
                        stability_decision=decision,
                    )
                    expanded_rows.append(
                        {
                            "family": family,
                            "run_id": source["run_id"],
                            "claim_pair": claim_pair,
                            "space_preset": space,
                            "delta": float(row["delta"]),
                            "higher_is_better": higher_is_better,
                            "metric_mean_diff": mean_diff,
                            "metric_ci_low": ci_low,
                            "metric_ci_high": ci_high,
                            "metric_supportive": consistent,
                            "claimstab_decision": decision,
                            "baseline_claim_holds": baseline_claim_holds,
                            "baseline_claim_holds_rate": row.get("naive_baseline_realistic", {}).get("naive_holds_rate"),
                            "claim_holds_rate_mean": row.get("holds_rate_mean"),
                            "claim_validation_outcome": claim_outcome,
                            "stability_hat": float(row["stability_hat"]),
                            "stability_ci_low": float(row["stability_ci_low"]),
                            "stability_ci_high": float(row["stability_ci_high"]),
                            "false_reassurance": bool(consistent and claim_outcome != "validated"),
                            "false_reassurance_refuted": bool(consistent and claim_outcome == "refuted"),
                            "false_reassurance_unstable": bool(consistent and decision == "unstable"),
                            "false_reassurance_inconclusive": bool(consistent and decision == "inconclusive"),
                        }
                    )

        family_rows = [row for row in expanded_rows if row["family"] == family]
        supportive_rows = [row for row in family_rows if bool(row["metric_supportive"])]
        false_rows = [row for row in supportive_rows if bool(row["false_reassurance"])]
        family_summary_rows.append(
            {
                "family": family,
                "run_id": source["run_id"],
                "total_variants": len(family_rows),
                "stable_count": verdict_counts["stable"],
                "inconclusive_count": verdict_counts["inconclusive"],
                "unstable_count": verdict_counts["unstable"],
                "validated_count": sum(1 for row in family_rows if row["claim_validation_outcome"] == "validated"),
                "refuted_count": sum(1 for row in family_rows if row["claim_validation_outcome"] == "refuted"),
                "metric_supportive_count": len(supportive_rows),
                "false_reassurance_count": len(false_rows),
                "false_reassurance_refuted_count": sum(1 for row in false_rows if row["claim_validation_outcome"] == "refuted"),
                "false_reassurance_unstable_count": sum(1 for row in false_rows if row["claimstab_decision"] == "unstable"),
                "false_reassurance_inconclusive_count": sum(1 for row in false_rows if row["claimstab_decision"] == "inconclusive"),
                "conditional_false_reassurance_rate": (len(false_rows) / len(supportive_rows)) if supportive_rows else None,
            }
        )
        verdict_rows_for_figure.append(
            {
                "family": family,
                "stable": verdict_counts["stable"],
                "inconclusive": verdict_counts["inconclusive"],
                "unstable": verdict_counts["unstable"],
                "total": len(family_rows),
            }
        )

    expanded_rows.sort(key=lambda row: (row["family"], row["space_preset"], row["claim_pair"], float(row["delta"])))
    family_summary_rows.sort(key=lambda row: row["family"])
    verdict_rows_for_figure.sort(key=lambda row: row["family"])

    _write_csv(rq1_dir / "cross_family_metric_baselines.csv", expanded_rows)
    _write_json(
        rq1_dir / "cross_family_metric_baselines.json",
        {"rows": expanded_rows, "family_summary": family_summary_rows},
    )
    _write_csv(tables_dir / "tab_a_cross_family_false_reassurance.csv", family_summary_rows)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, ax = plt.subplots(figsize=(6.3, 3.7))
    x = range(len(verdict_rows_for_figure))
    bottoms = [0.0] * len(verdict_rows_for_figure)
    for verdict in ["stable", "inconclusive", "unstable"]:
        heights = []
        for row in verdict_rows_for_figure:
            total = max(1, int(row["total"]))
            heights.append(100.0 * float(row[verdict]) / total)
        ax.bar(
            list(x),
            heights,
            bottom=bottoms,
            color=VERDICT_COLORS[verdict],
            edgecolor="white",
            width=0.68,
            label=verdict,
        )
        for idx, height in enumerate(heights):
            if height < 8:
                bottoms[idx] += height
                continue
            ax.text(
                idx,
                bottoms[idx] + height / 2.0,
                f"{height:.0f}%",
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                fontweight="bold",
            )
            bottoms[idx] += height
    for idx, row in enumerate(verdict_rows_for_figure):
        ax.text(idx, 102.0, f"n={row['total']}", ha="center", va="bottom", fontsize=9, color="#555555")
    ax.set_ylim(0, 108)
    ax.set_ylabel("verdict share (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([row["family"] for row in verdict_rows_for_figure])
    ax.set_title("Cross-Family Verdict Distribution")
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(figures_dir / "fig_a_cross_family_verdicts.png", dpi=240)
    fig.savefig(figures_dir / "fig_a_cross_family_verdicts.pdf")
    plt.close(fig)

    summary = {
        "families": family_summary_rows,
        "figure": str((figures_dir / "fig_a_cross_family_verdicts.png").resolve()),
        "table": str((tables_dir / "tab_a_cross_family_false_reassurance.csv").resolve()),
    }
    return summary


def _derive_scope_robustness(out_root: Path) -> dict[str, Any]:
    rq2_dir = out_root / "derived_paper_evaluation" / "RQ2_semantics"
    figures_dir = out_root / "pack" / "figures" / "main"
    rq2_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    selections = [
        {
            "case_id": "clear_stable",
            "source_run": "E2_ghz_structural",
            "source_path": Path("output/paper/evaluation_v2/runs/E2_ghz_structural/claim_stability.json"),
            "claim_pair": "GHZ_Linear>GHZ_Star",
            "delta": 0.0,
            "metric_name": "circuit_depth",
            "label": "Clear stable: GHZ_Linear > GHZ_Star",
        },
        {
            "case_id": "clear_unstable",
            "source_run": "E1_maxcut_main",
            "source_path": Path("output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json"),
            "claim_pair": "QAOA_p2>QAOA_p1",
            "delta": 0.05,
            "label": "Clear unstable: QAOA_p2 > QAOA_p1",
        },
        {
            "case_id": "near_boundary",
            "source_run": "W1_vqe_pilot",
            "source_path": Path("output/paper/evaluation_v3/runs/W1_vqe_pilot/claim_stability.json"),
            "claim_pair": "VQE_HEA>VQE_HF",
            "delta": 0.05,
            "label": "Near-boundary: VQE_HEA > VQE_HF",
        },
    ]

    rows: list[dict[str, Any]] = []
    case_summaries: list[dict[str, Any]] = []
    for selection in selections:
        payload = _read_json(Path(selection["source_path"]))
        candidates = [
            row
            for row in _extract_comparative_rows(payload)
            if str(row["claim_pair"]) == selection["claim_pair"] and float(row["delta"]) == float(selection["delta"])
        ]
        if selection.get("metric_name"):
            candidates = [row for row in candidates if str(row.get("metric_name")) == str(selection["metric_name"])]
        candidates.sort(key=lambda row: SCOPE_ORDER.index(str(row["space_preset"])) if str(row["space_preset"]) in SCOPE_ORDER else 99)
        decisions = [str(row["decision"]) for row in candidates]
        if all(decision == "stable" for decision in decisions):
            transport = "stable_transport"
        elif all(decision == "unstable" for decision in decisions):
            transport = "unstable_transport"
        elif "inconclusive" in decisions:
            transport = "abstention_under_scope_change"
        else:
            transport = "scope_flip"
        for row in candidates:
            rows.append(
                {
                    "case_id": selection["case_id"],
                    "label": selection["label"],
                    "source_run": selection["source_run"],
                    "claim_pair": selection["claim_pair"],
                    "delta": float(selection["delta"]),
                    "space_preset": str(row["space_preset"]),
                    "scope_label": SCOPE_LABELS.get(str(row["space_preset"]), str(row["space_preset"])),
                    "stability_hat": float(row["stability_hat"]),
                    "stability_ci_low": float(row["stability_ci_low"]),
                    "stability_ci_high": float(row["stability_ci_high"]),
                    "decision": str(row["decision"]),
                    "scope_transport": transport,
                }
            )
        case_summaries.append(
            {
                "case_id": selection["case_id"],
                "label": selection["label"],
                "source_run": selection["source_run"],
                "claim_pair": selection["claim_pair"],
                "delta": float(selection["delta"]),
                "decisions_by_scope": {str(row["space_preset"]): str(row["decision"]) for row in candidates},
                "scope_transport": transport,
            }
        )

    rows.sort(key=lambda row: (row["case_id"], SCOPE_ORDER.index(row["space_preset"]) if row["space_preset"] in SCOPE_ORDER else 99))
    _write_csv(rq2_dir / "scope_robustness.csv", rows)
    _write_json(rq2_dir / "scope_robustness.json", {"cases": case_summaries, "rows": rows})

    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.2), sharey=True)
    for ax, selection in zip(axes, selections, strict=True):
        case_rows = [row for row in rows if row["case_id"] == selection["case_id"]]
        xs = [SCOPE_ORDER.index(row["space_preset"]) for row in case_rows]
        ys = [row["stability_hat"] for row in case_rows]
        ax.plot(xs, ys, color="#4c566a", linewidth=1.2, zorder=1)
        for row, x, y in zip(case_rows, xs, ys, strict=True):
            ax.scatter(
                [x],
                [y],
                color=VERDICT_COLORS[row["decision"]],
                s=42,
                zorder=2,
            )
            ax.text(x, y + 0.02, row["decision"], ha="center", va="bottom", fontsize=8, color="#333333")
        ax.axhline(0.95, color="#555555", linestyle="--", linewidth=1.0)
        ax.set_title(selection["label"], fontsize=10)
        ax.set_xticks(range(len(SCOPE_ORDER)))
        ax.set_xticklabels([SCOPE_LABELS.get(scope, scope) for scope in SCOPE_ORDER], rotation=25, ha="right")
        ax.set_ylim(0.6, 1.03)
        ax.grid(axis="y", color="#e1e1e1", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("stability estimate ŝ")
    fig.suptitle("Scope-Robustness Under Declared Scope Broadening", y=1.02, fontsize=11)
    fig.tight_layout()
    fig.savefig(figures_dir / "fig_b_scope_robustness.png", dpi=240, bbox_inches="tight")
    fig.savefig(figures_dir / "fig_b_scope_robustness.pdf", bbox_inches="tight")
    plt.close(fig)

    return {
        "cases": case_summaries,
        "figure": str((figures_dir / "fig_b_scope_robustness.png").resolve()),
        "csv": str((rq2_dir / "scope_robustness.csv").resolve()),
    }


def _derive_exact_vs_heuristic_table(out_root: Path) -> dict[str, Any]:
    tables_dir = out_root / "pack" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for source in FAMILY_SOURCES:
        run_root = Path(source["run_root"])
        payload = _read_json(run_root / "claim_stability.json")
        for exp in payload.get("experiments", []):
            if not isinstance(exp, dict):
                continue
            robustness = ((exp.get("overall") or {}).get("conditional_robustness") or {})
            exact_by_delta = robustness.get("exact_mos_by_delta")
            heuristic_by_delta = robustness.get("minimal_lockdown_set_by_delta")
            if not isinstance(exact_by_delta, dict) or not isinstance(heuristic_by_delta, dict):
                continue
            claim = exp.get("claim", {})
            claim_label = ">".join(
                part
                for part in [claim.get("method_a"), claim.get("method_b")]
                if isinstance(part, str) and part
            )
            for delta, exact_payload in exact_by_delta.items():
                heuristic_payload = heuristic_by_delta.get(delta, {})
                exact_best = exact_payload.get("best") if isinstance(exact_payload, dict) else None
                heuristic_best = heuristic_payload.get("best") if isinstance(heuristic_payload, dict) else None
                exact_dims = list((exact_best or {}).get("lock_dimensions", [])) if isinstance(exact_best, dict) else []
                heuristic_dims = list((heuristic_best or {}).get("lock_dimensions", [])) if isinstance(heuristic_best, dict) else []
                rows.append(
                    {
                        "family": source["family"],
                        "run_id": source["run_id"],
                        "experiment_id": exp.get("experiment_id"),
                        "claim_pair": claim_label,
                        "space_preset": ((exp.get("sampling") or {}).get("space_preset")),
                        "delta": delta,
                        "exact_mos_size": len(exact_dims) if exact_dims else None,
                        "greedy_mos_size": len(heuristic_dims) if heuristic_dims else None,
                        "overlap_count": len(set(exact_dims) & set(heuristic_dims)),
                        "exact_lock_dimensions": exact_dims,
                        "greedy_lock_dimensions": heuristic_dims,
                        "heuristic_source": "minimal_lockdown_set_by_delta",
                    }
                )
    if not rows:
        return {"available": False}
    rows.sort(key=lambda row: (row["family"], str(row["space_preset"]), str(row["claim_pair"]), str(row["delta"])))
    _write_csv(tables_dir / "tab_c_exact_vs_greedy_mos.csv", rows)
    return {
        "available": True,
        "table": str((tables_dir / "tab_c_exact_vs_greedy_mos.csv").resolve()),
        "rows": len(rows),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Derive ICSE strengthening artifacts into evaluation_v4.")
    ap.add_argument("--out-root", default="output/paper/evaluation_v4")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out_root = Path(args.out_root)
    for path in [
        out_root / "derived_paper_evaluation" / "RQ1_necessity",
        out_root / "derived_paper_evaluation" / "RQ2_semantics",
        out_root / "pack" / "figures" / "main",
        out_root / "pack" / "tables",
        out_root / "manifests",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    a_summary = _derive_cross_family_metric_baselines(out_root)
    b_summary = _derive_scope_robustness(out_root)
    c_summary = _derive_exact_vs_heuristic_table(out_root)

    manifest = {
        "schema_version": "icse_strengthening_v4_v1",
        "out_root": str(out_root.resolve()),
        "A": a_summary,
        "B": b_summary,
        "C": c_summary,
    }
    _write_json(out_root / "manifests" / "icse_strengthening_manifest.json", manifest)
    print(f"Wrote ICSE strengthening artifacts under: {out_root.resolve()}")


if __name__ == "__main__":
    main()
