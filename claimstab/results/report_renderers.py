from __future__ import annotations

import html
from typing import Any

from claimstab.results.report_helpers import as_float, decision_badge, decision_count, numeric_sort_key


def render_delta_table(delta_rows: list[dict[str, Any]]) -> str:
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
            f"<td>{decision_badge(row.get('decision'))}</td>"
            f"<td>{row.get('clustered_stability_mean')}</td>"
            f"<td>{row.get('clustered_stability_ci_low')}</td>"
            f"<td>{row.get('clustered_stability_ci_high')}</td>"
            f"<td>{decision_badge(row.get('clustered_decision'))}</td>"
            f"<td>{row.get('n_instances')}</td>"
            f"<td>{row.get('n_claim_evals')}</td>"
            f"<td>{decision_count(row, 'stable')}</td>"
            f"<td>{decision_count(row, 'unstable')}</td>"
            f"<td>{decision_count(row, 'inconclusive')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(rows)}</table>"


def render_comparative_table(rows: list[dict[str, Any]]) -> str:
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
            f"<td>{decision_badge(row.get('decision'))}</td>"
            f"<td>{row.get('clustered_stability_mean')}</td>"
            f"<td>{row.get('clustered_stability_ci_low')}</td>"
            f"<td>{row.get('clustered_stability_ci_high')}</td>"
            f"<td>{decision_badge(row.get('clustered_decision'))}</td>"
            f"<td>{decision_count(row, 'stable')}</td>"
            f"<td>{decision_count(row, 'unstable')}</td>"
            f"<td>{decision_count(row, 'inconclusive')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def render_device_summary_table(rows: list[dict[str, Any]]) -> str:
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
            f"<td>{decision_badge(row.get('decision'))}</td>"
            f"<td>{decision_count(row, 'stable')}</td>"
            f"<td>{decision_count(row, 'unstable')}</td>"
            f"<td>{decision_count(row, 'inconclusive')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def render_top_unstable(top_events: list[dict[str, Any]]) -> str:
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


def render_dimension_breakdown(by_dim: dict[str, dict[str, dict[str, Any]]]) -> str:
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


def render_lockdown_recommendations(rows: list[dict[str, Any]]) -> str:
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


def render_conditional_robustness(
    robustness: dict[str, Any],
    *,
    delta_rows: list[dict[str, Any]],
) -> str:
    if not isinstance(robustness, dict) or not robustness:
        return "<p>No conditional robustness map available.</p>"

    robust_core = robustness.get("robust_core_by_delta", {})
    failure_frontier = robustness.get("failure_frontier_by_delta", {})
    lockdown = robustness.get("minimal_lockdown_set_by_delta", {})
    exact_mos = robustness.get("exact_mos_by_delta", {})
    cells = robustness.get("cells_by_delta", {})

    deltas = [str(r.get("delta")) for r in delta_rows if r.get("delta") is not None]
    if not deltas:
        keys = set()
        if isinstance(robust_core, dict):
            keys.update(str(k) for k in robust_core.keys())
        if isinstance(failure_frontier, dict):
            keys.update(str(k) for k in failure_frontier.keys())
        deltas = sorted(keys, key=numeric_sort_key)

    out: list[str] = []
    for delta in deltas:
        core_rows = robust_core.get(delta, []) if isinstance(robust_core, dict) else []
        frontier_rows = failure_frontier.get(delta, []) if isinstance(failure_frontier, dict) else []
        lock_payload = lockdown.get(delta, {}) if isinstance(lockdown, dict) else {}
        lock_best = lock_payload.get("best", {}) if isinstance(lock_payload, dict) else {}
        exact_payload = exact_mos.get(delta, {}) if isinstance(exact_mos, dict) else {}
        exact_best = exact_payload.get("best", {}) if isinstance(exact_payload, dict) else {}
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
        if isinstance(exact_best, dict) and exact_best:
            out.append(
                "<p><b>Exact MOS:</b> "
                f"lock_dimensions={html.escape(str(exact_best.get('lock_dimensions', [])))}, "
                f"conditions={html.escape(str(exact_best.get('conditions', {})))}, "
                f"decision={html.escape(str(exact_best.get('decision')))}</p>"
            )

    return "".join(out) if out else "<p>No conditional robustness map available.</p>"


def render_stratified_stability(
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
        deltas = sorted([str(k) for k in by_delta.keys()], key=numeric_sort_key)

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
                f"<td>{decision_badge(row.get('decision'))}</td>"
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


def render_effect_diagnostics(
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
        deltas = sorted([str(k) for k in by_delta.keys()], key=numeric_sort_key)

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


def render_shots_curve_table(rows: list[dict[str, Any]]) -> str:
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
            f"<td>{decision_badge(row.get('decision'))}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


def render_auxiliary_claims(aux: dict[str, Any]) -> str:
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


def render_naive_summary(comparative_rows: list[dict[str, Any]]) -> str:
    def _count(field_name: str) -> dict[str, int]:
        counts = {"naive_overclaim": 0, "naive_underclaim": 0, "agree": 0, "naive_uninformative": 0}
        for row in comparative_rows:
            naive = row.get(field_name)
            if not isinstance(naive, dict):
                continue
            label = str(naive.get("comparison", "naive_uninformative"))
            if label in counts:
                counts[label] += 1
        return counts

    def _render_table(title: str, counts: dict[str, int]) -> str:
        header = "<tr><th>category</th><th>count</th></tr>"
        body = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in counts.items())
        return f"<h4>{html.escape(title)}</h4><table>{header}{body}</table>"

    legacy_counts = _count("naive_baseline")
    realistic_counts = _count("naive_baseline_realistic")
    has_realistic = any(v > 0 for v in realistic_counts.values())
    out = [_render_table("Legacy Baseline (strict)", legacy_counts)]
    if has_realistic:
        out.append(_render_table("Realistic Default Baseline", realistic_counts))
    return "".join(out)


def render_rq_summary(rq: dict[str, Any]) -> str:
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
        out.append("<p><b>RQ6 decision counts:</b> " f"{html.escape(str(rq6.get('decision_counts', {})))}</p>")
    rq7 = rq.get("rq7_effect_diagnostics", {})
    if isinstance(rq7, dict):
        out.append(
            "<p><b>RQ7 effect diagnostics:</b> "
            f"{rq7.get('experiments_with_effect_diagnostics', 0)} experiments.</p>"
        )
        out.append(f"<p><b>RQ7 top interactions:</b> {len(rq7.get('top_interactions', []))}</p>")
    return "".join(out)


def render_evidence_chain(
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
                "<p><b>Trace lookup fields:</b> " f"{html.escape(', '.join(str(x) for x in lookup_fields))}</p>"
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
