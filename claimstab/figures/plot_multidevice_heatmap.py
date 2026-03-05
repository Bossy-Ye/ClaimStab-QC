from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, save_fig


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Input JSON must be an object: {path}")
    return payload


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("device_summary")
    if not isinstance(rows, list):
        rows = payload.get("comparative", {}).get("space_claim_delta", [])
    if not isinstance(rows, list):
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def _pick_claim_pair(rows: list[dict[str, Any]], claim_pair: str | None) -> str | None:
    if claim_pair:
        return claim_pair
    tokens = [str(row.get("claim_pair")) for row in rows if row.get("claim_pair")]
    if not tokens:
        return None
    return Counter(tokens).most_common(1)[0][0]


def _pick_delta(rows: list[dict[str, Any]], delta: float | None) -> float | None:
    if delta is not None:
        return float(delta)
    options = sorted({_as_float(row.get("delta")) for row in rows})
    if not options:
        return None
    return options[0]


def _aggregate_matrix(
    rows: list[dict[str, Any]],
    *,
    value_key: str,
) -> tuple[list[str], list[str], np.ndarray, dict[tuple[str, str], str]]:
    devices = sorted({str(row.get("device_name")) for row in rows if row.get("device_name") is not None})
    metrics = sorted({str(row.get("metric_name")) for row in rows if row.get("metric_name") is not None})
    matrix = np.full((len(devices), len(metrics)), np.nan, dtype=float)
    decisions: dict[tuple[str, str], str] = {}

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        device = str(row.get("device_name", ""))
        metric = str(row.get("metric_name", ""))
        if not device or not metric:
            continue
        grouped[(device, metric)].append(row)

    for i, device in enumerate(devices):
        for j, metric in enumerate(metrics):
            slot = grouped.get((device, metric), [])
            if not slot:
                continue
            values = [_as_float(row.get(value_key), float("nan")) for row in slot]
            values = [v for v in values if not np.isnan(v)]
            if not values:
                continue
            matrix[i, j] = float(sum(values) / len(values))
            decision_counts = Counter(str(row.get("decision", "inconclusive")) for row in slot)
            decisions[(device, metric)] = decision_counts.most_common(1)[0][0]
    return devices, metrics, matrix, decisions


def _plot_heatmap(
    *,
    devices: list[str],
    metrics: list[str],
    matrix: np.ndarray,
    decisions: dict[tuple[str, str], str],
    title: str,
    out_base: Path,
    annotate_decision: bool,
) -> dict[str, str] | None:
    if matrix.size == 0:
        return None

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu", vmin=0.0, vmax=1.0)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("value")
    ax.set_xticks(range(len(metrics)))
    ax.set_yticks(range(len(devices)))
    ax.set_xticklabels(metrics, rotation=25, ha="right")
    ax.set_yticklabels(devices)
    ax.set_xlabel("metric")
    ax.set_ylabel("device")
    ax.set_title(title)

    for i, device in enumerate(devices):
        for j, metric in enumerate(metrics):
            value = matrix[i, j]
            if np.isnan(value):
                continue
            txt = f"{value:.2f}"
            if annotate_decision:
                decision = decisions.get((device, metric), "inconclusive")
                txt = f"{value:.2f}\n{decision}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8.2, color="#1f1f1f")

    return save_fig(fig, out_base)


def plot_multidevice_heatmaps(
    payload: dict[str, Any],
    out_dir: Path,
    *,
    claim_pair: str | None = None,
    delta: float | None = None,
) -> dict[str, Any]:
    rows = _extract_rows(payload)
    pair = _pick_claim_pair(rows, claim_pair)
    if pair is not None:
        rows = [row for row in rows if str(row.get("claim_pair")) == pair]
    selected_delta = _pick_delta(rows, delta)
    if selected_delta is not None:
        rows = [row for row in rows if abs(_as_float(row.get("delta")) - float(selected_delta)) <= 1e-12]

    out_dir.mkdir(parents=True, exist_ok=True)
    devices, metrics, stability_matrix, decisions = _aggregate_matrix(rows, value_key="stability_hat")
    _, _, ci_low_matrix, _ = _aggregate_matrix(rows, value_key="stability_ci_low")

    title_suffix = f"claim_pair={pair or 'N/A'}, delta={selected_delta if selected_delta is not None else 'N/A'}"
    ref_stability = _plot_heatmap(
        devices=devices,
        metrics=metrics,
        matrix=stability_matrix,
        decisions=decisions,
        title=f"Multi-Device Stability Hat Heatmap ({title_suffix})",
        out_base=out_dir / "fig_multidevice_stability_hat_heatmap",
        annotate_decision=True,
    )
    ref_ci_low = _plot_heatmap(
        devices=devices,
        metrics=metrics,
        matrix=ci_low_matrix,
        decisions=decisions,
        title=f"Multi-Device CI Low Heatmap ({title_suffix})",
        out_base=out_dir / "fig_multidevice_ci_low_heatmap",
        annotate_decision=False,
    )
    return {
        "selected_claim_pair": pair,
        "selected_delta": selected_delta,
        "n_rows": len(rows),
        "stability_hat_heatmap": ref_stability,
        "ci_low_heatmap": ref_ci_low,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate multi-device paper heatmaps from multidevice summary JSON.")
    ap.add_argument("--input", required=True, help="Path to multidevice JSON (combined_summary.json or compatible).")
    ap.add_argument("--out", required=True, help="Output directory for heatmaps.")
    ap.add_argument("--claim-pair", default=None, help="Optional claim_pair selector.")
    ap.add_argument("--delta", type=float, default=None, help="Optional delta selector.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    payload = _load_json(Path(args.input))
    refs = plot_multidevice_heatmaps(
        payload,
        Path(args.out),
        claim_pair=args.claim_pair,
        delta=args.delta,
    )
    print("Wrote multidevice heatmaps:")
    if isinstance(refs.get("stability_hat_heatmap"), dict):
        print(" ", refs["stability_hat_heatmap"].get("pdf"))
        print(" ", refs["stability_hat_heatmap"].get("png"))
    if isinstance(refs.get("ci_low_heatmap"), dict):
        print(" ", refs["ci_low_heatmap"].get("pdf"))
        print(" ", refs["ci_low_heatmap"].get("png"))


if __name__ == "__main__":
    main()
