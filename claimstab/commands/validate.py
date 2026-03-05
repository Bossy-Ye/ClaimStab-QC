from __future__ import annotations

import argparse
import sys
from pathlib import Path

from claimstab.evidence import validate_evidence_file
from claimstab.spec import load_spec, validate_spec


def cmd_validate_spec(args: argparse.Namespace) -> int:
    try:
        spec = load_spec(args.spec, validate=False)
        validate_spec(spec)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Spec valid: {args.spec}")
    return 0


def cmd_validate_evidence(args: argparse.Namespace) -> int:
    try:
        result = validate_evidence_file(
            args.json,
            base_dir=args.base_dir,
            trace_jsonl=args.trace_jsonl,
            check_trace=not args.no_trace_check,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Evidence JSON: {Path(args.json).resolve()}")
    print(f"Schema valid: {result.schema_valid}")
    print(f"Trace checked: {result.trace_checked}")
    print(
        "Experiments checked: "
        f"{result.experiments_checked} "
        f"(trace matches: {result.experiments_with_trace_match})"
    )
    if result.warnings:
        print("Warnings:")
        for line in result.warnings:
            print(f"- {line}")
    if result.errors:
        print("Errors:", file=sys.stderr)
        for line in result.errors:
            print(f"- {line}", file=sys.stderr)
        return 2
    if args.strict_warnings and result.warnings:
        print("Validation failed because --strict-warnings is enabled.", file=sys.stderr)
        return 2
    print("Evidence validation passed.")
    return 0
