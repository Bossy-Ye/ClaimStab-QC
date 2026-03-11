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
from claimstab.figures.heatmap import plot_fliprate_heatmap, plot_space_profile_composite
from claimstab.figures.icse_eval import (
    plot_claim_distribution,
    plot_cost_confidence_tradeoff,
    plot_space_flip_rate,
    plot_stability_profile,
    save_publication_figure,
)
from claimstab.figures.loaders import comparative_dataframe, load_claim_json
from claimstab.figures.robustness import plot_rq5_robustness_map, plot_rq6_decision_counts, plot_rq7_top_main_effects


def _collect_naive_rows(payload: dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    out: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field_name, policy in (
                ("naive_baseline", "legacy_strict_all"),
                ("naive_baseline_realistic", "default_researcher_v1"),
            ):
                naive = row.get(field_name)
                if not isinstance(naive, dict):
                    continue
                out.append(
                    {
                        "space_preset": row.get("space_preset"),
                        "claim_type": row.get("claim_type", "ranking"),
                        "comparison": naive.get("comparison"),
                        "policy": naive.get("naive_policy", policy),
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


def _task_label_from_run_name(run_name: str) -> str:
    token = str(run_name).strip().lower()
    if "maxcut" in token:
        return "MaxCut"
    if "ghz" in token:
        return "GHZ"
    if "bv" in token:
        return "BV"
    if "grover" in token:
        return "Grover"
    return run_name


def _pick_rq4_summary_path(*, input_dirs: list[Path], explicit: str | None) -> Path | None:
    if explicit:
        candidate = Path(explicit)
        return candidate if candidate.exists() else None
    candidates: list[Path] = []
    for in_dir in input_dirs:
        candidates.extend(
            [
                in_dir / "rq4_adaptive" / "rq4_adaptive_tuned_summary.json",
                in_dir / "rq4_adaptive" / "rq4_adaptive_summary.json",
                in_dir.parent / "rq4_adaptive" / "rq4_adaptive_tuned_summary.json",
                in_dir.parent / "rq4_adaptive" / "rq4_adaptive_summary.json",
            ]
        )
    candidates.extend(
        [
            Path("output/presentations/large/rq4_adaptive/rq4_adaptive_tuned_summary.json"),
            Path("output/presentations/large/rq4_adaptive/rq4_adaptive_summary.json"),
            Path("output/presentation_large/rq4_adaptive/rq4_adaptive_tuned_summary.json"),
            Path("output/presentation_large/rq4_adaptive/rq4_adaptive_summary.json"),
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _rq4_points_to_df(summary: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    strategies = summary.get("strategies", [])
    if not isinstance(strategies, list):
        return pd.DataFrame(rows)
    for strategy in strategies:
        if not isinstance(strategy, dict):
            continue
        detail_rows = strategy.get("rows_by_delta", [])
        if not isinstance(detail_rows, list) or not detail_rows:
            continue
        costs: list[float] = []
        widths: list[float] = []
        for drow in detail_rows:
            if not isinstance(drow, dict):
                continue
            try:
                low = float(drow.get("stability_ci_low"))
                high = float(drow.get("stability_ci_high"))
                costs.append(float(drow.get("n_claim_evals")))
                widths.append(max(0.0, high - low))
            except Exception:
                continue
        if not costs or not widths:
            continue
        rows.append(
            {
                "strategy": str(strategy.get("strategy", "unknown")),
                "cost": sum(costs) / len(costs),
                "ci_width": sum(widths) / len(widths),
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate paper-ready figures from ClaimStab outputs")
    ap.add_argument("--input-dir", default="output/presentations/large", help="Directory containing claim_stability.json")
    ap.add_argument("--also-calibration", default=None, help="Optional second directory to include")
    ap.add_argument("--output-dir", default="figures", help="Output figure directory")
    ap.add_argument("--threshold", type=float, default=0.95)
    ap.add_argument("--rq4-summary", default=None, help="Optional rq4_adaptive summary JSON path.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_dirs = [Path(args.input_dir)]
    if args.also_calibration:
        input_dirs.append(Path(args.also_calibration))

    manifests: dict[str, Any] = {"inputs": [str(p) for p in input_dirs], "figures": {}, "icse_main": {}, "icse_appendix": {}}
    json_jobs: list[Path] = []
    for in_dir in input_dirs:
        root_json = in_dir / "claim_stability.json"
        if root_json.exists():
            json_jobs.append(root_json)
            continue
        for candidate in sorted(in_dir.glob("*/claim_stability.json")):
            json_jobs.append(candidate)

    run_frames: dict[str, pd.DataFrame] = {}
    run_payloads: dict[str, dict[str, Any]] = {}
    for json_path in json_jobs:
        in_dir = json_path.parent
        payload = load_claim_json(json_path)
        run_payloads[in_dir.name] = payload
        comparative_df = comparative_dataframe(payload)
        run_frames[in_dir.name] = comparative_df.copy()
        for space in ["compilation_only", "sampling_only", "combined_light"]:
            if comparative_df.empty or "space_preset" not in comparative_df.columns:
                continue
            space_df = comparative_df[comparative_df["space_preset"] == space]
            fig_key = f"heatmap_{in_dir.name}_{space}"
            ref = plot_fliprate_heatmap(space_df, output_dir / fig_key)
            if ref:
                manifests["figures"][fig_key] = ref
        if not comparative_df.empty and "space_preset" in comparative_df.columns and comparative_df["space_preset"].nunique() >= 2:
            fig_key = f"space_profile_composite_{in_dir.name}"
            ref = plot_space_profile_composite(comparative_df, output_dir / fig_key)
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

    # ICSE main four-figure bundle.
    main_dir = output_dir / "main"
    appendix_dir = output_dir / "appendix"
    main_dir.mkdir(parents=True, exist_ok=True)
    appendix_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1 + Figure 2 from MaxCut main track.
    maxcut_df = run_frames.get("maxcut_ranking")
    if isinstance(maxcut_df, pd.DataFrame) and not maxcut_df.empty:
        fig = plot_stability_profile(maxcut_df, threshold=args.threshold)
        ref = save_publication_figure(fig, main_dir / "fig1_stability_profile")
        manifests["icse_main"]["fig1_stability_profile"] = ref
        # Paper figure 2: robustness summary by delta (maxcut, mechanism contrast).
        maxcut_payload = run_payloads.get("maxcut_ranking", {})
        ref = plot_rq5_robustness_map(maxcut_payload, main_dir / "fig2_robustness_cells_by_delta")
        if ref:
            manifests["icse_main"]["fig2_robustness_cells_by_delta"] = ref

    # Figure 3 from cross-task decision distributions.
    dist_rows: list[dict[str, Any]] = []
    for run_name, frame in run_frames.items():
        if frame.empty or "decision" not in frame.columns:
            continue
        task = _task_label_from_run_name(run_name)
        for decision in frame["decision"].astype(str).tolist():
            dist_rows.append({"task": task, "decision": decision})
    dist_df = pd.DataFrame(dist_rows)
    if not dist_df.empty:
        ref = save_publication_figure(plot_claim_distribution(dist_df), main_dir / "fig3_claim_distribution")
        manifests["icse_main"]["fig3_claim_distribution"] = ref

    # Figure 4 from E5 summary.
    rq4_summary_path = _pick_rq4_summary_path(input_dirs=input_dirs, explicit=args.rq4_summary)
    if rq4_summary_path and rq4_summary_path.exists():
        rq4_payload = json.loads(rq4_summary_path.read_text(encoding="utf-8"))
        rq4_df = _rq4_points_to_df(rq4_payload)
        if not rq4_df.empty:
            ref = save_publication_figure(plot_cost_confidence_tradeoff(rq4_df), main_dir / "fig4_cost_confidence_tradeoff")
            manifests["icse_main"]["fig4_cost_confidence_tradeoff"] = ref
            manifests["icse_main"]["rq4_summary_source"] = str(rq4_summary_path)

    # Stage degenerate/supporting panels into appendix.
    appendix_patterns = ("*ghz_structural*.*", "*bv_decision*.*", "*grover_distribution*.*", "multidevice/*.*")
    appendix_refs: list[str] = []
    for pattern in appendix_patterns:
        for src in output_dir.glob(pattern):
            if src.is_file() and src.suffix.lower() in {".png", ".pdf"}:
                dst = appendix_dir / src.name
                dst.write_bytes(src.read_bytes())
                appendix_refs.append(str(dst))
    if appendix_refs:
        manifests["icse_appendix"]["staged_files"] = appendix_refs

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
