from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from claimstab.figures.style import SERIF_FALLBACK
from claimstab.results.report_sections import available_sections_text, is_section_enabled, parse_sections_arg


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _numeric_sort_key(value: Any) -> tuple[int, float | str]:
    text = str(value)
    try:
        return (0, float(text))
    except Exception:
        return (1, text)


def _report_plot_rc() -> dict[str, Any]:
    return {
        "figure.facecolor": "#fbfaf7",
        "axes.facecolor": "#f7f5ef",
        "font.family": "serif",
        "font.serif": SERIF_FALLBACK,
        "mathtext.fontset": "stix",
        "axes.titleweight": "semibold",
        "axes.grid": True,
        "grid.linestyle": "-",
        "grid.color": "#b2b2b2",
        "grid.linewidth": 0.75,
        "grid.alpha": 0.24,
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.facecolor": "white",
        "legend.edgecolor": "#c7c7c7",
        "legend.fancybox": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }


def _decision_badge(value: Any) -> str:
    label = str(value)
    css = "neutral"
    if label == "stable":
        css = "stable"
    elif label == "unstable":
        css = "unstable"
    elif label == "inconclusive":
        css = "inconclusive"
    return f"<span class='badge {css}'>{html.escape(label)}</span>"


def _decision_count(row: dict[str, Any], label: str) -> int:
    counts = row.get("decision_counts")
    if isinstance(counts, dict):
        return int(counts.get(label, 0))
    fallback_key = f"{label}_count"
    return int(row.get(fallback_key, 0))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate an HTML claim-stability report from JSON output")
    ap.add_argument("--json", required=True, help="Path to rankflip JSON artifact")
    ap.add_argument("--out", default=None, help="Output HTML path; default: <json_dir>/stability_report.html")
    ap.add_argument("--assets-dir", default=None, help="Directory for generated plot assets")
    ap.add_argument("--with-plots", action="store_true", help="Attempt to render plot images (requires matplotlib/font support)")
    ap.add_argument(
        "--sections",
        default="",
        help=(
            "Optional comma-separated section ids. If empty, default layout is unchanged. "
            f"Available ids: {available_sections_text()}."
        ),
    )
    return ap.parse_args()


def _render_delta_table(delta_rows: list[dict[str, Any]]) -> str:
    header = (
        "<tr>"
        "<th>delta</th>"
        "<th>flip_rate_mean</th>"
        "<th>flip_rate_max</th>"
        "<th>flip_rate_min</th>"
        "<th>holds_rate_mean</th>"
        "<th>holds_rate_ci_low</th>"
        "<th>holds_rate_ci_high</th>"
        "<th>stability_hat</th>"
        "<th>stability_ci_low</th>"
        "<th>stability_ci_high</th>"
        "<th>decision</th>"
        "<th>clustered_stability_mean</th>"
        "<th>clustered_stability_ci_low</th>"
        "<th>clustered_stability_ci_high</th>"
        "<th>clustered_decision</th>"
        "<th>n_instances</th>"
        "<th>n_claim_evals</th>"
        "<th>stable</th>"
        "<th>unstable</th>"
        "<th>inconclusive</th>"
        "</tr>"
    )
    rows = []
    for row in delta_rows:
        rows.append(
            "<tr>"
            f"<td>{row.get('delta')}</td>"
            f"<td>{row.get('flip_rate_mean')}</td>"
            f"<td>{row.get('flip_rate_max')}</td>"
            f"<td>{row.get('flip_rate_min')}</td>"
            f"<td>{row.get('holds_rate_mean')}</td>"
            f"<td>{row.get('holds_rate_ci_low')}</td>"
            f"<td>{row.get('holds_rate_ci_high')}</td>"
            f"<td>{row.get('stability_hat')}</td>"
            f"<td>{row.get('stability_ci_low')}</td>"
            f"<td>{row.get('stability_ci_high')}</td>"
            f"<td>{_decision_badge(row.get('decision'))}</td>"
            f"<td>{row.get('clustered_stability_mean')}</td>"
            f"<td>{row.get('clustered_stability_ci_low')}</td>"
            f"<td>{row.get('clustered_stability_ci_high')}</td>"
            f"<td>{_decision_badge(row.get('clustered_decision'))}</td>"
            f"<td>{row.get('n_instances')}</td>"
            f"<td>{row.get('n_claim_evals')}</td>"
            f"<td>{_decision_count(row, 'stable')}</td>"
            f"<td>{_decision_count(row, 'unstable')}</td>"
            f"<td>{_decision_count(row, 'inconclusive')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(rows)}</table>"


def _render_comparative_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "<tr>"
        "<th>space_preset</th>"
        "<th>claim_pair</th>"
        "<th>delta</th>"
        "<th>flip_rate_mean</th>"
        "<th>holds_rate_mean</th>"
        "<th>holds_rate_ci_low</th>"
        "<th>holds_rate_ci_high</th>"
        "<th>stability_hat</th>"
        "<th>stability_ci_low</th>"
        "<th>stability_ci_high</th>"
        "<th>decision</th>"
        "<th>clustered_stability_mean</th>"
        "<th>clustered_stability_ci_low</th>"
        "<th>clustered_stability_ci_high</th>"
        "<th>clustered_decision</th>"
        "<th>stable</th>"
        "<th>unstable</th>"
        "<th>inconclusive</th>"
        "</tr>"
    )
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('space_preset')))}</td>"
            f"<td>{html.escape(str(row.get('claim_pair')))}</td>"
            f"<td>{row.get('delta')}</td>"
            f"<td>{row.get('flip_rate_mean')}</td>"
            f"<td>{row.get('holds_rate_mean')}</td>"
            f"<td>{row.get('holds_rate_ci_low')}</td>"
            f"<td>{row.get('holds_rate_ci_high')}</td>"
            f"<td>{row.get('stability_hat')}</td>"
            f"<td>{row.get('stability_ci_low')}</td>"
            f"<td>{row.get('stability_ci_high')}</td>"
            f"<td>{_decision_badge(row.get('decision'))}</td>"
            f"<td>{row.get('clustered_stability_mean')}</td>"
            f"<td>{row.get('clustered_stability_ci_low')}</td>"
            f"<td>{row.get('clustered_stability_ci_high')}</td>"
            f"<td>{_decision_badge(row.get('clustered_decision'))}</td>"
            f"<td>{_decision_count(row, 'stable')}</td>"
            f"<td>{_decision_count(row, 'unstable')}</td>"
            f"<td>{_decision_count(row, 'inconclusive')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def _render_device_summary_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "<tr>"
        "<th>batch_mode</th>"
        "<th>device_name</th>"
        "<th>metric_name</th>"
        "<th>claim_pair</th>"
        "<th>delta</th>"
        "<th>flip_rate_mean</th>"
        "<th>holds_rate_mean</th>"
        "<th>stability_hat</th>"
        "<th>stability_ci_low</th>"
        "<th>stability_ci_high</th>"
        "<th>decision</th>"
        "<th>stable</th>"
        "<th>unstable</th>"
        "<th>inconclusive</th>"
        "</tr>"
    )
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('batch_mode')))}</td>"
            f"<td>{html.escape(str(row.get('device_name')))}</td>"
            f"<td>{html.escape(str(row.get('metric_name')))}</td>"
            f"<td>{html.escape(str(row.get('claim_pair')))}</td>"
            f"<td>{row.get('delta')}</td>"
            f"<td>{row.get('flip_rate_mean')}</td>"
            f"<td>{row.get('holds_rate_mean')}</td>"
            f"<td>{row.get('stability_hat')}</td>"
            f"<td>{row.get('stability_ci_low')}</td>"
            f"<td>{row.get('stability_ci_high')}</td>"
            f"<td>{_decision_badge(row.get('decision'))}</td>"
            f"<td>{_decision_count(row, 'stable')}</td>"
            f"<td>{_decision_count(row, 'unstable')}</td>"
            f"<td>{_decision_count(row, 'inconclusive')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def _render_top_unstable(top_events: list[dict[str, Any]]) -> str:
    if not top_events:
        return "<p>No flip events.</p>"
    header = (
        "<tr>"
        "<th>graph_id</th>"
        "<th>config</th>"
        "<th>score_a</th>"
        "<th>score_b</th>"
        "<th>baseline_relation</th>"
        "<th>perturbed_relation</th>"
        "<th>flip_severity</th>"
        "<th>margin_to_threshold</th>"
        "</tr>"
    )
    rows = []
    for event in top_events:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(event.get('graph_id')))}</td>"
            f"<td><code>{html.escape(str(event.get('config')))}</code></td>"
            f"<td>{event.get('score_a')}</td>"
            f"<td>{event.get('score_b')}</td>"
            f"<td>{html.escape(str(event.get('baseline_relation')))}</td>"
            f"<td>{html.escape(str(event.get('perturbed_relation')))}</td>"
            f"<td>{event.get('flip_severity')}</td>"
            f"<td>{event.get('margin_to_threshold')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(rows)}</table>"


def _render_dimension_breakdown(by_dim: dict[str, dict[str, dict[str, Any]]]) -> str:
    if not by_dim:
        return "<p>No factor attribution available.</p>"
    sections = []
    for dim_name, values in by_dim.items():
        header = "<tr><th>value</th><th>flip_rate</th><th>flips</th><th>total</th></tr>"
        rows = []
        for value, stats in values.items():
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(value))}</td>"
                f"<td>{stats.get('flip_rate')}</td>"
                f"<td>{stats.get('flips')}</td>"
                f"<td>{stats.get('total')}</td>"
                "</tr>"
            )
        sections.append(f"<h5>{html.escape(dim_name)}</h5><table>{header}{''.join(rows)}</table>")
    return "".join(sections)


def _render_lockdown_recommendations(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No lockdown recommendations available.</p>"
    header = (
        "<tr>"
        "<th>dimension</th>"
        "<th>value</th>"
        "<th>avg_flip_rate_improvement</th>"
        "<th>avg_flip_rate</th>"
        "<th>avg_stability_hat</th>"
        "<th>count</th>"
        "</tr>"
    )
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('dimension')))}</td>"
            f"<td>{html.escape(str(row.get('value')))}</td>"
            f"<td>{row.get('avg_flip_rate_improvement')}</td>"
            f"<td>{row.get('avg_flip_rate')}</td>"
            f"<td>{row.get('avg_stability_hat')}</td>"
            f"<td>{row.get('count')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def _render_conditional_robustness(
    robustness: dict[str, Any],
    *,
    delta_rows: list[dict[str, Any]],
) -> str:
    if not isinstance(robustness, dict) or not robustness:
        return "<p>No conditional robustness map available.</p>"

    robust_core = robustness.get("robust_core_by_delta", {})
    failure_frontier = robustness.get("failure_frontier_by_delta", {})
    lockdown = robustness.get("minimal_lockdown_set_by_delta", {})
    cells = robustness.get("cells_by_delta", {})

    deltas = [str(r.get("delta")) for r in delta_rows if r.get("delta") is not None]
    if not deltas:
        keys = set()
        if isinstance(robust_core, dict):
            keys.update(str(k) for k in robust_core.keys())
        if isinstance(failure_frontier, dict):
            keys.update(str(k) for k in failure_frontier.keys())
        deltas = sorted(keys, key=_numeric_sort_key)

    out: list[str] = []
    for delta in deltas:
        core_rows = robust_core.get(delta, []) if isinstance(robust_core, dict) else []
        frontier_rows = failure_frontier.get(delta, []) if isinstance(failure_frontier, dict) else []
        lock_payload = lockdown.get(delta, {}) if isinstance(lockdown, dict) else {}
        lock_best = lock_payload.get("best", {}) if isinstance(lock_payload, dict) else {}
        cell_rows = cells.get(delta, []) if isinstance(cells, dict) else []

        out.append(f"<h4>delta={html.escape(delta)}</h4>")
        out.append(
            "<p>"
            f"cells={len(cell_rows) if isinstance(cell_rows, list) else 0}, "
            f"robust_core={len(core_rows) if isinstance(core_rows, list) else 0}, "
            f"failure_frontier={len(frontier_rows) if isinstance(frontier_rows, list) else 0}"
            "</p>"
        )

        if isinstance(core_rows, list) and core_rows:
            top = core_rows[0] if isinstance(core_rows[0], dict) else {}
            out.append(
                "<p><b>Robust core example:</b> "
                f"conditions={html.escape(str(top.get('conditions', {})))}, "
                f"CI_low={html.escape(str(top.get('stability_ci_low')))}, "
                f"decision={html.escape(str(top.get('decision')))}</p>"
            )
        if isinstance(frontier_rows, list) and frontier_rows:
            top = frontier_rows[0] if isinstance(frontier_rows[0], dict) else {}
            out.append(
                "<p><b>Failure frontier example:</b> "
                f"changed_dimension={html.escape(str(top.get('changed_dimension')))}, "
                f"stable={html.escape(str(top.get('stable_conditions', {})))}, "
                f"unstable={html.escape(str(top.get('unstable_conditions', {})))}</p>"
            )
        if isinstance(lock_best, dict) and lock_best:
            out.append(
                "<p><b>Minimal lockdown set:</b> "
                f"lock_dimensions={html.escape(str(lock_best.get('lock_dimensions', [])))}, "
                f"conditions={html.escape(str(lock_best.get('conditions', {})))}, "
                f"decision={html.escape(str(lock_best.get('decision')))}</p>"
            )

    return "".join(out) if out else "<p>No conditional robustness map available.</p>"


def _render_stratified_stability(
    stratified: dict[str, Any],
    *,
    delta_rows: list[dict[str, Any]],
) -> str:
    if not isinstance(stratified, dict) or not stratified:
        return "<p>No stratified stability summary available.</p>"
    by_delta = stratified.get("by_delta", {})
    if not isinstance(by_delta, dict):
        return "<p>No stratified stability summary available.</p>"

    deltas = [str(r.get("delta")) for r in delta_rows if r.get("delta") is not None]
    if not deltas:
        deltas = sorted([str(k) for k in by_delta.keys()], key=_numeric_sort_key)

    out: list[str] = []
    dims = stratified.get("strata_dimensions", [])
    if isinstance(dims, list) and dims:
        out.append(f"<p><b>Strata dimensions:</b> {html.escape(', '.join(str(x) for x in dims))}</p>")

    header = (
        "<tr><th>conditions</th><th>decision</th><th>n_instances</th><th>n_eval</th>"
        "<th>flip_rate</th><th>stability_ci_low</th><th>stability_ci_high</th></tr>"
    )
    for delta in deltas:
        rows = by_delta.get(delta, [])
        if not isinstance(rows, list) or not rows:
            continue
        body = []
        for row in rows[:6]:
            if not isinstance(row, dict):
                continue
            body.append(
                "<tr>"
                f"<td><code>{html.escape(str(row.get('conditions', {})))}</code></td>"
                f"<td>{_decision_badge(row.get('decision'))}</td>"
                f"<td>{html.escape(str(row.get('n_instances')))}</td>"
                f"<td>{html.escape(str(row.get('n_eval')))}</td>"
                f"<td>{html.escape(str(row.get('flip_rate')))}</td>"
                f"<td>{html.escape(str(row.get('stability_ci_low')))}</td>"
                f"<td>{html.escape(str(row.get('stability_ci_high')))}</td>"
                "</tr>"
            )
        if body:
            out.append(f"<h4>delta={html.escape(delta)}</h4>")
            out.append("<table>" + header + "".join(body) + "</table>")

    return "".join(out) if out else "<p>No stratified stability summary available.</p>"


def _render_effect_diagnostics(
    effects: dict[str, Any],
    *,
    delta_rows: list[dict[str, Any]],
) -> str:
    if not isinstance(effects, dict) or not effects:
        return "<p>No effect diagnostics available.</p>"
    by_delta = effects.get("by_delta", {})
    if not isinstance(by_delta, dict):
        return "<p>No effect diagnostics available.</p>"

    deltas = [str(r.get("delta")) for r in delta_rows if r.get("delta") is not None]
    if not deltas:
        deltas = sorted([str(k) for k in by_delta.keys()], key=_numeric_sort_key)

    out: list[str] = []
    for delta in deltas:
        payload = by_delta.get(delta, {})
        if not isinstance(payload, dict):
            continue
        main_effects = payload.get("main_effects", [])
        interactions = payload.get("interaction_effects", [])
        out.append(f"<h4>delta={html.escape(delta)}</h4>")

        if isinstance(main_effects, list) and main_effects:
            main_header = "<tr><th>dimension</th><th>effect_score</th><th>n_levels</th><th>n_eval</th></tr>"
            main_rows = []
            for row in main_effects[:5]:
                if not isinstance(row, dict):
                    continue
                main_rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(row.get('dimension')))}</td>"
                    f"<td>{html.escape(str(row.get('effect_score')))}</td>"
                    f"<td>{html.escape(str(row.get('n_levels')))}</td>"
                    f"<td>{html.escape(str(row.get('n_eval')))}</td>"
                    "</tr>"
                )
            if main_rows:
                out.append("<p><b>Main effects</b></p>")
                out.append("<table>" + main_header + "".join(main_rows) + "</table>")

        if isinstance(interactions, list) and interactions:
            int_header = (
                "<tr><th>dimensions</th><th>interaction_score</th><th>joint_spread</th>"
                "<th>reference_main_effect</th><th>n_cells</th><th>n_eval</th></tr>"
            )
            int_rows = []
            for row in interactions[:5]:
                if not isinstance(row, dict):
                    continue
                int_rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(row.get('dimensions')))}</td>"
                    f"<td>{html.escape(str(row.get('interaction_score')))}</td>"
                    f"<td>{html.escape(str(row.get('joint_spread')))}</td>"
                    f"<td>{html.escape(str(row.get('reference_main_effect')))}</td>"
                    f"<td>{html.escape(str(row.get('n_cells')))}</td>"
                    f"<td>{html.escape(str(row.get('n_eval')))}</td>"
                    "</tr>"
                )
            if int_rows:
                out.append("<p><b>Top interactions</b></p>")
                out.append("<table>" + int_header + "".join(int_rows) + "</table>")

    return "".join(out) if out else "<p>No effect diagnostics available.</p>"


def _render_shots_curve_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No shots-by-stability data.</p>"
    header = (
        "<tr>"
        "<th>shots</th>"
        "<th>n_eval</th>"
        "<th>flip_rate</th>"
        "<th>stability_hat</th>"
        "<th>stability_ci_low</th>"
        "<th>stability_ci_high</th>"
        "<th>ci_width</th>"
        "<th>decision</th>"
        "</tr>"
    )
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{row.get('shots')}</td>"
            f"<td>{row.get('n_eval')}</td>"
            f"<td>{row.get('flip_rate')}</td>"
            f"<td>{row.get('stability_hat')}</td>"
            f"<td>{row.get('stability_ci_low')}</td>"
            f"<td>{row.get('stability_ci_high')}</td>"
            f"<td>{row.get('ci_width')}</td>"
            f"<td>{_decision_badge(row.get('decision'))}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def _shots_warning(rows: list[dict[str, Any]]) -> str | None:
    if len(rows) == 1:
        return "Only one shots value available; cannot infer trend. Add more shots levels to estimate minimum required shots."
    return None


def _shots_diagnostic_text(rows: list[dict[str, Any]], threshold: float) -> str:
    if not rows:
        return "No shots-by-stability data available."
    widths = [_as_float(row.get("stability_ci_high"), 0.0) - _as_float(row.get("stability_ci_low"), 0.0) for row in rows]
    max_width = max(widths) if widths else 0.0
    any_stable = any(str(row.get("decision")) == "stable" for row in rows)
    if not any_stable:
        best = max(rows, key=lambda r: _as_float(r.get("stability_ci_low"), 0.0))
        if max_width > 0.05:
            return (
                "CI is wide in this shots sweep (>0.05): increase n_eval (more perturbation samples or more instances) "
                "before concluding stability cannot be reached."
            )
        if _as_float(best.get("stability_hat"), 0.0) < threshold:
            return (
                "CI is relatively narrow and stability_hat is below threshold: observed instability appears genuine; "
                "increasing shots may or may not help without changing other perturbation controls."
            )
        return (
            "CI is relatively narrow but CI lower bound stays below threshold: the conservative rule still rejects stability "
            "for evaluated shot levels."
        )
    if max_width > 0.05:
        return "Some shot levels are already stable, but CI is wide for others; increase n_eval for tighter uncertainty."
    return "CI width is reasonably tight for most shot levels; decisions are likely driven by measured stability rather than sampling noise."


def _render_auxiliary_claims(aux: dict[str, Any]) -> str:
    if not aux:
        return "<p>No auxiliary decision/distribution examples.</p>"
    sections = []
    graph_id = aux.get("graph_id")
    if graph_id:
        sections.append(f"<p><b>Reference graph:</b> {html.escape(str(graph_id))}</p>")
    decision_example = aux.get("decision_example", {})
    if decision_example:
        sections.append("<h4>Decision Claim Example</h4>")
        sections.append(f"<p><b>Rule:</b> {html.escape(str(decision_example.get('rule')))}</p>")
        sections.append(
            "<p>"
            f"accepted={decision_example.get('accepted')} / total={decision_example.get('total')}, "
            f"acceptance_rate={decision_example.get('acceptance_rate')}, "
            f"CI=[{decision_example.get('ci_low')}, {decision_example.get('ci_high')}], "
            f"decision={decision_example.get('decision')}"
            "</p>"
        )
    distribution_example = aux.get("distribution_example", {})
    if distribution_example:
        sections.append("<h4>Distribution Claim Example</h4>")
        sections.append(
            "<p>"
            f"groups=({html.escape(str(distribution_example.get('observed_group')))} vs "
            f"{html.escape(str(distribution_example.get('reference_group')))}), "
            f"epsilon={distribution_example.get('epsilon')}"
            "</p>"
        )
        sections.append(
            "<p>"
            f"primary {distribution_example.get('primary_distance')}={distribution_example.get('primary_value')} "
            f"(holds={distribution_example.get('primary_holds')}), "
            f"sanity {distribution_example.get('sanity_distance')}={distribution_example.get('sanity_value')} "
            f"(holds={distribution_example.get('sanity_holds')}), "
            f"agree={distribution_example.get('distances_agree')}"
            "</p>"
        )
    return "".join(sections) if sections else "<p>No auxiliary decision/distribution examples.</p>"


def _render_naive_summary(comparative_rows: list[dict[str, Any]]) -> str:
    counts = {"naive_overclaim": 0, "naive_underclaim": 0, "agree": 0, "naive_uninformative": 0}
    for row in comparative_rows:
        naive = row.get("naive_baseline")
        if isinstance(naive, dict):
            label = str(naive.get("comparison", "naive_uninformative"))
            if label in counts:
                counts[label] += 1
    header = "<tr><th>category</th><th>count</th></tr>"
    body = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in counts.items())
    return f"<table>{header}{body}</table>"


def _render_rq_summary(rq: dict[str, Any]) -> str:
    if not rq:
        return "<p>No RQ summary available.</p>"
    out = []
    rq1 = rq.get("rq1_prevalence", {})
    out.append(f"<p><b>RQ1 prevalence:</b> {html.escape(str(rq1.get('by_space_and_claim_type', {})))}</p>")
    rq2 = rq.get("rq2_drivers", {})
    metric_label = rq2.get("metric_label")
    metric_note = rq2.get("metric_note")
    if metric_label:
        out.append(f"<p><b>RQ2 metric:</b> {html.escape(str(metric_label))}.</p>")
    if metric_note:
        out.append(f"<p><i>{html.escape(str(metric_note))}</i></p>")
    out.append(f"<p><b>RQ2 top drivers:</b> {html.escape(str(rq2.get('top_dimensions', [])))}</p>")
    rq3 = rq.get("rq3_cost_tradeoff", {})
    rows = rq3.get("stability_vs_cost_rows", [])
    out.append(f"<p><b>RQ3 cost rows:</b> {len(rows) if isinstance(rows, list) else 0}</p>")
    rq4 = rq.get("rq4_adaptive_sampling", {})
    out.append(
        f"<p><b>RQ4 adaptive runs:</b> {len(rq4.get('adaptive_sampling', [])) if isinstance(rq4, dict) else 0}</p>"
    )
    rq5 = rq.get("rq5_conditional_robustness", {})
    if isinstance(rq5, dict):
        out.append(f"<p><b>RQ5 robustness maps:</b> {rq5.get('experiments_with_map', 0)} experiments.</p>")
        out.append(f"<p><b>RQ5 minimal lockdown examples:</b> {len(rq5.get('minimal_lockdown_examples', []))}</p>")
    rq6 = rq.get("rq6_stratified_stability", {})
    if isinstance(rq6, dict):
        out.append(f"<p><b>RQ6 stratified runs:</b> {rq6.get('experiments_with_strata', 0)} experiments.</p>")
        out.append(
            "<p><b>RQ6 decision counts:</b> "
            f"{html.escape(str(rq6.get('decision_counts', {})))}</p>"
        )
    rq7 = rq.get("rq7_effect_diagnostics", {})
    if isinstance(rq7, dict):
        out.append(
            "<p><b>RQ7 effect diagnostics:</b> "
            f"{rq7.get('experiments_with_effect_diagnostics', 0)} experiments.</p>"
        )
        out.append(f"<p><b>RQ7 top interactions:</b> {len(rq7.get('top_interactions', []))}</p>")
    return "".join(out)


def _render_evidence_chain(
    *,
    meta: dict[str, Any],
    experiments: list[dict[str, Any]],
) -> str:
    artifacts = meta.get("artifacts", {})
    evidence_meta = meta.get("evidence_chain", {})

    parts: list[str] = []
    if isinstance(artifacts, dict):
        rows = []
        for key in ("trace_jsonl", "events_jsonl", "cache_db", "replay_trace"):
            value = artifacts.get(key)
            if value:
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(key))}</td>"
                    f"<td><code>{html.escape(str(value))}</code></td>"
                    "</tr>"
                )
        if rows:
            parts.append("<h3>Artifact References</h3>")
            parts.append("<table><tr><th>artifact</th><th>path</th></tr>" + "".join(rows) + "</table>")

    if isinstance(evidence_meta, dict):
        protocol = evidence_meta.get("protocol")
        schema_id = evidence_meta.get("schema_id")
        required_fields = evidence_meta.get("required_evidence_fields")
        if protocol:
            parts.append(f"<p><b>CEP protocol:</b> {html.escape(str(protocol))}</p>")
        if schema_id:
            parts.append(f"<p><b>CEP schema:</b> <code>{html.escape(str(schema_id))}</code></p>")
        if isinstance(required_fields, list) and required_fields:
            parts.append(
                "<p><b>Required evidence fields:</b> "
                f"{html.escape(', '.join(str(x) for x in required_fields))}</p>"
            )
        lookup_fields = evidence_meta.get("lookup_fields")
        if isinstance(lookup_fields, list) and lookup_fields:
            parts.append(
                "<p><b>Trace lookup fields:</b> "
                f"{html.escape(', '.join(str(x) for x in lookup_fields))}</p>"
            )
        provenance = evidence_meta.get("decision_provenance")
        if provenance:
            parts.append(f"<p><b>Decision provenance:</b> {html.escape(str(provenance))}</p>")

    exp_rows: list[str] = []
    for exp in experiments:
        evidence = exp.get("evidence")
        if not isinstance(evidence, dict):
            continue
        trace_query = evidence.get("trace_query", {})
        cep_hash = ""
        cep = evidence.get("cep")
        if isinstance(cep, dict):
            cf = cep.get("config_fingerprint")
            if isinstance(cf, dict):
                cep_hash = str(cf.get("hash", ""))
        cep_short = cep_hash[:12] if cep_hash else ""
        exp_rows.append(
            "<tr>"
            f"<td>{html.escape(str(exp.get('experiment_id')))}</td>"
            f"<td><code>{html.escape(str(trace_query))}</code></td>"
            f"<td><code>{html.escape(cep_short)}</code></td>"
            "</tr>"
        )
    if exp_rows:
        parts.append("<h3>Experiment-to-Trace Queries</h3>")
        parts.append(
            "<table><tr><th>experiment_id</th><th>trace_query</th><th>config_fingerprint(hash)</th></tr>"
            + "".join(exp_rows)
            + "</table>"
        )

    if not parts:
        return "<p>No explicit evidence-chain references found in this artifact.</p>"
    return "".join(parts)


def _executive_summary(experiments: list[dict[str, Any]], comparative_rows: list[dict[str, Any]]) -> list[str]:
    if not experiments:
        return ["No experiments available."]
    worst = None
    if comparative_rows:
        worst = max(comparative_rows, key=lambda r: float(r.get("flip_rate_mean", 0.0)))
    most_stable = None
    if comparative_rows:
        most_stable = max(comparative_rows, key=lambda r: float(r.get("stability_hat", 0.0)))

    bullets = [
        f"Evaluated {len(experiments)} claim experiments with conservative CI-based decisions.",
    ]
    if worst:
        bullets.append(
            "Worst observed instability: "
            f"{worst.get('space_preset')} / {worst.get('claim_pair')} / delta={worst.get('delta')} "
            f"with flip_rate_mean={worst.get('flip_rate_mean')}."
        )
    if most_stable:
        bullets.append(
            "Best aggregated stability: "
            f"{most_stable.get('space_preset')} / {most_stable.get('claim_pair')} / delta={most_stable.get('delta')} "
            f"with stability_hat={most_stable.get('stability_hat')}."
        )
    return bullets


def _plot_delta_curve(delta_rows: list[dict[str, Any]], out_path: Path) -> None:
    import numpy as np
    import matplotlib.pyplot as plt

    ordered = sorted(delta_rows, key=lambda r: float(r.get("delta", 0.0)))
    xs = [float(r["delta"]) for r in ordered]
    ys = [float(r["flip_rate_mean"]) for r in ordered]
    ymin = [float(r.get("flip_rate_min", y)) for r, y in zip(ordered, ys)]
    ymax = [float(r.get("flip_rate_max", y)) for r, y in zip(ordered, ys)]

    with plt.rc_context(_report_plot_rc()):
        fig, ax = plt.subplots(figsize=(7.1, 4.25))
        ax.plot(xs, ys, marker="o", markersize=6.8, color="#2f5f89", linewidth=2.2, label="mean flip rate")
        band = ax.fill_between(xs, ymin, ymax, color="#7aa6c2", alpha=0.24)
        band.set_hatch("////")
        band.set_edgecolor("#4e718f")
        band.set_linewidth(0.0)
        ax.set_xlabel("delta", fontweight="semibold")
        ax.set_ylabel("mean flip rate", fontweight="semibold")
        ax.set_title("Delta Sweep: Ranking Flip Rate")
        y_min_data = float(np.nanmin(ymin))
        y_max_data = float(np.nanmax(ymax))
        y_span = y_max_data - y_min_data
        if y_span < 1e-6:
            pad = 0.03
        else:
            pad = max(0.02, 0.18 * y_span)
        lo = max(0.0, y_min_data - pad)
        hi = min(1.0, y_max_data + pad)
        if hi - lo < 0.08:
            hi = min(1.0, lo + 0.08)
        ax.set_ylim(lo, hi)
        if len(xs) == 1:
            ax.set_xlim(xs[0] - 0.02, xs[0] + 0.02)
        else:
            xspan = max(xs) - min(xs)
            xpad = max(0.002, 0.06 * xspan)
            ax.set_xlim(min(xs) - xpad, max(xs) + xpad)
        ax.legend(loc="upper left")

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320, bbox_inches="tight")
        plt.close(fig)


def _plot_shots_curve(shots_rows: list[dict[str, Any]], out_path: Path, *, threshold: float = 0.95) -> bool:
    if not shots_rows:
        return False
    import numpy as np
    import matplotlib.pyplot as plt

    bucket: dict[int, list[dict[str, Any]]] = {}
    for row in shots_rows:
        shot = int(row.get("shots", 0))
        bucket.setdefault(shot, []).append(row)

    ordered: list[dict[str, Any]] = []
    decision_order = {"stable": 3, "inconclusive": 2, "unstable": 1}
    for shot in sorted(bucket.keys()):
        rows = bucket[shot]
        n = len(rows)
        mean_hat = sum(float(r.get("stability_hat", 0.0)) for r in rows) / n
        mean_low = sum(float(r.get("stability_ci_low", 0.0)) for r in rows) / n
        mean_high = sum(float(r.get("stability_ci_high", 0.0)) for r in rows) / n
        mean_eval = int(round(sum(float(r.get("n_eval", 0.0)) for r in rows) / n))
        labels = [str(r.get("decision", "inconclusive")) for r in rows]
        labels.sort(key=lambda x: decision_order.get(x, 0), reverse=True)
        ordered.append(
            {
                "shots": shot,
                "stability_hat": mean_hat,
                "stability_ci_low": mean_low,
                "stability_ci_high": mean_high,
                "n_eval": mean_eval,
                "decision": labels[0] if labels else "inconclusive",
            }
        )

    xs = [int(r["shots"]) for r in ordered]
    ys = [float(r["stability_hat"]) for r in ordered]
    lows = [float(r["stability_ci_low"]) for r in ordered]
    highs = [float(r["stability_ci_high"]) for r in ordered]
    decisions = [str(r.get("decision", "inconclusive")) for r in ordered]
    eval_counts = [int(r.get("n_eval", 0)) for r in ordered]

    with plt.rc_context(_report_plot_rc()):
        fig, ax = plt.subplots(figsize=(7.1, 4.25))
        band = ax.fill_between(xs, lows, highs, color="#8ab6d6", alpha=0.24)
        band.set_hatch("\\\\\\\\")
        band.set_edgecolor("#4b7090")
        band.set_linewidth(0.0)
        ax.plot(
            xs,
            lows,
            color="#204d74",
            linewidth=2.35,
            linestyle="-",
            marker="o",
            markersize=6.8,
            markerfacecolor="#204d74",
            markeredgecolor="#2f2f2f",
            markeredgewidth=0.35,
            label="CI lower bound",
        )
        ax.plot(
            xs,
            ys,
            color="#5f84a6",
            linewidth=1.4,
            linestyle=(0, (2, 2)),
            marker="o",
            markersize=4.6,
            markerfacecolor="#5f84a6",
            markeredgecolor="#415869",
            markeredgewidth=0.3,
            alpha=0.75,
            label="stability_hat",
        )
        yerr_low = [max(0.0, y - lo) for y, lo in zip(ys, lows)]
        yerr_high = [max(0.0, hi - y) for y, hi in zip(ys, highs)]
        ax.errorbar(xs, ys, yerr=[yerr_low, yerr_high], fmt="none", ecolor="#6688a3", elinewidth=1.0, alpha=0.7, capsize=3)

        ax.axhline(threshold, color="#6b6b6b", linewidth=1.2, linestyle=(0, (4, 3)), label="stability threshold")
        ax.set_xlabel("shots", fontweight="semibold")
        ax.set_ylabel("stability (CI)", fontweight="semibold")
        ax.set_title("Stability vs Cost (Shots)")
        ax.set_xscale("log", base=2)
        lo = max(0.0, float(np.nanmin(lows)) - 0.04)
        hi = min(1.0, float(np.nanmax(highs)) + 0.03)
        if hi - lo < 0.12:
            lo = max(0.0, hi - 0.12)
        ax.set_ylim(lo, hi)
        ax.set_xticks(xs)
        ax.set_xticklabels([str(x) for x in xs])
        if len(xs) == 1:
            x = xs[0]
            pad = max(1.0, 0.06 * x)
            ax.set_xlim(x - pad, x + pad)

        y_annot_top = ax.get_ylim()[1]
        for x, low, decision, n_eval in zip(xs, lows, decisions, eval_counts):
            y = min(y_annot_top - 0.01, low + 0.012)
            ax.text(
                x,
                y,
                f"{decision}, n={n_eval}",
                fontsize=7.3,
                color="#2f2f2f",
                ha="center",
                va="bottom",
            )
        ax.legend(loc="lower right")
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320, bbox_inches="tight")
        plt.close(fig)
    return True


def _plot_factor_attribution(
    per_graph: dict[str, Any],
    *,
    selected_delta: str,
    out_path: Path,
) -> bool:
    import matplotlib.pyplot as plt

    if not per_graph:
        return False
    graph_id, graph_payload = next(iter(per_graph.items()))
    attrib = graph_payload.get("factor_attribution", {}).get(selected_delta)
    if not attrib:
        return False

    dim_payload = attrib.get("by_dimension", {})
    dimensions = list(dim_payload.keys())
    if not dimensions:
        return False

    with plt.rc_context(_report_plot_rc()):
        fig, axes = plt.subplots(len(dimensions), 1, figsize=(7.8, 2.9 * len(dimensions)))
        if len(dimensions) == 1:
            axes = [axes]

        stem_color = "#2f6690"
        marker_style = "o"

        for ax, dim in zip(axes, dimensions):
            values = dim_payload.get(dim, {})
            labels = sorted(list(values.keys()), key=_numeric_sort_key)
            rates = [float(values[label].get("flip_rate", 0.0)) for label in labels]
            x = list(range(len(labels)))
            # Uniform lollipop/stem style for readability (single metric, no category encoding).
            for i, (xi, rate) in enumerate(zip(x, rates)):
                ax.vlines(
                    xi,
                    0.0,
                    rate,
                    color=stem_color,
                    linewidth=2.4,
                    linestyles=(0, (4, 2)),
                    alpha=0.95,
                )
                ax.scatter(
                    [xi],
                    [rate],
                    s=80,
                    marker=marker_style,
                    facecolor=stem_color,
                    edgecolor="#2f2f2f",
                    linewidth=0.45,
                    zorder=4,
                )
                ax.text(xi, rate + 0.01, f"{rate:.2f}", ha="center", va="bottom", fontsize=7.8, color="#2f2f2f")
            max_rate = max(rates) if rates else 0.0
            upper = 0.12 if max_rate == 0.0 else min(1.0, max(0.12, max_rate + 0.1))
            ax.set_ylim(0.0, upper)
            ax.set_xticks(x)
            ax.set_xticklabels([str(v) for v in labels])
            ax.set_ylabel("flip rate", fontweight="semibold")
            ax.set_title(f"{graph_id}: {dim} (delta={selected_delta})", fontsize=11.2)

        axes[-1].set_xlabel("dimension value", fontweight="semibold")
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=320, bbox_inches="tight")
        plt.close(fig)
    return True


def _legacy_to_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    sampling = payload.get("sampling", {})
    return {
        "experiment_id": "legacy:single",
        "claim": payload.get("claim", {}),
        "baseline": payload.get("baseline", {}),
        "stability_rule": payload.get("stability_rule", {}),
        "sampling": sampling,
        "backend": {
            "engine": payload.get("backend_engine"),
            "spot_check_noise": False,
            "one_qubit_error": None,
            "two_qubit_error": None,
        },
        "per_graph": payload.get("per_graph", {}),
        "overall": payload.get("overall", {}),
    }


def _relative_ref(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    selected_sections = parse_sections_arg(args.sections)

    json_path = Path(args.json)
    out_path = Path(args.out) if args.out else (json_path.parent / "stability_report.html")
    assets_dir = Path(args.assets_dir) if args.assets_dir else (json_path.parent / "report_assets")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    experiments = payload.get("experiments", [])
    if not experiments:
        experiments = [_legacy_to_experiment(payload)]

    comparative_rows = payload.get("comparative", {}).get("space_claim_delta", [])
    device_rows = payload.get("device_summary", [])
    summary_bullets = _executive_summary(experiments, comparative_rows)

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
        html_body.append(_render_evidence_chain(meta=meta_obj, experiments=experiments))

    if device_rows and is_section_enabled("device_summary", selected_sections):
        html_body.append("<h2>Per-Device Summary</h2>")
        html_body.append(_render_device_summary_table(device_rows))

    if comparative_rows and is_section_enabled("claim_table", selected_sections):
        html_body.append("<h2>Claim Summary Table (Space x Claim x Delta)</h2>")
        html_body.append(_render_comparative_table(comparative_rows))
    if comparative_rows and is_section_enabled("naive_comparison", selected_sections):
        html_body.append("<h2>Naive Baseline vs ClaimStab</h2>")
        html_body.append(_render_naive_summary(comparative_rows))

    rq_summary = payload.get("rq_summary", {})
    if isinstance(rq_summary, dict) and rq_summary and is_section_enabled("rq_summary", selected_sections):
        html_body.append("<h2>RQ Summary (RQ1-RQ7)</h2>")
        html_body.append(_render_rq_summary(rq_summary))

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
            html_body.append(_render_delta_table(delta_rows))

        delta_plot_ok = False
        factor_plot_ok = False
        shots_plot_ok = False
        delta_plot = assets_dir / f"delta_sweep_{idx + 1}.png"
        factor_plot = assets_dir / f"factor_attribution_{idx + 1}.png"
        shots_plot = assets_dir / f"shots_stability_{idx + 1}.png"

        if claim_type == "ranking" and delta_rows and args.with_plots and is_section_enabled("delta_sweep", selected_sections):
            try:
                _plot_delta_curve(delta_rows, delta_plot)
                delta_plot_ok = True
            except Exception as exc:
                print(f"[WARN] Could not render delta plot for experiment {idx + 1}: {exc}")

        selected_delta = str(delta_rows[0].get("delta")) if delta_rows else "0.0"
        if claim_type == "ranking" and args.with_plots and is_section_enabled("delta_sweep", selected_sections):
            try:
                factor_plot_ok = _plot_factor_attribution(
                    per_graph,
                    selected_delta=selected_delta,
                    out_path=factor_plot,
                )
            except Exception as exc:
                print(f"[WARN] Could not render factor plot for experiment {idx + 1}: {exc}")
                factor_plot_ok = False

        if claim_type == "ranking" and delta_plot_ok and is_section_enabled("delta_sweep", selected_sections):
            delta_ref = _relative_ref(delta_plot, out_path.parent)
            html_body.append("<h3>Delta Curve</h3>")
            html_body.append(f"<img src='{html.escape(delta_ref)}' width='700' />")

        if claim_type == "ranking" and factor_plot_ok and is_section_enabled("delta_sweep", selected_sections):
            factor_ref = _relative_ref(factor_plot, out_path.parent)
            html_body.append("<h3>Example Graph Factor Attribution</h3>")
            html_body.append(f"<img src='{html.escape(factor_ref)}' width='760' />")

        stability_vs_cost = overall.get("stability_vs_cost", {})
        shots_rows_delta0 = stability_vs_cost.get("by_delta", {}).get(str(delta_rows[0].get("delta")) if delta_rows else "0.0", [])
        threshold = float(rule.get("threshold", 0.95)) if isinstance(rule, dict) else 0.95
        if args.with_plots and is_section_enabled("cost_curve", selected_sections):
            try:
                shots_plot_ok = _plot_shots_curve(shots_rows_delta0, shots_plot, threshold=threshold)
            except Exception as exc:
                print(f"[WARN] Could not render shots curve for experiment {idx + 1}: {exc}")
                shots_plot_ok = False

        if is_section_enabled("cost_curve", selected_sections):
            html_body.append("<h3>Stability vs Cost (Shots)</h3>")
            for delta in [str(r.get("delta")) for r in delta_rows if r.get("delta") is not None]:
                rows_for_delta = stability_vs_cost.get("by_delta", {}).get(delta, [])
                html_body.append(f"<h4>delta={html.escape(delta)}</h4>")
                html_body.append(_render_shots_curve_table(rows_for_delta))
                min_shots = stability_vs_cost.get("minimum_shots_for_stable", {}).get(delta)
                min_shots_text = str(min_shots) if min_shots is not None else "None within evaluated shot levels"
                html_body.append(f"<p><b>minimum_shots_for_stable:</b> {html.escape(min_shots_text)}</p>")
                warn = _shots_warning(rows_for_delta)
                if warn:
                    html_body.append(f"<p><b>Warning:</b> {html.escape(warn)}</p>")
                html_body.append(f"<p><i>{html.escape(_shots_diagnostic_text(rows_for_delta, threshold))}</i></p>")
            if shots_plot_ok:
                shots_ref = _relative_ref(shots_plot, out_path.parent)
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
                html_body.append(_render_top_unstable(top_by_delta.get(delta, [])))
                html_body.append("<h5>Aggregated Factor Attribution</h5>")
                html_body.append(_render_dimension_breakdown(dim_by_delta.get(delta, {})))
                html_body.append("<h5>Top Lock-Down Drivers (Fix knob to improve stability)</h5>")
                html_body.append(_render_lockdown_recommendations(lockdown_by_delta.get(delta, [])))

        if claim_type == "ranking" and is_section_enabled("robustness_map", selected_sections):
            html_body.append("<h3>Conditional Robustness Map (RQ5-RQ7)</h3>")
            html_body.append(
                _render_conditional_robustness(
                    overall.get("conditional_robustness", {}),
                    delta_rows=delta_rows,
                )
            )
            html_body.append("<h3>Stratified Stability</h3>")
            html_body.append(
                _render_stratified_stability(
                    overall.get("stratified_stability", {}),
                    delta_rows=delta_rows,
                )
            )
            html_body.append("<h3>Main + Interaction Effects</h3>")
            html_body.append(
                _render_effect_diagnostics(
                    overall.get("effect_diagnostics", {}),
                    delta_rows=delta_rows,
                )
            )

        if is_section_enabled("auxiliary_claims", selected_sections):
            html_body.append("<h3>Decision + Distribution Examples</h3>")
            html_body.append(_render_auxiliary_claims(aux))
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
    report_html = "".join(html_body)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_html, encoding="utf-8")

    print("Wrote:")
    print(" ", out_path.resolve())


if __name__ == "__main__":
    main()
