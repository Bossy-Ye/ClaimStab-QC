from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from claimstab.figures.plot_rq4_adaptive import plot_rq4_adaptive


CLAIM_PAIRS = "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline"
DELTAS = "0.0,0.01,0.05"


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _extract_strategy_record(strategy_name: str, strategy_group: str, claim_json: Path) -> dict[str, Any]:
    payload = _load_json(claim_json)
    experiments = payload.get("experiments", [])
    if not isinstance(experiments, list) or not experiments:
        raise ValueError(f"No experiments found in: {claim_json}")
    exp = experiments[0]
    if not isinstance(exp, dict):
        raise ValueError(f"Invalid experiment payload in: {claim_json}")

    sampling = exp.get("sampling", {})
    sampling = sampling if isinstance(sampling, dict) else {}
    adaptive = sampling.get("adaptive_stopping")
    adaptive = adaptive if isinstance(adaptive, dict) else {}

    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    rows = [row for row in rows if isinstance(row, dict)]
    by_variant: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: (str(r.get("claim_pair")), _as_float(r.get("delta")))):
        by_variant.append(
            {
                "claim_pair": row.get("claim_pair"),
                "delta": row.get("delta"),
                "decision": row.get("decision"),
                "stability_hat": row.get("stability_hat"),
                "stability_ci_low": row.get("stability_ci_low"),
                "stability_ci_high": row.get("stability_ci_high"),
                "n_claim_evals": row.get("n_claim_evals"),
                "space_preset": row.get("space_preset"),
            }
        )

    k_used = sampling.get("sampled_configurations_with_baseline")
    if adaptive.get("enabled"):
        k_used = adaptive.get("selected_configurations_with_baseline", k_used)

    return {
        "strategy": strategy_name,
        "strategy_group": strategy_group,
        "claim_json": str(claim_json.resolve()),
        "sampling_mode": sampling.get("mode"),
        "k_used": k_used,
        "k_budget": sampling.get("sample_size"),
        "perturbation_space_size": sampling.get("perturbation_space_size"),
        "adaptive_stopping": adaptive,
        "rows_by_delta": by_variant,
    }


def _attach_agreement(summary: dict[str, Any]) -> None:
    strategies = summary.get("strategies", [])
    if not isinstance(strategies, list):
        return
    baseline = next((row for row in strategies if isinstance(row, dict) and row.get("strategy_group") == "full_factorial"), None)
    if not isinstance(baseline, dict):
        return
    baseline_decision = {
        (str(row.get("claim_pair")), str(row.get("delta"))): str(row.get("decision"))
        for row in baseline.get("rows_by_delta", [])
        if isinstance(row, dict)
    }
    for strategy in strategies:
        if not isinstance(strategy, dict):
            continue
        matches: dict[str, bool] = {}
        total = 0
        hit = 0
        for row in strategy.get("rows_by_delta", []):
            if not isinstance(row, dict):
                continue
            key = (str(row.get("claim_pair")), str(row.get("delta")))
            decision = str(row.get("decision"))
            if key not in baseline_decision:
                continue
            ok = decision == baseline_decision[key]
            matches[f"{key[0]}|{key[1]}"] = ok
            total += 1
            if ok:
                hit += 1
        strategy["agreement_with_factorial"] = {
            "per_variant": matches,
            "rate": (float(hit) / float(total)) if total else None,
        }


def _attach_source_e1_bands(summary: dict[str, Any], source_e1_json: Path) -> None:
    payload = _load_json(source_e1_json)
    rows = payload.get("comparative", {}).get("space_claim_delta", [])
    rows = [row for row in rows if isinstance(row, dict) and row.get("space_preset") == "sampling_only_exact"]
    by_variant = {(str(row.get("claim_pair")), str(row.get("delta"))): row for row in rows}

    values = sorted(_as_float(row.get("stability_hat")) for row in rows)
    if not values:
        return
    low_cut = values[max(0, len(values) // 3 - 1)]
    high_cut = values[max(0, (2 * len(values)) // 3 - 1)]

    for strategy in summary.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        for row in strategy.get("rows_by_delta", []):
            if not isinstance(row, dict):
                continue
            key = (str(row.get("claim_pair")), str(row.get("delta")))
            source = by_variant.get(key)
            if not source:
                continue
            s = _as_float(source.get("stability_hat"))
            if s <= low_cut:
                band = "lower_source_band"
            elif s <= high_cut:
                band = "middle_source_band"
            else:
                band = "upper_source_band"
            row["source_e1_sampling_only_stability_hat"] = s
            row["source_e1_sampling_only_decision"] = source.get("decision")
            row["source_band"] = band

    for strategy in summary.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        grouped: dict[str, list[bool]] = {}
        for row in strategy.get("rows_by_delta", []):
            if not isinstance(row, dict):
                continue
            band = str(row.get("source_band", "unknown"))
            claim_pair = str(row.get("claim_pair"))
            delta = str(row.get("delta"))
            key = f"{claim_pair}|{delta}"
            ok = bool((strategy.get("agreement_with_factorial") or {}).get("per_variant", {}).get(key))
            grouped.setdefault(band, []).append(ok)
        strategy["agreement_by_source_band"] = {
            band: {"n": len(values), "rate": (sum(1 for v in values if v) / len(values)) if values else None}
            for band, values in grouped.items()
        }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run evaluation_v2 RQ4 policy comparison on the expanded E5 grid.")
    ap.add_argument("--out", default="output/paper/evaluation_v2/runs/E5_policy_comparison")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default="basic")
    ap.add_argument("--suite", default="large")
    ap.add_argument("--sample-seed", type=int, default=42)
    ap.add_argument("--adaptive-tuned-target-ci-width", type=float, default=0.11)
    ap.add_argument(
        "--source-e1-json",
        default="output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json",
        help="Existing E1 artifact used only to annotate source-band metadata.",
    )
    ap.add_argument("--skip-run", action="store_true", help="Skip execution and summarize existing outputs only.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out_root = Path(args.out)
    runs_dir = out_root / "runs"
    figs_dir = out_root / "figures"
    runs_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)

    strategy_specs = [
        {"name": "full_factorial", "group": "full_factorial", "sampling_mode": "full_factorial", "extra": []},
        {"name": "random_k_32", "group": "random_k", "sampling_mode": "random_k", "extra": ["--sample-size", "32"]},
        {"name": "random_k_64", "group": "random_k", "sampling_mode": "random_k", "extra": ["--sample-size", "64"]},
        {
            "name": "adaptive_ci",
            "group": "adaptive_ci",
            "sampling_mode": "adaptive_ci",
            "extra": [
                "--target-ci-width",
                "0.05",
                "--max-sample-size",
                "256",
                "--min-sample-size",
                "16",
                "--step-size",
                "8",
            ],
        },
        {
            "name": "adaptive_ci_tuned",
            "group": "adaptive_ci_tuned",
            "sampling_mode": "adaptive_ci",
            "extra": [
                "--target-ci-width",
                str(args.adaptive_tuned_target_ci_width),
                "--max-sample-size",
                "256",
                "--min-sample-size",
                "16",
                "--step-size",
                "8",
            ],
        },
    ]

    for spec in strategy_specs:
        run_dir = runs_dir / str(spec["name"])
        if not args.skip_run:
            cmd = [
                sys.executable,
                "-m",
                "claimstab.pipelines.claim_stability_app",
                "--task",
                "maxcut",
                "--suite",
                str(args.suite),
                "--space-preset",
                "sampling_policy_eval",
                "--claim-pairs",
                CLAIM_PAIRS,
                "--deltas",
                DELTAS,
                "--sampling-mode",
                str(spec["sampling_mode"]),
                "--sample-seed",
                str(args.sample_seed),
                "--backend-engine",
                str(args.backend_engine),
                "--out-dir",
                str(run_dir),
            ]
            cmd.extend(list(spec["extra"]))
            _run(cmd)

    strategy_rows: list[dict[str, Any]] = []
    for spec in strategy_specs:
        claim_json = runs_dir / str(spec["name"]) / "claim_stability.json"
        if not claim_json.exists():
            continue
        strategy_rows.append(
            _extract_strategy_record(
                strategy_name=str(spec["name"]),
                strategy_group=str(spec["group"]),
                claim_json=claim_json,
            )
        )

    summary = {
        "schema_version": "rq4_evaluation_v2_v1",
        "task": "maxcut",
        "suite": str(args.suite),
        "space_preset": "sampling_policy_eval",
        "claim_pairs": CLAIM_PAIRS.split(","),
        "deltas": [0.0, 0.01, 0.05],
        "adaptive_tuned_target_ci_width": float(args.adaptive_tuned_target_ci_width),
        "source_selection_note": (
            "All 9 unique MaxCut ranking claim-pair/delta variants are evaluated on the E5-only expanded sampling grid. "
            "Source-band annotations are derived from E1 sampling_only_exact stability estimates."
        ),
        "strategies": strategy_rows,
    }
    _attach_agreement(summary)
    _attach_source_e1_bands(summary, Path(args.source_e1_json))

    refs = plot_rq4_adaptive(summary, figs_dir)
    summary["figures"] = refs

    summary_path = out_root / "rq4_policy_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote:")
    print(" ", summary_path.resolve())
    if isinstance(refs.get("ci_width_vs_cost"), dict):
        print(" ", refs["ci_width_vs_cost"].get("pdf"))
        print(" ", refs["ci_width_vs_cost"].get("png"))
    if isinstance(refs.get("agreement_vs_cost"), dict):
        print(" ", refs["agreement_vs_cost"].get("pdf"))
        print(" ", refs["agreement_vs_cost"].get("png"))


if __name__ == "__main__":
    main()
