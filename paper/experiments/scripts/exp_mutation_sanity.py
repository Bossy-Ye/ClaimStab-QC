from __future__ import annotations

import argparse
import json
from pathlib import Path

from claimstab.analysis.sanity import load_claim_payload, load_score_rows_csv, summarize_mutation_sanity_run


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run ranking-only mutation-style sanity analysis on an existing ClaimStab output directory."
    )
    ap.add_argument("--run-dir", default="output/presentations/large/maxcut_ranking")
    ap.add_argument("--out", default="output/presentations/large/mutation_sanity/mutation_sanity_summary.json")
    ap.add_argument(
        "--mutations",
        default="baseline_relation_flip",
        help="Comma-separated mutation kinds. Supported: baseline_relation_flip, swap_methods, global_score_offset",
    )
    ap.add_argument(
        "--require-fragility-signal",
        action="store_true",
        help="Return non-zero if no mutation case produces a lower-stability signal.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    claim_json = run_dir / "claim_stability.json"
    scores_csv = run_dir / "scores.csv"
    if not claim_json.exists():
        raise FileNotFoundError(f"Expected output not found: {claim_json}")
    if not scores_csv.exists():
        raise FileNotFoundError(f"Expected output not found: {scores_csv}")

    mutations = [token.strip() for token in str(args.mutations).split(",") if token.strip()]
    payload = load_claim_payload(claim_json)
    rows = load_score_rows_csv(scores_csv)
    summary = summarize_mutation_sanity_run(
        payload=payload,
        rows=rows,
        mutation_kinds=mutations,
    )
    summary["run_dir"] = str(run_dir.resolve())
    summary["claim_json"] = str(claim_json.resolve())
    summary["scores_csv"] = str(scores_csv.resolve())

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote:")
    print(" ", out_path.resolve())
    print("Fragility signal detected:", summary.get("fragility_signal_detected"))

    if args.require_fragility_signal and not bool(summary.get("fragility_signal_detected")):
        print("Fragility signal was required but not detected.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
