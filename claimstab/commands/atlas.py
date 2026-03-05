from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from claimstab.atlas import build_dataset_registry_markdown, compare_claim_outputs, publish_result, validate_atlas


def cmd_publish_result(args: argparse.Namespace) -> int:
    try:
        record = publish_result(
            args.run_dir,
            atlas_root=args.atlas_root,
            contributor=args.contributor,
            title=args.title,
            submission_id=args.submission_id,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Published submission: {record['submission_id']}")
    print(f"Atlas root: {Path(args.atlas_root).resolve()}")
    print(f"Task/Suite: {record.get('task')} / {record.get('suite')}")
    return 0


def cmd_validate_atlas(args: argparse.Namespace) -> int:
    try:
        result = validate_atlas(args.atlas_root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Atlas valid: {result.root}")
    print(f"Submission count: {result.submission_count}")
    if result.warnings:
        print("Warnings:")
        for line in result.warnings:
            print(f"- {line}")
    return 0


def cmd_export_dataset_registry(args: argparse.Namespace) -> int:
    try:
        markdown = build_dataset_registry_markdown(atlas_root=args.atlas_root, repo_url=args.repo_url)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    print(f"Wrote dataset registry page: {out}")
    return 0


def cmd_atlas_compare(args: argparse.Namespace) -> int:
    try:
        diff = compare_claim_outputs(args.left, args.right)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Left: {diff.get('left_source')}")
    print(f"Right: {diff.get('right_source')}")
    print(f"Paired rows: {diff.get('paired_rows')}")
    print(f"Decision changed: {diff.get('decision_changed_count')}")
    print(f"Naive comparison changed: {diff.get('naive_comparison_changed_count')}")
    print(f"Mean flip-rate delta (right-left): {diff.get('mean_flip_rate_delta')}")
    print(f"Mean stability-hat delta (right-left): {diff.get('mean_stability_hat_delta')}")
    print(f"Left-only keys: {len(diff.get('left_only_keys', []))}")
    print(f"Right-only keys: {len(diff.get('right_only_keys', []))}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(diff, indent=2), encoding="utf-8")
        print(f"Wrote compare diff: {out}")
    return 0
