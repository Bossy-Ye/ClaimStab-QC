from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from claimstab.figures.style import SERIF_FALLBACK


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def numeric_sort_key(value: Any) -> tuple[int, float | str]:
    text = str(value)
    try:
        return (0, float(text))
    except Exception:
        return (1, text)


def report_plot_rc() -> dict[str, Any]:
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


def decision_badge(value: Any) -> str:
    label = str(value)
    css = "neutral"
    if label == "stable":
        css = "stable"
    elif label == "unstable":
        css = "unstable"
    elif label == "inconclusive":
        css = "inconclusive"
    return f"<span class='badge {css}'>{html.escape(label)}</span>"


def decision_count(row: dict[str, Any], label: str) -> int:
    counts = row.get("decision_counts")
    if isinstance(counts, dict):
        return int(counts.get(label, 0))
    fallback_key = f"{label}_count"
    return int(row.get(fallback_key, 0))


def shots_warning(rows: list[dict[str, Any]]) -> str | None:
    if len(rows) == 1:
        return "Only one shots value available; cannot infer trend. Add more shots levels to estimate minimum required shots."
    return None


def shots_diagnostic_text(rows: list[dict[str, Any]], threshold: float) -> str:
    if not rows:
        return "No shots-by-stability data available."
    widths = [as_float(row.get("stability_ci_high"), 0.0) - as_float(row.get("stability_ci_low"), 0.0) for row in rows]
    max_width = max(widths) if widths else 0.0
    any_stable = any(str(row.get("decision")) == "stable" for row in rows)
    if not any_stable:
        best = max(rows, key=lambda r: as_float(r.get("stability_ci_low"), 0.0))
        if max_width > 0.05:
            return (
                "CI is wide in this shots sweep (>0.05): increase n_eval (more perturbation samples or more instances) "
                "before concluding stability cannot be reached."
            )
        if as_float(best.get("stability_hat"), 0.0) < threshold:
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


def executive_summary(experiments: list[dict[str, Any]], comparative_rows: list[dict[str, Any]]) -> list[str]:
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


def legacy_to_experiment(payload: dict[str, Any]) -> dict[str, Any]:
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


def relative_ref(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
