from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from claimstab.results.report_helpers import (
    executive_summary,
    legacy_to_experiment,
    relative_ref,
    shots_diagnostic_text,
    shots_warning,
)
from claimstab.results.report_plots import plot_delta_curve, plot_factor_attribution, plot_shots_curve
from claimstab.results.report_renderers import (
    render_auxiliary_claims,
    render_comparative_table,
    render_conditional_robustness,
    render_delta_table,
    render_device_summary_table,
    render_dimension_breakdown,
    render_effect_diagnostics,
    render_evidence_chain,
    render_lockdown_recommendations,
    render_naive_summary,
    render_rq_summary,
    render_shots_curve_table,
    render_stratified_stability,
    render_top_unstable,
)
from claimstab.results.report_sections import is_section_enabled


def build_report_html(
    *,
    payload: dict[str, Any],
    out_path: Path,
    assets_dir: Path,
    with_plots: bool,
    selected_sections: set[str] | None,
) -> str:
    experiments = payload.get("experiments", [])
    if not experiments:
        experiments = [legacy_to_experiment(payload)]

    comparative_rows = payload.get("comparative", {}).get("space_claim_delta", [])
    device_rows = payload.get("device_summary", [])
    summary_bullets = executive_summary(experiments, comparative_rows)

    html_body = [
        "<html><head><meta charset='utf-8'><title>ClaimStab Report</title>",
        (
            "<style>"
            ":root{--bg:#f8f6f2;--panel:#fffdf8;--ink:#1e1f22;--line:#c8c2b6;--muted:#6a6a6a;"
            "--stable:#2d7f5e;--unstable:#b0413e;--inconclusive:#8a6f2f;}"
            "body{font-family:'Times New Roman',Times,'Nimbus Roman',serif;margin:24px;color:var(--ink);"
            "background:radial-gradient(circle at top right,#f2ece0 0%,var(--bg) 42%,#f7f4ee 100%);line-height:1.38;}"
            "table{border-collapse:collapse;margin:10px 0 16px 0;width:100%;background:var(--panel);}"
            "th,td{border:1px solid var(--line);padding:7px 10px;vertical-align:top;}"
            "th{background:#ece7da;font-family:'Times New Roman',Times,'Nimbus Roman',serif;font-size:0.94rem;letter-spacing:0.2px;}"
            "tr:nth-child(even) td{background:#fbf8f1;}"
            "h1,h2,h3,h4,h5{font-family:'Times New Roman',Times,'Nimbus Roman',serif;margin:11px 0 7px 0;letter-spacing:0.2px;}"
            "h1{font-size:2rem;border-bottom:2px solid #d8cfbd;padding-bottom:6px;}"
            "code{background:#eee8dd;padding:2px 5px;border-radius:4px;border:1px solid #d6cec0;}"
            "p{margin:4px 0 10px 0;}"
            ".badge{display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid transparent;"
            "font-size:0.83rem;font-weight:600;text-transform:lowercase;}"
            ".badge.stable{background:#e7f4ee;border-color:#b6dac8;color:var(--stable);}"
            ".badge.unstable{background:#faeceb;border-color:#e5b9b7;color:var(--unstable);}"
            ".badge.inconclusive{background:#f9f2e2;border-color:#e2d1ab;color:var(--inconclusive);}"
            ".badge.neutral{background:#efefef;border-color:#d4d4d4;color:#4c4c4c;}"
            "img{max-width:100%;height:auto;border:1px solid #cdc6b8;background:#fffdf8;padding:6px;box-shadow:0 1px 0 #ece6d9;}"
            "</style>"
        ),
        "</head><body>",
        "<h1>Claim Stability Report</h1>",
    ]

    meta_obj = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    if meta_obj:
        html_body.append(f"<p><b>Meta:</b> {html.escape(str(meta_obj))}</p>")
    if payload.get("batch"):
        html_body.append(f"<p><b>Batch:</b> {html.escape(str(payload['batch']))}</p>")
    if is_section_enabled("summary", selected_sections):
        html_body.append("<h2>Executive Summary</h2>")
        html_body.append("<ul>" + "".join(f"<li>{html.escape(b)}</li>" for b in summary_bullets[:3]) + "</ul>")
    if is_section_enabled("evidence_chain", selected_sections):
        html_body.append("<h2>Evidence Chain</h2>")
        html_body.append(render_evidence_chain(meta=meta_obj, experiments=experiments))

    if device_rows and is_section_enabled("device_summary", selected_sections):
        html_body.append("<h2>Per-Device Summary</h2>")
        html_body.append(render_device_summary_table(device_rows))

    if comparative_rows and is_section_enabled("claim_table", selected_sections):
        html_body.append("<h2>Claim Summary Table (Space x Claim x Delta)</h2>")
        html_body.append(render_comparative_table(comparative_rows))
    if comparative_rows and is_section_enabled("naive_comparison", selected_sections):
        html_body.append("<h2>Naive Baseline vs ClaimStab</h2>")
        html_body.append(render_naive_summary(comparative_rows))

    rq_summary = payload.get("rq_summary", {})
    if isinstance(rq_summary, dict) and rq_summary and is_section_enabled("rq_summary", selected_sections):
        html_body.append("<h2>RQ Summary (RQ1-RQ7)</h2>")
        html_body.append(render_rq_summary(rq_summary))

    for idx, experiment in enumerate(experiments):
        claim = experiment.get("claim", {})
        sampling = experiment.get("sampling", {})
        rule = experiment.get("stability_rule", {})
        backend = experiment.get("backend", {})
        overall = experiment.get("overall", {})
        delta_rows = overall.get("delta_sweep", [])
        per_graph = experiment.get("per_graph", {})
        aux = experiment.get("auxiliary_claims", {})

        html_body.append(f"<h2>Experiment {idx + 1}: {html.escape(str(experiment.get('experiment_id')))}</h2>")
        if is_section_enabled("experiment_summary", selected_sections):
            html_body.append(f"<p><b>Claim:</b> {html.escape(str(claim))}</p>")
            html_body.append(f"<p><b>Sampling:</b> {html.escape(str(sampling))}</p>")
            if isinstance(sampling, dict):
                adaptive = sampling.get("adaptive_stopping")
                if isinstance(adaptive, dict) and adaptive.get("enabled"):
                    html_body.append(
                        "<p><b>Adaptive CI stopping:</b> "
                        f"target_ci_width={html.escape(str(adaptive.get('target_ci_width')))}, "
                        f"achieved_ci_width={html.escape(str(adaptive.get('achieved_ci_width')))}, "
                        f"selected_configs={html.escape(str(adaptive.get('selected_configurations_with_baseline')))}, "
                        f"reason={html.escape(str(adaptive.get('stop_reason')))}"
                        "</p>"
                    )
            html_body.append(f"<p><b>Decision rule:</b> {html.escape(str(rule))}</p>")
            html_body.append(f"<p><b>Backend:</b> {html.escape(str(backend))}</p>")
        claim_type = str(claim.get("type", "ranking"))
        if is_section_enabled("delta_sweep", selected_sections):
            if claim_type == "ranking":
                html_body.append(
                    "<p><i>Flip definition:</i> a flip is a relation change from baseline under delta semantics (A_GT_B, A_EQ_B, A_LT_B).</p>"
                )
                html_body.append(
                    "<p><i>Interpretation note:</i> delta is a practical significance threshold, not a stability tuning knob. Read flip/stability together with holds rate.</p>"
                )
                html_body.append(
                    "<p><i>Clustered CI note:</i> clustered stability bootstraps across instances (not pooled runs) to reduce dependence concerns.</p>"
                )
            html_body.append("<h3>Delta Sweep Summary</h3>")
            html_body.append(render_delta_table(delta_rows))

        delta_plot_ok = False
        factor_plot_ok = False
        shots_plot_ok = False
        delta_plot = assets_dir / f"delta_sweep_{idx + 1}.png"
        factor_plot = assets_dir / f"factor_attribution_{idx + 1}.png"
        shots_plot = assets_dir / f"shots_stability_{idx + 1}.png"

        if claim_type == "ranking" and delta_rows and with_plots and is_section_enabled("delta_sweep", selected_sections):
            try:
                plot_delta_curve(delta_rows, delta_plot)
                delta_plot_ok = True
            except Exception as exc:
                print(f"[WARN] Could not render delta plot for experiment {idx + 1}: {exc}")

        selected_delta = str(delta_rows[0].get("delta")) if delta_rows else "0.0"
        if claim_type == "ranking" and with_plots and is_section_enabled("delta_sweep", selected_sections):
            try:
                factor_plot_ok = plot_factor_attribution(
                    per_graph,
                    selected_delta=selected_delta,
                    out_path=factor_plot,
                )
            except Exception as exc:
                print(f"[WARN] Could not render factor plot for experiment {idx + 1}: {exc}")
                factor_plot_ok = False

        if claim_type == "ranking" and delta_plot_ok and is_section_enabled("delta_sweep", selected_sections):
            delta_ref = relative_ref(delta_plot, out_path.parent)
            html_body.append("<h3>Delta Curve</h3>")
            html_body.append(f"<img src='{html.escape(delta_ref)}' width='700' />")

        if claim_type == "ranking" and factor_plot_ok and is_section_enabled("delta_sweep", selected_sections):
            factor_ref = relative_ref(factor_plot, out_path.parent)
            html_body.append("<h3>Example Graph Factor Attribution</h3>")
            html_body.append(f"<img src='{html.escape(factor_ref)}' width='760' />")

        stability_vs_cost = overall.get("stability_vs_cost", {})
        shots_rows_delta0 = stability_vs_cost.get("by_delta", {}).get(str(delta_rows[0].get("delta")) if delta_rows else "0.0", [])
        threshold = float(rule.get("threshold", 0.95)) if isinstance(rule, dict) else 0.95
        if with_plots and is_section_enabled("cost_curve", selected_sections):
            try:
                shots_plot_ok = plot_shots_curve(shots_rows_delta0, shots_plot, threshold=threshold)
            except Exception as exc:
                print(f"[WARN] Could not render shots curve for experiment {idx + 1}: {exc}")
                shots_plot_ok = False

        if is_section_enabled("cost_curve", selected_sections):
            html_body.append("<h3>Stability vs Cost (Shots)</h3>")
            for delta in [str(r.get("delta")) for r in delta_rows if r.get("delta") is not None]:
                rows_for_delta = stability_vs_cost.get("by_delta", {}).get(delta, [])
                html_body.append(f"<h4>delta={html.escape(delta)}</h4>")
                html_body.append(render_shots_curve_table(rows_for_delta))
                min_shots = stability_vs_cost.get("minimum_shots_for_stable", {}).get(delta)
                min_shots_text = str(min_shots) if min_shots is not None else "None within evaluated shot levels"
                html_body.append(f"<p><b>minimum_shots_for_stable:</b> {html.escape(min_shots_text)}</p>")
                warn = shots_warning(rows_for_delta)
                if warn:
                    html_body.append(f"<p><b>Warning:</b> {html.escape(warn)}</p>")
                html_body.append(f"<p><i>{html.escape(shots_diagnostic_text(rows_for_delta, threshold))}</i></p>")
            if shots_plot_ok:
                shots_ref = relative_ref(shots_plot, out_path.parent)
                html_body.append(f"<img src='{html.escape(shots_ref)}' width='700' />")

        diagnostics = overall.get("diagnostics", {})
        dim_by_delta = diagnostics.get("by_delta_dimension", {})
        top_by_delta = diagnostics.get("top_unstable_configs_by_delta", {})
        lockdown_by_delta = diagnostics.get("top_lockdown_recommendations_by_delta", {})
        if claim_type == "ranking" and (dim_by_delta or top_by_delta) and is_section_enabled("diagnostics", selected_sections):
            html_body.append("<h3>Failure Mode Diagnostics</h3>")
            for delta in [str(r.get("delta")) for r in delta_rows]:
                html_body.append(f"<h4>delta={html.escape(delta)}</h4>")
                html_body.append("<h5>Top Unstable Configurations</h5>")
                html_body.append(render_top_unstable(top_by_delta.get(delta, [])))
                html_body.append("<h5>Aggregated Factor Attribution</h5>")
                html_body.append(render_dimension_breakdown(dim_by_delta.get(delta, {})))
                html_body.append("<h5>Top Lock-Down Drivers (Fix knob to improve stability)</h5>")
                html_body.append(render_lockdown_recommendations(lockdown_by_delta.get(delta, [])))

        if claim_type == "ranking" and is_section_enabled("robustness_map", selected_sections):
            html_body.append("<h3>Conditional Robustness Map (RQ5-RQ7)</h3>")
            html_body.append(
                render_conditional_robustness(
                    overall.get("conditional_robustness", {}),
                    delta_rows=delta_rows,
                )
            )
            html_body.append("<h3>Stratified Stability</h3>")
            html_body.append(
                render_stratified_stability(
                    overall.get("stratified_stability", {}),
                    delta_rows=delta_rows,
                )
            )
            html_body.append("<h3>Main + Interaction Effects</h3>")
            html_body.append(
                render_effect_diagnostics(
                    overall.get("effect_diagnostics", {}),
                    delta_rows=delta_rows,
                )
            )

        if is_section_enabled("auxiliary_claims", selected_sections):
            html_body.append("<h3>Decision + Distribution Examples</h3>")
            html_body.append(render_auxiliary_claims(aux))
            if claim_type == "decision":
                failures = overall.get("decision_failures", [])
                if failures:
                    html_body.append("<h3>Top Failure Configurations</h3>")
                    html_body.append(f"<p>{html.escape(str(failures[:8]))}</p>")

    html_body.append("<h2>Reproduce</h2>")
    reproduce = payload.get("meta", {}).get("reproduce_command")
    if reproduce:
        html_body.append(f"<p><code>{html.escape(str(reproduce))}</code></p>")
    else:
        html_body.append("<p>Run the experiment script with your selected suite/space/claim settings, then regenerate this report from the JSON artifact.</p>")

    html_body.append("</body></html>")
    return "".join(html_body)
