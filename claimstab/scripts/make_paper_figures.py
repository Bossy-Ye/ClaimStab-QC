from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from claimstab.figures.attribution import plot_top_attribution_bars
from claimstab.figures.baseline_compare import plot_naive_vs_claimstab
from claimstab.figures.ci_shrink import plot_ci_width_vs_budget
from claimstab.figures.cost_curve import plot_stability_vs_shots
from claimstab.figures.heatmap import plot_fliprate_heatmap
from claimstab.figures.loaders import comparative_dataframe, load_claim_json
from claimstab.figures.robustness import plot_rq5_robustness_map, plot_rq6_decision_counts, plot_rq7_top_main_effects


def _collect_naive_rows(payload: dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    out: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            naive = row.get("naive_baseline")
            if isinstance(naive, dict):
                out.append(
                    {
                        "space_preset": row.get("space_preset"),
                        "claim_type": row.get("claim_type", "ranking"),
                        "comparison": naive.get("comparison"),
                    }
                )
    return pd.DataFrame(out)


def _collect_shots_rows(payload: dict[str, Any], *, threshold: float) -> pd.DataFrame:
    _ = threshold
    rows: list[dict[str, Any]] = []
    for exp in payload.get("experiments", []):
        overall = exp.get("overall", {})
        svs = overall.get("stability_vs_cost", {})
        by_delta = svs.get("by_delta", {})
        if not isinstance(by_delta, dict):
            continue
        for delta, delta_rows in by_delta.items():
            if not isinstance(delta_rows, list):
                continue
            for r in delta_rows:
                if isinstance(r, dict):
                    rows.append(dict(r, experiment_id=exp.get("experiment_id"), delta=delta))
    return pd.DataFrame(rows)


def _collect_adaptive_rows(payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for exp in payload.get("experiments", []):
        sampling = exp.get("sampling", {})
        if isinstance(sampling, dict):
            adaptive = sampling.get("adaptive_stopping")
            if isinstance(adaptive, dict) and adaptive.get("enabled"):
                rows.append(dict(adaptive, experiment_id=exp.get("experiment_id")))
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate paper-ready figures from ClaimStab outputs")
    ap.add_argument("--input-dir", default="output/exp_comprehensive_large", help="Directory containing claim_stability.json")
    ap.add_argument("--also-calibration", default=None, help="Optional second directory to include")
    ap.add_argument("--output-dir", default="figures", help="Output figure directory")
    ap.add_argument("--threshold", type=float, default=0.95)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_dirs = [Path(args.input_dir)]
    if args.also_calibration:
        input_dirs.append(Path(args.also_calibration))

    manifests: dict[str, Any] = {"inputs": [str(p) for p in input_dirs], "figures": {}}
    json_jobs: list[Path] = []
    for in_dir in input_dirs:
        root_json = in_dir / "claim_stability.json"
        if root_json.exists():
            json_jobs.append(root_json)
            continue
        for candidate in sorted(in_dir.glob("*/claim_stability.json")):
            json_jobs.append(candidate)

    for json_path in json_jobs:
        in_dir = json_path.parent
        payload = load_claim_json(json_path)
        comparative_df = comparative_dataframe(payload)
        for space in ["compilation_only", "sampling_only", "combined_light"]:
            if comparative_df.empty or "space_preset" not in comparative_df.columns:
                continue
            space_df = comparative_df[comparative_df["space_preset"] == space]
            fig_key = f"heatmap_{in_dir.name}_{space}"
            ref = plot_fliprate_heatmap(space_df, output_dir / fig_key)
            if ref:
                manifests["figures"][fig_key] = ref

        rq = payload.get("rq_summary", {})
        if isinstance(rq, dict):
            rq2 = rq.get("rq2_drivers", {})
            attr_df = pd.DataFrame(rq2.get("all_dimensions", []) if isinstance(rq2, dict) else [])
            ref = plot_top_attribution_bars(attr_df, output_dir / f"fig_attribution_top_{in_dir.name}")
            if ref:
                manifests["figures"][f"attribution_{in_dir.name}"] = ref
            ref = plot_rq5_robustness_map(payload, output_dir / f"fig_rq5_robustness_map_{in_dir.name}")
            if ref:
                manifests["figures"][f"rq5_robustness_map_{in_dir.name}"] = ref
            rq6 = rq.get("rq6_stratified_stability", {})
            ref = plot_rq6_decision_counts(
                rq6 if isinstance(rq6, dict) else {},
                output_dir / f"fig_rq6_decisions_{in_dir.name}",
            )
            if ref:
                manifests["figures"][f"rq6_decisions_{in_dir.name}"] = ref
            rq7 = rq.get("rq7_effect_diagnostics", {})
            ref = plot_rq7_top_main_effects(
                rq7 if isinstance(rq7, dict) else {},
                output_dir / f"fig_rq7_main_effects_{in_dir.name}",
            )
            if ref:
                manifests["figures"][f"rq7_effects_{in_dir.name}"] = ref

        shots_df = _collect_shots_rows(payload, threshold=args.threshold)
        ref = plot_stability_vs_shots(shots_df, output_dir / f"fig_stability_vs_shots_{in_dir.name}", threshold=args.threshold)
        if ref:
            manifests["figures"][f"shots_{in_dir.name}"] = ref

        adaptive_df = _collect_adaptive_rows(payload)
        ref = plot_ci_width_vs_budget(adaptive_df, output_dir / f"fig_ci_width_shrink_{in_dir.name}")
        if ref:
            manifests["figures"][f"adaptive_{in_dir.name}"] = ref

        naive_df = _collect_naive_rows(payload)
        ref = plot_naive_vs_claimstab(naive_df, output_dir / f"fig_naive_vs_claimstab_{in_dir.name}")
        if ref:
            manifests["figures"][f"naive_{in_dir.name}"] = ref

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
