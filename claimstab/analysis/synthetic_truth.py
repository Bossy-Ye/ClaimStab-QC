from __future__ import annotations

import argparse
import json
from random import Random
from typing import Any, Iterable

from claimstab.claims.stability import ci_width, conservative_stability_decision, estimate_binomial_rate


def _sample_binomial(n: int, p: float, rng: Random) -> int:
    if n <= 0:
        return 0
    if p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    success = 0
    for _ in range(n):
        if rng.random() < p:
            success += 1
    return success


def simulate_truth_profile(
    *,
    true_stability: float,
    n_evals: int,
    trials: int = 500,
    threshold: float = 0.95,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> dict[str, Any]:
    if not 0.0 <= true_stability <= 1.0:
        raise ValueError(f"true_stability must be in [0,1], got {true_stability}")
    if n_evals <= 0:
        raise ValueError(f"n_evals must be > 0, got {n_evals}")
    if trials <= 0:
        raise ValueError(f"trials must be > 0, got {trials}")

    rng = Random(seed)
    decision_counts = {"stable": 0, "unstable": 0, "inconclusive": 0}
    covered = 0
    total_rate = 0.0
    total_width = 0.0

    for _ in range(trials):
        successes = _sample_binomial(n_evals, true_stability, rng)
        est = estimate_binomial_rate(successes=successes, total=n_evals, confidence=confidence_level)
        decision = conservative_stability_decision(est, threshold).value
        decision_counts[decision] += 1
        if est.ci_low <= true_stability <= est.ci_high:
            covered += 1
        total_rate += float(est.rate)
        total_width += float(ci_width(est))

    return {
        "true_stability": float(true_stability),
        "n_evals": int(n_evals),
        "trials": int(trials),
        "threshold": float(threshold),
        "confidence_level": float(confidence_level),
        "mean_hat": total_rate / float(trials),
        "mean_ci_width": total_width / float(trials),
        "coverage_rate": float(covered) / float(trials),
        "decision_rates": {
            key: float(count) / float(trials)
            for key, count in decision_counts.items()
        },
    }


def run_truth_grid(
    *,
    true_stabilities: Iterable[float],
    n_values: Iterable[int],
    trials: int = 500,
    threshold: float = 0.95,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seed_offset = 0
    for n in n_values:
        for p in true_stabilities:
            rows.append(
                simulate_truth_profile(
                    true_stability=float(p),
                    n_evals=int(n),
                    trials=trials,
                    threshold=threshold,
                    confidence_level=confidence_level,
                    seed=seed + seed_offset,
                )
            )
            seed_offset += 17

    rows.sort(key=lambda row: (float(row["true_stability"]), int(row["n_evals"])))
    return {
        "schema_version": "synthetic_truth_v1",
        "rows": rows,
        "config": {
            "true_stabilities": [float(v) for v in true_stabilities],
            "n_values": [int(v) for v in n_values],
            "trials": int(trials),
            "threshold": float(threshold),
            "confidence_level": float(confidence_level),
            "seed": int(seed),
        },
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Synthetic truth calibration for claim-stability CI/decision behavior.")
    ap.add_argument("--truths", default="0.80,0.90,0.95,0.99")
    ap.add_argument("--n-values", default="32,64,128,256")
    ap.add_argument("--trials", type=int, default=500)
    ap.add_argument("--threshold", type=float, default=0.95)
    ap.add_argument("--confidence-level", type=float, default=0.95)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="output/presentations/large/synthetic_truth.json")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    truths = [float(token.strip()) for token in str(args.truths).split(",") if token.strip()]
    n_values = [int(token.strip()) for token in str(args.n_values).split(",") if token.strip()]
    summary = run_truth_grid(
        true_stabilities=truths,
        n_values=n_values,
        trials=int(args.trials),
        threshold=float(args.threshold),
        confidence_level=float(args.confidence_level),
        seed=int(args.seed),
    )
    out_path = args.out
    from pathlib import Path

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote: {out.resolve()}")


if __name__ == "__main__":
    main()
