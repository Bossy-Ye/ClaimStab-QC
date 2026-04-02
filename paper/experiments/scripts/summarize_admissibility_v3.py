from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path
from typing import Iterable


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _cohen_kappa(labels_a: Iterable[str], labels_b: Iterable[str]) -> float | None:
    a = list(labels_a)
    b = list(labels_b)
    if len(a) != len(b) or not a:
        return None
    labels = sorted(set(a) | set(b))
    po = sum(1 for left, right in zip(a, b) if left == right) / len(a)
    pa = 0.0
    for label in labels:
        p_left = sum(1 for value in a if value == label) / len(a)
        p_right = sum(1 for value in b if value == label) / len(b)
        pa += p_left * p_right
    if pa >= 1.0:
        return 1.0
    return (po - pa) / (1.0 - pa)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Summarize W4 admissibility-study ratings.")
    ap.add_argument("--items", default="paper/experiments/data/admissibility_v1/admissibility_items_v1.csv")
    ap.add_argument("--ratings-dir", default="paper/experiments/data/admissibility_v1/ratings")
    ap.add_argument("--out-root", default="output/paper/evaluation_v3")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    items_path = Path(args.items)
    ratings_dir = Path(args.ratings_dir)
    out_root = Path(args.out_root)

    items = _read_rows(items_path)
    templates_dir = out_root / "runs" / "W4_admissibility" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_path = templates_dir / "rater_template.csv"
    if not template_path.exists():
        rows = [{"item_id": row["item_id"], "label": ""} for row in items]
        _write_csv(template_path, rows)

    rating_files = sorted(ratings_dir.glob("rater_*.csv"))
    summary_dir = out_root / "derived_paper_evaluation" / "RQ2_semantics"
    summary_dir.mkdir(parents=True, exist_ok=True)

    if len(rating_files) < 2:
        pending = {
            "schema_version": "w4_admissibility_pending_v1",
            "status": "pending_human_labels",
            "items_file": str(items_path.resolve()),
            "ratings_dir": str(ratings_dir.resolve()),
            "required_rater_files": [f"rater_{idx}.csv" for idx in range(1, 4)],
            "template_file": str(template_path.resolve()),
        }
        (summary_dir / "admissibility_study_status.json").write_text(json.dumps(pending, indent=2), encoding="utf-8")
        (out_root / "runs" / "W4_admissibility" / "pending_status.json").write_text(
            json.dumps(pending, indent=2),
            encoding="utf-8",
        )
        print("W4 pending: need at least two rater CSV files.")
        return

    item_lookup = {row["item_id"]: row for row in items}
    ratings: dict[str, dict[str, str]] = {}
    for path in rating_files:
        rows = _read_rows(path)
        ratings[path.stem] = {row["item_id"]: row["label"].strip().lower() for row in rows if row.get("item_id")}

    pairwise: list[dict[str, object]] = []
    disagreements: list[dict[str, object]] = []
    for left, right in itertools.combinations(sorted(ratings), 2):
        shared = sorted(set(ratings[left]) & set(ratings[right]))
        kappa = _cohen_kappa((ratings[left][item] for item in shared), (ratings[right][item] for item in shared))
        pairwise.append({"rater_a": left, "rater_b": right, "kappa": None if kappa is None else round(kappa, 4), "shared_items": len(shared)})

    for item_id, item in item_lookup.items():
        labels = {rater: ratings[rater].get(item_id, "") for rater in sorted(ratings)}
        non_empty = [label for label in labels.values() if label]
        agreement = len(set(non_empty)) <= 1 and len(non_empty) == len(labels)
        disagreements.append(
            {
                "item_id": item_id,
                "perturbation": item["perturbation"],
                "expected_label": item["expected_label"],
                "trigger_rule": item["trigger_rule"],
                **labels,
                "agreement": "yes" if agreement else "no",
            }
        )

    _write_csv(summary_dir / "admissibility_pairwise_kappa.csv", pairwise)
    _write_csv(summary_dir / "admissibility_disagreement_table.csv", disagreements)

    overall = {
        "schema_version": "w4_admissibility_summary_v1",
        "status": "complete",
        "items_file": str(items_path.resolve()),
        "ratings": [str(path.resolve()) for path in rating_files],
        "pairwise_kappa_mean": round(
            sum(float(row["kappa"]) for row in pairwise if row["kappa"] is not None) / max(1, len(pairwise)),
            4,
        ),
        "pairwise": pairwise,
    }
    (summary_dir / "admissibility_study_status.json").write_text(json.dumps(overall, indent=2), encoding="utf-8")
    print(f"Wrote W4 admissibility summary to {summary_dir}")


if __name__ == "__main__":
    main()
