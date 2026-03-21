from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from claimstab.figures.plot_rq4_adaptive import plot_rq4_adaptive


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


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
    by_delta: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: _as_float(r.get("delta"))):
        by_delta.append(
            {
                "delta": row.get("delta"),
                "decision": row.get("decision"),
                "stability_hat": row.get("stability_hat"),
                "stability_ci_low": row.get("stability_ci_low"),
                "stability_ci_high": row.get("stability_ci_high"),
                "n_claim_evals": row.get("n_claim_evals"),
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
        "rows_by_delta": by_delta,
    }


def _attach_agreement(summary: dict[str, Any]) -> None:
    strategies = summary.get("strategies", [])
    if not isinstance(strategies, list):
        return
    baseline = next((row for row in strategies if isinstance(row, dict) and row.get("strategy_group") == "full_factorial"), None)
    if not isinstance(baseline, dict):
        return
    baseline_decision = {
        str(row.get("delta")): str(row.get("decision"))
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
            delta = str(row.get("delta"))
            decision = str(row.get("decision"))
            if delta not in baseline_decision:
                continue
            ok = decision == baseline_decision[delta]
            matches[delta] = ok
            total += 1
            if ok:
                hit += 1
        strategy["agreement_with_factorial"] = {
            "per_delta": matches,
            "rate": (float(hit) / float(total)) if total else None,
        }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run RQ4 adaptive sampling comparison and generate summary figures.")
    ap.add_argument("--out", default="output/presentations/large/rq4_adaptive")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default="basic")
    ap.add_argument("--suite", default="standard")
    ap.add_argument("--sample-seed", type=int, default=42)
    ap.add_argument(
        "--adaptive-tuned-target-ci-width",
        type=float,
        default=0.11,
        help="Relaxed CI-width target for the tuned adaptive strategy.",
    )
    ap.add_argument("--skip-run", action="store_true", help="Skip execution and only summarize existing outputs.")
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
                "128",
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
                "128",
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
                "sampling_only",
                "--claim-pairs",
                "QAOA_p2>QAOA_p1",
                "--deltas",
                "0.0,0.01",
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
        "schema_version": "rq4_adaptive_v1",
        "task": "maxcut",
        "suite": str(args.suite),
        "space_preset": "sampling_only",
        "claim_pair": "QAOA_p2>QAOA_p1",
        "deltas": [0.0, 0.01],
        "adaptive_tuned_target_ci_width": float(args.adaptive_tuned_target_ci_width),
        "strategies": strategy_rows,
    }
    _attach_agreement(summary)

    refs = plot_rq4_adaptive(summary, figs_dir)
    summary["figures"] = refs

    summary_path = out_root / "rq4_adaptive_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    tuned_summary_path = out_root / "rq4_adaptive_tuned_summary.json"
    tuned_summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote:")
    print(" ", summary_path.resolve())
    print(" ", tuned_summary_path.resolve())
    if isinstance(refs.get("ci_width_vs_cost"), dict):
        print(" ", refs["ci_width_vs_cost"].get("pdf"))
        print(" ", refs["ci_width_vs_cost"].get("png"))
    if isinstance(refs.get("agreement_vs_cost"), dict):
        print(" ", refs["agreement_vs_cost"].get("pdf"))
        print(" ", refs["agreement_vs_cost"].get("png"))


if __name__ == "__main__":
    main()
