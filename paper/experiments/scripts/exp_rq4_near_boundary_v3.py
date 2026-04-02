from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from claimstab.figures.plot_rq4_adaptive import plot_rq4_adaptive


CLAIM_PAIRS = "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1"
DELTAS = "0.0,0.01,0.02,0.05"


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at: {path}")
    return payload


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _extract_strategy_record(strategy_name: str, strategy_group: str, claim_json: Path) -> dict[str, Any]:
    payload = _load_json(claim_json)
    exp = payload.get("experiments", [])[0]
    sampling = exp.get("sampling", {}) if isinstance(exp, dict) else {}
    sampling = sampling if isinstance(sampling, dict) else {}
    adaptive = sampling.get("adaptive_stopping")
    adaptive = adaptive if isinstance(adaptive, dict) else {}

    rows = [row for row in payload.get("comparative", {}).get("space_claim_delta", []) if isinstance(row, dict)]
    rows_by_delta: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: (str(r.get("claim_pair")), _as_float(r.get("delta")))):
        rows_by_delta.append(
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
        "rows_by_delta": rows_by_delta,
    }


def _attach_agreement(summary: dict[str, Any]) -> None:
    strategies = summary.get("strategies", [])
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
        total = 0
        hit = 0
        per_variant: dict[str, bool] = {}
        for row in strategy.get("rows_by_delta", []):
            if not isinstance(row, dict):
                continue
            key = (str(row.get("claim_pair")), str(row.get("delta")))
            if key not in baseline_decision:
                continue
            ok = str(row.get("decision")) == baseline_decision[key]
            total += 1
            if ok:
                hit += 1
            per_variant[f"{key[0]}|{key[1]}"] = ok
        strategy["agreement_with_factorial"] = {
            "per_variant": per_variant,
            "rate": (float(hit) / float(total)) if total else None,
        }


def _attach_source_s2(summary: dict[str, Any], source_s2_json: Path) -> None:
    payload = _load_json(source_s2_json)
    rows = [row for row in payload.get("comparative", {}).get("space_claim_delta", []) if isinstance(row, dict)]
    source_map: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("claim_pair")), str(row.get("delta")))
        record = {
            "source_s2_space_preset": row.get("space_preset"),
            "source_s2_stability_hat": row.get("stability_hat"),
            "source_s2_decision": row.get("decision"),
        }
        current = source_map.get(key)
        if current is None or _as_float(record["source_s2_stability_hat"]) > _as_float(current["source_s2_stability_hat"]):
            source_map[key] = record

    for strategy in summary.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        for row in strategy.get("rows_by_delta", []):
            if not isinstance(row, dict):
                continue
            key = (str(row.get("claim_pair")), str(row.get("delta")))
            source = source_map.get(key)
            if not source:
                continue
            row.update(source)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run W5 near-boundary MaxCut policy comparison on the expanded sampling grid.")
    ap.add_argument("--out", default="output/paper/evaluation_v3/runs/W5_near_boundary_policy")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default="basic")
    ap.add_argument("--suite", default="standard")
    ap.add_argument("--sample-seed", type=int, default=19)
    ap.add_argument("--adaptive-tuned-target-ci-width", type=float, default=0.11)
    ap.add_argument(
        "--source-s2-json",
        default="output/paper/evaluation_v2/runs/S2_boundary/run/claim_stability.json",
    )
    ap.add_argument("--skip-run", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out_root = Path(args.out)
    runs_dir = out_root / "runs"
    figs_dir = out_root / "figures"
    cache_db = out_root / "near_boundary_cache.sqlite"
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
                "--cache-db",
                str(cache_db),
                "--out-dir",
                str(run_dir),
            ]
            cmd.extend(list(spec["extra"]))
            _run(cmd)

    strategy_rows: list[dict[str, Any]] = []
    for spec in strategy_specs:
        claim_json = runs_dir / str(spec["name"]) / "claim_stability.json"
        if claim_json.exists():
            strategy_rows.append(
                _extract_strategy_record(
                    strategy_name=str(spec["name"]),
                    strategy_group=str(spec["group"]),
                    claim_json=claim_json,
                )
            )

    summary = {
        "schema_version": "rq4_near_boundary_v3_v1",
        "task": "maxcut",
        "suite": str(args.suite),
        "space_preset": "sampling_policy_eval",
        "claim_pairs": CLAIM_PAIRS.split(","),
        "deltas": [0.0, 0.01, 0.02, 0.05],
        "adaptive_tuned_target_ci_width": float(args.adaptive_tuned_target_ci_width),
        "source_selection_note": (
            "Near-boundary pack sourced from S2 claim pairs/deltas and evaluated on the expanded sampling_policy_eval grid. "
            "Source S2 stability metadata records the highest source-space stability per claim-pair/delta."
        ),
        "strategies": strategy_rows,
    }
    _attach_agreement(summary)
    _attach_source_s2(summary, Path(args.source_s2_json))
    refs = plot_rq4_adaptive(summary, figs_dir)
    summary["figures"] = refs

    summary_path = out_root / "rq4_near_boundary_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote:", summary_path.resolve())
    for key in ("ci_width_vs_cost", "agreement_vs_cost"):
        if isinstance(refs.get(key), dict):
            print(" ", refs[key].get("pdf"))
            print(" ", refs[key].get("png"))


if __name__ == "__main__":
    main()
