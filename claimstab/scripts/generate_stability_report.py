from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


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
            f"<td>{row.get('decision')}</td>"
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
            f"<td>{row.get('decision')}</td>"
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
            f"<td>{row.get('decision')}</td>"
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
            f"<td>{row.get('decision')}</td>"
            "</tr>"
        )
    return f"<table>{header}{''.join(body)}</table>"


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
    import matplotlib.pyplot as plt

    xs = [float(r["delta"]) for r in delta_rows]
    ys = [float(r["flip_rate_mean"]) for r in delta_rows]

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.plot(xs, ys, marker="o")
    ax.set_xlabel("delta")
    ax.set_ylabel("mean flip rate")
    ax.set_title("Delta sweep: ranking flip rate")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_shots_curve(shots_rows: list[dict[str, Any]], out_path: Path) -> bool:
    if not shots_rows:
        return False
    import matplotlib.pyplot as plt

    xs = [int(r["shots"]) for r in shots_rows]
    ys = [float(r["stability_hat"]) for r in shots_rows]
    lows = [float(r["stability_ci_low"]) for r in shots_rows]
    highs = [float(r["stability_ci_high"]) for r in shots_rows]
    yerr_low = [y - lo for y, lo in zip(ys, lows)]
    yerr_high = [hi - y for y, hi in zip(ys, highs)]

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.errorbar(xs, ys, yerr=[yerr_low, yerr_high], marker="o", capsize=3)
    ax.set_xlabel("shots")
    ax.set_ylabel("stability")
    ax.set_title("Stability vs Cost (shots)")
    ax.set_ylim(0.0, 1.0)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
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

    fig, axes = plt.subplots(len(dimensions), 1, figsize=(7.0, 2.6 * len(dimensions)))
    if len(dimensions) == 1:
        axes = [axes]

    for ax, dim in zip(axes, dimensions):
        values = dim_payload.get(dim, {})
        labels = list(values.keys())
        rates = [float(values[label].get("flip_rate", 0.0)) for label in labels]
        ax.bar(labels, rates)
        ax.set_ylim(0.0, 1.0)
        ax.set_ylabel("flip rate")
        ax.set_title(f"{graph_id}: {dim} (delta={selected_delta})")

    axes[-1].set_xlabel("dimension value")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
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
        "<style>body{font-family:Arial,sans-serif;margin:24px;}table{border-collapse:collapse;margin-bottom:14px;}th,td{border:1px solid #999;padding:6px 10px;}h1,h2,h3,h4{margin-bottom:8px;}code{background:#f3f3f3;padding:2px 4px;}p{margin:4px 0 10px 0;}</style>",
        "</head><body>",
        "<h1>Claim Stability Report</h1>",
    ]

    if payload.get("meta"):
        html_body.append(f"<p><b>Meta:</b> {html.escape(str(payload['meta']))}</p>")
    if payload.get("batch"):
        html_body.append(f"<p><b>Batch:</b> {html.escape(str(payload['batch']))}</p>")
    html_body.append("<h2>Executive Summary</h2>")
    html_body.append("<ul>" + "".join(f"<li>{html.escape(b)}</li>" for b in summary_bullets[:3]) + "</ul>")

    if device_rows:
        html_body.append("<h2>Per-Device Summary</h2>")
        html_body.append(_render_device_summary_table(device_rows))

    if comparative_rows:
        html_body.append("<h2>Claim Summary Table (Space x Claim x Delta)</h2>")
        html_body.append(_render_comparative_table(comparative_rows))

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
        html_body.append(f"<p><b>Claim:</b> {html.escape(str(claim))}</p>")
        html_body.append(f"<p><b>Sampling:</b> {html.escape(str(sampling))}</p>")
        html_body.append(f"<p><b>Decision rule:</b> {html.escape(str(rule))}</p>")
        html_body.append(f"<p><b>Backend:</b> {html.escape(str(backend))}</p>")
        html_body.append("<p><i>Interpretation note:</i> delta is a practical significance threshold, not a stability tuning knob. Read flip/stability together with holds rate.</p>")
        html_body.append("<h3>Delta Sweep Summary</h3>")
        html_body.append(_render_delta_table(delta_rows))

        delta_plot_ok = False
        factor_plot_ok = False
        shots_plot_ok = False
        delta_plot = assets_dir / f"delta_sweep_{idx + 1}.png"
        factor_plot = assets_dir / f"factor_attribution_{idx + 1}.png"
        shots_plot = assets_dir / f"shots_stability_{idx + 1}.png"

        if delta_rows and args.with_plots:
            try:
                _plot_delta_curve(delta_rows, delta_plot)
                delta_plot_ok = True
            except Exception as exc:
                print(f"[WARN] Could not render delta plot for experiment {idx + 1}: {exc}")

        selected_delta = str(delta_rows[0].get("delta")) if delta_rows else "0.0"
        if args.with_plots:
            try:
                factor_plot_ok = _plot_factor_attribution(
                    per_graph,
                    selected_delta=selected_delta,
                    out_path=factor_plot,
                )
            except Exception as exc:
                print(f"[WARN] Could not render factor plot for experiment {idx + 1}: {exc}")
                factor_plot_ok = False

        if delta_plot_ok:
            delta_ref = _relative_ref(delta_plot, out_path.parent)
            html_body.append("<h3>Delta Curve</h3>")
            html_body.append(f"<img src='{html.escape(delta_ref)}' width='700' />")

        if factor_plot_ok:
            factor_ref = _relative_ref(factor_plot, out_path.parent)
            html_body.append("<h3>Example Graph Factor Attribution</h3>")
            html_body.append(f"<img src='{html.escape(factor_ref)}' width='760' />")

        stability_vs_cost = overall.get("stability_vs_cost", {})
        shots_rows_delta0 = stability_vs_cost.get("by_delta", {}).get(str(delta_rows[0].get("delta")) if delta_rows else "0.0", [])
        if args.with_plots:
            try:
                shots_plot_ok = _plot_shots_curve(shots_rows_delta0, shots_plot)
            except Exception as exc:
                print(f"[WARN] Could not render shots curve for experiment {idx + 1}: {exc}")
                shots_plot_ok = False

        html_body.append("<h3>Stability vs Cost (Shots)</h3>")
        for delta in [str(r.get("delta")) for r in delta_rows]:
            html_body.append(f"<h4>delta={html.escape(delta)}</h4>")
            html_body.append(_render_shots_curve_table(stability_vs_cost.get("by_delta", {}).get(delta, [])))
            min_shots = stability_vs_cost.get("minimum_shots_for_stable", {}).get(delta)
            html_body.append(f"<p><b>minimum_shots_for_stable:</b> {html.escape(str(min_shots))}</p>")
        if shots_plot_ok:
            shots_ref = _relative_ref(shots_plot, out_path.parent)
            html_body.append(f"<img src='{html.escape(shots_ref)}' width='700' />")

        diagnostics = overall.get("diagnostics", {})
        dim_by_delta = diagnostics.get("by_delta_dimension", {})
        top_by_delta = diagnostics.get("top_unstable_configs_by_delta", {})
        lockdown_by_delta = diagnostics.get("top_lockdown_recommendations_by_delta", {})
        if dim_by_delta or top_by_delta:
            html_body.append("<h3>Failure Mode Diagnostics</h3>")
            for delta in [str(r.get("delta")) for r in delta_rows]:
                html_body.append(f"<h4>delta={html.escape(delta)}</h4>")
                html_body.append("<h5>Top Unstable Configurations</h5>")
                html_body.append(_render_top_unstable(top_by_delta.get(delta, [])))
                html_body.append("<h5>Aggregated Factor Attribution</h5>")
                html_body.append(_render_dimension_breakdown(dim_by_delta.get(delta, {})))
                html_body.append("<h5>Top Lock-Down Drivers (Fix knob to improve stability)</h5>")
                html_body.append(_render_lockdown_recommendations(lockdown_by_delta.get(delta, [])))

        html_body.append("<h3>Decision + Distribution Examples</h3>")
        html_body.append(_render_auxiliary_claims(aux))

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
