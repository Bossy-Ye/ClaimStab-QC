from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from claimstab.figures.adaptive import classify_matrix_encoding, diagnose_matrix
from claimstab.figures.heatmap import _delta_label, _resolve_row_key


SPACES = ["compilation_only", "sampling_only", "combined_light"]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _heatmap_diag(df: pd.DataFrame, metric: str = "flip_rate_mean") -> tuple[str, tuple[int, int], float]:
    if df.empty:
        return "empty", (0, 0), 0.0
    frame = df.copy()
    frame["row_key"] = _resolve_row_key(frame)
    frame["col_key"] = frame["delta"].map(_delta_label)
    pivot = frame.pivot_table(index="row_key", columns="col_key", values=metric, aggfunc="mean")
    matrix = pivot.to_numpy(dtype=float) if not pivot.empty else np.array([[]], dtype=float)
    diag = diagnose_matrix(matrix)
    enc = classify_matrix_encoding(diag, near_constant_tol=0.01)
    return enc, matrix.shape if matrix.ndim == 2 else (0, 0), diag.value_range


def _parse_run_for_heatmap(name: str) -> tuple[str | None, str | None]:
    # heatmap_<run>_<space>.png
    stem = name.removesuffix(".png")
    if not stem.startswith("heatmap_"):
        return None, None
    body = stem[len("heatmap_") :]
    for space in SPACES:
        suffix = f"_{space}"
        if body.endswith(suffix):
            return body[: -len(suffix)], space
    return None, None


def _category_and_type_for_encoding(enc: str) -> tuple[str, str]:
    if enc == "heatmap":
        return "A", "heatmap (kept, style improved)"
    if enc in {"strip", "strip_constant"}:
        return "B", "ordered lollipop / strip profile"
    if enc in {"single_value", "constant_table"}:
        return "C", "compact annotated table/stat panel"
    return "D", "move to appendix/text summary"


def _load_claim_runs(input_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for run_dir in sorted((input_root / "large").glob("*")):
        if not run_dir.is_dir():
            continue
        claim_json = run_dir / "claim_stability.json"
        rq_json = run_dir / "rq_summary.json"
        if not claim_json.exists():
            continue
        out[run_dir.name] = {
            "claim_json": _load_json(claim_json),
            "rq_json": _load_json(rq_json) if rq_json.exists() else {},
        }
    return out


def build_audit_rows(fig_dir: Path, input_root: Path) -> list[dict[str, str]]:
    runs = _load_claim_runs(input_root)
    rows: list[dict[str, str]] = []

    top_pngs = sorted([p for p in fig_dir.glob("*.png") if p.is_file()])
    for path in top_pngs:
        name = path.name
        diagnosis = ""
        category = "A"
        recommended = "keep as chart with style refresh"
        reason = ""
        placement = "main"
        current = "unknown"

        if name.startswith("heatmap_"):
            run, space = _parse_run_for_heatmap(name)
            current = "heatmap"
            if run and space and run in runs:
                comp_rows = runs[run]["claim_json"].get("comparative", {}).get("space_claim_delta", [])
                cdf = pd.DataFrame([r for r in comp_rows if isinstance(r, dict)])
                cdf = cdf[cdf["space_preset"] == space] if not cdf.empty and "space_preset" in cdf.columns else pd.DataFrame()
                enc, shape, value_range = _heatmap_diag(cdf)
                category, recommended = _category_and_type_for_encoding(enc)
                diagnosis = f"matrix={shape[0]}x{shape[1]}, value_range={value_range:.4f}, encoding={enc}"
                reason = "Encoding now matches available structure and avoids low-information heatmaps."
                if run != "maxcut_ranking":
                    placement = "appendix"
                    if category in {"A", "B"}:
                        category = "D"
                        recommended = "appendix figure / text summary"
                        reason = "Control-track visual retained but de-emphasized from main paper."
        elif name.startswith("fig_stability_vs_shots_"):
            run = name.removeprefix("fig_stability_vs_shots_").removesuffix(".png")
            current = "line+CI"
            if run in runs:
                exps = runs[run]["claim_json"].get("experiments", [])
                point_count = 0
                for exp in exps:
                    bd = (exp.get("overall", {}).get("stability_vs_cost", {}).get("by_delta", {}))
                    if isinstance(bd, dict) and bd:
                        first_key = next(iter(bd))
                        arr = bd.get(first_key, [])
                        point_count = len(arr) if isinstance(arr, list) else 0
                        break
                if point_count <= 1:
                    category = "C"
                    recommended = "compact statistic panel"
                    diagnosis = f"single cost point ({point_count})"
                    reason = "Single-point curves were replaced by a concise CI summary card."
                else:
                    category = "A"
                    recommended = "line + CI band"
                    diagnosis = f"{point_count} cost points"
                    reason = "Trend and uncertainty are visible; line chart remains appropriate."
                if run != "maxcut_ranking":
                    placement = "appendix"
        elif name.startswith("fig_attribution_top_"):
            run = name.removeprefix("fig_attribution_top_").removesuffix(".png")
            current = "horizontal bar chart"
            rq2 = ((runs.get(run, {}).get("rq_json", {}).get("rq2_drivers") or {}).get("all_dimensions", []))
            adf = pd.DataFrame(rq2)
            metric = "driver_score" if "driver_score" in adf.columns else ("flip_rate" if "flip_rate" in adf.columns else None)
            if metric and not adf.empty:
                vals = pd.to_numeric(adf[metric], errors="coerce").dropna()
                vrange = float(vals.max() - vals.min()) if not vals.empty else 0.0
                if vrange < 1e-6:
                    category = "C"
                    recommended = "compact driver summary card"
                    diagnosis = "all driver scores identical"
                    reason = "Avoids misleading pseudo-ranking when there is no differential signal."
                else:
                    category = "B"
                    recommended = "ordered lollipop ranking"
                    diagnosis = f"value_range={vrange:.4f}"
                    reason = "Lollipop emphasizes rank contrast with less visual ink."
            if run != "maxcut_ranking":
                placement = "appendix"
        elif name.startswith("fig_rq7_main_effects_"):
            run = name.removeprefix("fig_rq7_main_effects_").removesuffix(".png")
            current = "horizontal bar chart"
            rq7 = ((runs.get(run, {}).get("rq_json", {}).get("rq7_effect_diagnostics") or {}).get("top_main_effects", []))
            edf = pd.DataFrame(rq7)
            vals = pd.to_numeric(edf.get("effect_score", pd.Series(dtype=float)), errors="coerce").dropna()
            vrange = float(vals.max() - vals.min()) if not vals.empty else 0.0
            if vrange < 1e-6:
                category = "C"
                recommended = "compact effect summary card"
                diagnosis = "all effect scores identical"
                reason = "Suppresses empty ranking visuals when no interaction/main-effect contrast exists."
            else:
                category = "B"
                recommended = "ordered lollipop ranking"
                diagnosis = f"value_range={vrange:.4f}"
                reason = "Improves readability and ranking contrast."
            if run != "maxcut_ranking":
                placement = "appendix"
        elif name.startswith("fig_naive_vs_claimstab_"):
            run = name.removeprefix("fig_naive_vs_claimstab_").removesuffix(".png")
            current = "grouped bar chart"
            comp_rows = runs.get(run, {}).get("claim_json", {}).get("comparative", {}).get("space_claim_delta", [])
            recs: list[dict[str, str]] = []
            for row in comp_rows if isinstance(comp_rows, list) else []:
                for field in ("naive_baseline", "naive_baseline_realistic"):
                    naive = row.get(field)
                    if isinstance(naive, dict):
                        recs.append({"comparison": str(naive.get("comparison", "")), "policy": str(naive.get("naive_policy", ""))})
            ndf = pd.DataFrame(recs)
            nz = int(ndf["comparison"].nunique()) if not ndf.empty and "comparison" in ndf.columns else 0
            if nz <= 1:
                category = "C"
                recommended = "compact summary card"
                diagnosis = "single comparison outcome"
                reason = "Card/table avoids sparse grouped bars with no contrast."
            else:
                category = "C"
                recommended = "compact policy-by-outcome table"
                diagnosis = f"{nz} comparison outcomes"
                reason = "Table is denser and clearer than low-count grouped bars."
            if run != "maxcut_ranking":
                placement = "appendix"
        elif name.startswith("fig_rq6_decisions_"):
            run = name.removeprefix("fig_rq6_decisions_").removesuffix(".png")
            current = "bar chart"
            counts = ((runs.get(run, {}).get("rq_json", {}).get("rq6_stratified_stability") or {}).get("decision_counts") or {})
            values = [int(counts.get("stable", 0)), int(counts.get("inconclusive", 0)), int(counts.get("unstable", 0))]
            nz = sum(1 for v in values if v > 0)
            if nz <= 1:
                category = "C"
                recommended = "compact stat card"
                diagnosis = f"nonzero_categories={nz}"
                reason = "Suppresses low-information bars."
            else:
                category = "B"
                recommended = "ordered lollipop counts"
                diagnosis = f"nonzero_categories={nz}"
                reason = "Count ranking is easier to scan than bars."
            if run != "maxcut_ranking":
                placement = "appendix"
        elif name.startswith("fig_rq5_robustness_map_"):
            run = name.removeprefix("fig_rq5_robustness_map_").removesuffix(".png")
            current = "stacked bar chart"
            payload = runs.get(run, {}).get("claim_json", {})
            by_delta: dict[str, dict[str, int]] = {}
            for exp in payload.get("experiments", []) if isinstance(payload.get("experiments", []), list) else []:
                cells_by_delta = ((exp.get("overall", {}).get("conditional_robustness", {}).get("cells_by_delta")) or {})
                for delta, cells in cells_by_delta.items():
                    slot = by_delta.setdefault(str(delta), {"stable": 0, "inconclusive": 0, "unstable": 0})
                    for cell in cells if isinstance(cells, list) else []:
                        dec = str(cell.get("decision", "inconclusive"))
                        if dec not in slot:
                            dec = "inconclusive"
                        slot[dec] += 1
            if by_delta:
                st = [v["stable"] for v in by_delta.values()]
                ic = [v["inconclusive"] for v in by_delta.values()]
                un = [v["unstable"] for v in by_delta.values()]
                const = (max(st) - min(st) == 0) and (max(ic) - min(ic) == 0) and (max(un) - min(un) == 0)
                if const:
                    category = "C"
                    recommended = "compact decision-count table"
                    diagnosis = "counts constant across deltas"
                    reason = "Table avoids repetitive stacked bars."
                else:
                    category = "A"
                    recommended = "stacked bars (kept)"
                    diagnosis = "delta-wise decision shifts present"
                    reason = "Stacked bars reveal frontier movement over deltas."
            if run != "maxcut_ranking":
                placement = "appendix"
                if category == "A":
                    category = "D"
                    recommended = "appendix figure"
                    reason = "Control-track robustness map retained but not main-story figure."
        elif name.startswith("space_profile_composite_"):
            run = name.removeprefix("space_profile_composite_").removesuffix(".png")
            current = "new composite profile"
            category = "E"
            recommended = "merged multi-space comparative panel"
            diagnosis = "consolidates per-space differences into one scanable figure"
            reason = "Reduces reader effort vs comparing three separate files."
            placement = "main" if run == "maxcut_ranking" else "appendix"
        elif name == "paper_claims_outcomes.png":
            current = "bar chart"
            category = "B"
            recommended = "forest plot (dot + CI whiskers)"
            diagnosis = "claim-level uncertainty is primary signal"
            reason = "Forest style communicates prevalence and CI without dense bars."
            placement = "main"
        else:
            current = "chart"
            diagnosis = "manual review required"
            reason = "No automatic rule matched."

        rows.append(
            {
                "figure": name,
                "category": category,
                "current_type": current,
                "diagnosis": diagnosis or "n/a",
                "recommended_type": recommended,
                "why_better": reason or "n/a",
                "paper_placement": placement,
                "improved_path": str((fig_dir / name).resolve()),
            }
        )

    # Subfolder figures (RQ4 + multidevice).
    rq4_summary = _load_json(input_root / "rq4_adaptive" / "rq4_adaptive_summary.json")
    if (fig_dir / "rq4_adaptive" / "fig_rq4_ci_width_vs_cost.png").exists():
        rows.append(
            {
                "figure": "rq4_adaptive/fig_rq4_ci_width_vs_cost.png",
                "category": "A",
                "current_type": "line chart",
                "diagnosis": "cost-width tradeoff has multi-strategy contrast",
                "recommended_type": "line chart (kept, restrained style)",
                "why_better": "Preserves tradeoff trend with cleaner typography and muted palette.",
                "paper_placement": "main",
                "improved_path": str((fig_dir / "rq4_adaptive" / "fig_rq4_ci_width_vs_cost.png").resolve()),
            }
        )
    if (fig_dir / "rq4_adaptive" / "fig_rq4_agreement_vs_cost.png").exists():
        agreements = []
        for row in rq4_summary.get("strategies", []) if isinstance(rq4_summary.get("strategies", []), list) else []:
            agreements.append(float((row.get("agreement_with_factorial") or {}).get("rate", 0.0)))
        flat = agreements and (max(agreements) - min(agreements) < 0.005)
        rows.append(
            {
                "figure": "rq4_adaptive/fig_rq4_agreement_vs_cost.png",
                "category": "C" if flat else "A",
                "current_type": "line chart",
                "diagnosis": "agreement nearly constant across strategies" if flat else "agreement differences visible",
                "recommended_type": "compact table (agreement/cost) " if flat else "line chart (kept)",
                "why_better": "Avoids a flat line chart when agreement provides little vertical contrast." if flat else "Trend chart remains informative.",
                "paper_placement": "main",
                "improved_path": str((fig_dir / "rq4_adaptive" / "fig_rq4_agreement_vs_cost.png").resolve()),
            }
        )
    for multi_name in ["fig_multidevice_stability_hat_heatmap.png", "fig_multidevice_ci_low_heatmap.png"]:
        path = fig_dir / "multidevice" / multi_name
        if path.exists():
            rows.append(
                {
                    "figure": f"multidevice/{multi_name}",
                    "category": "C",
                    "current_type": "heatmap",
                    "diagnosis": "device metrics exhibit narrow value range",
                    "recommended_type": "adaptive table/strip fallback",
                    "why_better": "Prevents near-constant heatmap blocks from hiding small but relevant differences.",
                    "paper_placement": "appendix",
                    "improved_path": str(path.resolve()),
                }
            )
    return rows


def write_markdown(rows: list[dict[str, str]], out_path: Path, fig_dir: Path) -> None:
    weakest_examples = [
        "redesign_examples/heatmap_bv_decision_sampling_only_before_after.png",
        "redesign_examples/fig_stability_vs_shots_maxcut_ranking_before_after.png",
        "redesign_examples/fig_attribution_top_ghz_structural_before_after.png",
        "redesign_examples/fig_rq7_main_effects_ghz_structural_before_after.png",
    ]
    lines: list[str] = []
    lines.append("# Figure Audit and Redesign (Full Pass)")
    lines.append("")
    lines.append("This audit evaluates each generated result figure for publication readiness and redesign suitability.")
    lines.append("")
    lines.append("## Reusable Figure Policy")
    lines.append("")
    lines.append("1. Use **bar charts** only when there are at least 3 non-degenerate categories and meaningful spread.")
    lines.append("2. Use **heatmaps** only when the matrix has meaningful 2D structure and non-trivial variation.")
    lines.append("3. Use **ordered dot/lollipop** plots for rank/contrast views, 1xN/Nx1 matrices, or sparse category counts.")
    lines.append("4. Use **compact annotated tables/stat cards** for single-value, near-constant, or single-category outputs.")
    lines.append("5. Use **composite figures** when the same pattern is repeated across spaces and side-by-side comparison is needed.")
    lines.append("6. Move low-variance control-track visuals to **appendix/text summary** when they do not add main-story signal.")
    lines.append("")
    lines.append("## Weakest Before vs After Examples")
    lines.append("")
    for rel in weakest_examples:
        p = fig_dir / rel
        if p.exists():
            lines.append(f"- [{rel}]({p.resolve()})")
    lines.append("")
    lines.append("## Per-Figure Audit")
    lines.append("")
    lines.append("| Figure | Category | Diagnosis | Recommended Type | Why Better | Placement | Improved Output |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in sorted(rows, key=lambda r: r["figure"]):
        lines.append(
            "| {figure} | {category} | {diagnosis} | {recommended_type} | {why_better} | {paper_placement} | {improved_path} |".format(
                **row
            )
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Audit current paper figures and emit redesign diagnostics.")
    ap.add_argument("--fig-dir", default="output/paper/pack/figures")
    ap.add_argument("--input-root", default="output/presentations/large")
    ap.add_argument("--out", default="output/paper/pack/figures/FIGURE_AUDIT_REDESIGN.md")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    fig_dir = Path(args.fig_dir)
    input_root = Path(args.input_root)
    out = Path(args.out)
    rows = build_audit_rows(fig_dir, input_root)
    write_markdown(rows, out, fig_dir)
    print(f"Wrote figure audit: {out}")
    print(f"Rows audited: {len(rows)}")


if __name__ == "__main__":
    main()
