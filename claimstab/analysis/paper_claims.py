from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt

from claimstab.figures.adaptive import plot_compact_table
from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, apply_style, decision_color, save_fig


def _norm_str(value: Any) -> str:
    return str(value).strip()


def _norm_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("Loading paper claims YAML requires pyyaml (pip install pyyaml).") from exc
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Paper claims file must contain a mapping/object: {path}")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Claim stability input must be a mapping/object: {path}")
    return payload


def load_paper_claims(path: Path) -> list[dict[str, Any]]:
    payload = _load_yaml(path)
    rows = payload.get("paper_claims", [])
    if not isinstance(rows, list):
        raise ValueError("paper_claims must be a list.")
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"paper_claims[{idx}] must be an object.")
        claim_id = _norm_str(row.get("id", ""))
        text = _norm_str(row.get("text", ""))
        mapping = row.get("mapping", {})
        if not claim_id:
            raise ValueError(f"paper_claims[{idx}].id must be non-empty.")
        if not text:
            raise ValueError(f"paper_claims[{idx}].text must be non-empty.")
        if not isinstance(mapping, dict):
            raise ValueError(f"paper_claims[{idx}].mapping must be an object.")
        out.append({"id": claim_id, "text": text, "mapping": mapping})
    return out


def resolve_paper_claims(
    *,
    claims: list[dict[str, Any]],
    claim_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    comparative_rows = claim_payload.get("comparative", {}).get("space_claim_delta", [])
    if not isinstance(comparative_rows, list):
        comparative_rows = []
    comparable = [row for row in comparative_rows if isinstance(row, dict)]

    results: list[dict[str, Any]] = []
    for claim in claims:
        mapping = claim.get("mapping", {})
        mapping = mapping if isinstance(mapping, dict) else {}
        claim_type = _norm_str(mapping.get("type", "ranking")) or "ranking"
        claim_pair = mapping.get("claim_pair")
        space = mapping.get("space")
        delta = _norm_float(mapping.get("delta"))

        matched: dict[str, Any] | None = None
        for row in comparable:
            if _norm_str(row.get("claim_type", "ranking")) != claim_type:
                continue
            if claim_pair is not None and _norm_str(row.get("claim_pair")) != _norm_str(claim_pair):
                continue
            if space is not None and _norm_str(row.get("space_preset")) != _norm_str(space):
                continue
            row_delta = _norm_float(row.get("delta"))
            if delta is not None and row_delta is not None and abs(row_delta - delta) > 1e-12:
                continue
            if delta is not None and row_delta is None:
                continue
            matched = row
            break

        out_row: dict[str, Any] = {
            "claim_id": claim["id"],
            "claim_text": claim["text"],
            "mapping_type": claim_type,
            "mapping_claim_pair": claim_pair,
            "mapping_space": space,
            "mapping_delta": delta,
            "mapped": bool(matched is not None),
            "decision": "missing",
            "stability_hat": None,
            "stability_ci_low": None,
            "stability_ci_high": None,
            "n_claim_evals": None,
            "source_space_preset": None,
            "source_claim_pair": None,
            "source_delta": None,
        }
        if matched is not None:
            out_row.update(
                {
                    "decision": _norm_str(matched.get("decision", "inconclusive")) or "inconclusive",
                    "stability_hat": _norm_float(matched.get("stability_hat")),
                    "stability_ci_low": _norm_float(matched.get("stability_ci_low")),
                    "stability_ci_high": _norm_float(matched.get("stability_ci_high")),
                    "n_claim_evals": matched.get("n_claim_evals"),
                    "source_space_preset": matched.get("space_preset"),
                    "source_claim_pair": matched.get("claim_pair"),
                    "source_delta": matched.get("delta"),
                }
            )
        results.append(out_row)
    return results


def write_claim_outcomes_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarize_prevalence(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    counts: dict[str, int] = {}
    mapped_total = 0
    for row in rows:
        decision = _norm_str(row.get("decision", "missing")) or "missing"
        counts[decision] = counts.get(decision, 0) + 1
        if bool(row.get("mapped")):
            mapped_total += 1
    total = len(rows)
    out: list[dict[str, Any]] = []
    for decision, count in sorted(counts.items(), key=lambda kv: (kv[0] != "stable", kv[0])):
        out.append(
            {
                "decision": decision,
                "count": count,
                "rate_over_all_claims": (float(count) / float(total)) if total else 0.0,
                "mapped_claims": mapped_total,
                "total_claims": total,
            }
        )
    return out


def write_prevalence_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def plot_claim_outcomes(rows: list[dict[str, Any]], out_path: Path) -> dict[str, str] | None:
    if not rows:
        return None

    labels: list[str] = []
    values: list[float] = []
    err_low: list[float] = []
    err_high: list[float] = []
    decisions: list[str] = []
    for row in rows:
        labels.append(_norm_str(row.get("claim_id", "unknown")))
        decisions.append(_norm_str(row.get("decision", "missing")) or "missing")
        hat = _norm_float(row.get("stability_hat"))
        low = _norm_float(row.get("stability_ci_low"))
        high = _norm_float(row.get("stability_ci_high"))
        if hat is None:
            values.append(0.0)
            err_low.append(0.0)
            err_high.append(0.0)
            continue
        values.append(hat)
        err_low.append(max(0.0, hat - (low if low is not None else hat)))
        err_high.append(max(0.0, (high if high is not None else hat) - hat))

    colors = [decision_color(d) for d in decisions]

    apply_style()
    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    if len(labels) <= 2 or max(values) - min(values) < 0.01:
        import numpy as np

        table_rows = []
        for label, decision, hat, lo, hi in zip(labels, decisions, values, err_low, err_high):
            table_rows.append([hat, hat - lo, hat + hi, decision])
        matrix = np.array([[float(r[0]), float(r[1]), float(r[2])] for r in table_rows], dtype=float)
        plot_compact_table(
            ax,
            row_labels=labels,
            col_labels=["stability_hat", "ci_low", "ci_high"],
            matrix=matrix,
            title="Paper claims: stability with CI",
            note="Compact table used because visual spread is limited.",
        )
        return save_fig(fig, out_path)

    y = list(range(len(labels)))
    ax.hlines(y, xmin=0.0, xmax=1.0, color="#d8d8d8", linewidth=0.8, alpha=0.6)
    ax.errorbar(
        values,
        y,
        xerr=[err_low, err_high],
        fmt="o",
        ecolor="#6a6a6a",
        elinewidth=1.0,
        capsize=3.2,
        markersize=4.6,
        color="#5f5f5f",
        zorder=3,
    )
    for yi, label, value, decision, color in zip(y, labels, values, decisions, colors):
        ax.scatter([value], [yi], s=42, color=color, zorder=4, edgecolor="#2f2f2f", linewidth=0.4)
        ax.text(1.01, yi, decision, va="center", ha="left", fontsize=8.0, color="#4a4a4a")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0.0, 1.08)
    ax.set_xlabel("stability_hat (with CI)")
    ax.set_ylabel("paper claim id")
    ax.set_title("Paper claims: stability with CI", loc="left")
    return save_fig(fig, out_path)


def generate_paper_claims_outputs(
    *,
    claims_path: Path,
    input_json: Path,
    out_root: Path,
) -> dict[str, Any]:
    claims = load_paper_claims(claims_path)
    payload = _load_json(input_json)
    rows = resolve_paper_claims(claims=claims, claim_payload=payload)

    tables_dir = out_root / "tables"
    figs_dir = out_root / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "paper_claims_outcomes.csv"
    prevalence_csv_path = tables_dir / "paper_claims_prevalence.csv"
    fig_base = figs_dir / "paper_claims_outcomes"
    write_claim_outcomes_csv(rows, csv_path)
    prevalence = summarize_prevalence(rows)
    write_prevalence_csv(prevalence, prevalence_csv_path)
    fig_ref = plot_claim_outcomes(rows, fig_base)
    return {
        "claims_file": str(claims_path.resolve()),
        "input_json": str(input_json.resolve()),
        "csv": str(csv_path.resolve()),
        "prevalence_csv": str(prevalence_csv_path.resolve()),
        "prevalence": prevalence,
        "figures": fig_ref,
        "rows": len(rows),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Map paper-style natural-language claims to claim_stability outcomes.")
    ap.add_argument("--claims", required=True, help="Path to paper_claims YAML.")
    ap.add_argument("--input", required=True, help="Path to claim_stability.json.")
    ap.add_argument("--out", required=True, help="Output root for tables/ and figures/.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    summary = generate_paper_claims_outputs(
        claims_path=Path(args.claims),
        input_json=Path(args.input),
        out_root=Path(args.out),
    )
    print("Wrote paper claims outcomes:")
    print(" ", summary["csv"])
    figs = summary.get("figures")
    if isinstance(figs, dict):
        print(" ", figs.get("pdf"))
        print(" ", figs.get("png"))


if __name__ == "__main__":
    main()
