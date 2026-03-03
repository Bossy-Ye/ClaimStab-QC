from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

from claimstab.ecosystem import validate_ecosystem
from claimstab.spec import load_spec, validate_spec


def _csv_or_string(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    if value is None:
        return ""
    return str(value)


def _suite_name(spec: dict[str, Any]) -> str:
    task = spec.get("task")
    if isinstance(task, dict):
        task_suite = task.get("suite")
        if isinstance(task_suite, str) and task_suite.strip():
            return task_suite.strip()
    suite = spec.get("suite", "core")
    if isinstance(suite, str):
        return suite
    if isinstance(suite, dict):
        return str(suite.get("id") or suite.get("name") or "core")
    return "core"


def _extract_sampling(spec: dict[str, Any]) -> dict[str, Any]:
    def _pack(mode: str, sample_size: int | None, seed: int, raw: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = raw or {}
        return {
            "mode": mode,
            "sample_size": sample_size,
            "seed": seed,
            "target_ci_width": raw.get("target_ci_width"),
            "max_sample_size": raw.get("max_sample_size"),
            "min_sample_size": raw.get("min_sample_size"),
            "step_size": raw.get("step_size"),
        }

    sampling = spec.get("sampling", {})
    if isinstance(sampling, dict) and sampling:
        mode = str(sampling.get("mode", "full_factorial"))
        sample_size = sampling.get("sample_size")
        seed = int(sampling.get("seed", 0))
        return _pack(mode, int(sample_size) if sample_size is not None else None, seed, sampling)

    legacy = spec.get("sampling_policy", {})
    if isinstance(legacy, dict):
        policy = legacy.get("large_scale") or legacy.get("small_scale") or {}
        if isinstance(policy, dict) and policy:
            mode = str(policy.get("mode", "full_factorial"))
            sample_size = policy.get("sample_size")
            seed = int(policy.get("seed", 0))
            return _pack(mode, int(sample_size) if sample_size is not None else None, seed, policy)

    return _pack("full_factorial", None, 0, {})


def _extract_deltas(spec: dict[str, Any]) -> str:
    claims = spec.get("claims")
    if isinstance(claims, list):
        for entry in claims:
            if isinstance(entry, dict) and entry.get("type", "ranking") == "ranking":
                deltas = entry.get("deltas")
                if isinstance(deltas, list) and deltas:
                    return _csv_or_string(deltas)
    if isinstance(claims, dict):
        ranking = claims.get("ranking")
        if isinstance(ranking, dict):
            deltas = ranking.get("deltas")
            if isinstance(deltas, list) and deltas:
                return _csv_or_string(deltas)
    return "0.0,0.01,0.05"


def _extract_claim_pairs(spec: dict[str, Any]) -> str:
    claims = spec.get("claims")
    pairs: list[str] = []
    if isinstance(claims, list):
        for entry in claims:
            if not isinstance(entry, dict):
                continue
            if entry.get("type", "ranking") != "ranking":
                continue
            a = entry.get("method_a")
            b = entry.get("method_b")
            if isinstance(a, str) and isinstance(b, str) and a and b:
                pairs.append(f"{a}>{b}")
    elif isinstance(claims, dict):
        ranking = claims.get("ranking")
        if isinstance(ranking, dict):
            a = ranking.get("method_a")
            b = ranking.get("method_b")
            if isinstance(a, str) and isinstance(b, str) and a and b:
                pairs.append(f"{a}>{b}")

    if pairs:
        # de-duplicate while keeping order
        deduped: list[str] = []
        seen = set()
        for p in pairs:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return ",".join(deduped)

    return "QAOA_p2>RandomBaseline"


def _extract_decision(spec: dict[str, Any]) -> tuple[float, float]:
    decision_rule = spec.get("decision_rule", {})
    if isinstance(decision_rule, dict) and decision_rule:
        threshold = float(decision_rule.get("threshold", 0.95))
        confidence_level = float(decision_rule.get("confidence_level", 0.95))
        return threshold, confidence_level

    stability = spec.get("stability", {})
    if isinstance(stability, dict) and stability:
        threshold = float(stability.get("threshold", 0.95))
        confidence_level = float(stability.get("confidence_level", 0.95))
        return threshold, confidence_level

    return 0.95, 0.95


def _extract_space(spec: dict[str, Any]) -> tuple[str, str]:
    pert = spec.get("perturbations", {})
    if isinstance(pert, dict):
        presets = pert.get("presets")
        if isinstance(presets, list) and presets:
            return "--space-presets", _csv_or_string(presets)
        preset = pert.get("preset")
        if isinstance(preset, str) and preset:
            return "--space-preset", preset
    return "--space-preset", "baseline"


def _backend_engine(spec: dict[str, Any]) -> str:
    backend = spec.get("backend", {})
    if isinstance(backend, dict):
        return str(backend.get("engine", "basic"))
    return "basic"


def _infer_pipeline(spec: dict[str, Any]) -> str:
    pipeline = spec.get("pipeline")
    if isinstance(pipeline, str):
        value = pipeline.strip().lower()
        if value in {"main", "multidevice"}:
            return value

    experiment = spec.get("experiment")
    if isinstance(experiment, dict):
        value = experiment.get("pipeline") or experiment.get("track")
        if isinstance(value, str):
            low = value.strip().lower()
            if low in {"main", "paper", "comprehensive"}:
                return "main"
            if low in {"device", "multidevice", "device_aware"}:
                return "multidevice"

    if isinstance(spec.get("multidevice"), dict):
        return "multidevice"

    return "main"


def _build_main_command(spec_path: Path, spec: dict[str, Any], args: argparse.Namespace) -> list[str]:
    sampling = _extract_sampling(spec)
    mode = str(sampling["mode"])
    sample_size = sampling["sample_size"]
    sample_seed = int(sampling["seed"])
    if args.seed is not None:
        sample_seed = args.seed
    threshold, confidence = _extract_decision(spec)
    claim_pairs = _extract_claim_pairs(spec)
    deltas = _extract_deltas(spec)
    space_flag, space_val = _extract_space(spec)

    cmd = [
        sys.executable,
        "examples/claim_stability_demo.py",
        "--suite",
        _suite_name(spec),
        space_flag,
        space_val,
        "--sampling-mode",
        mode,
        "--sample-seed",
        str(sample_seed),
        "--stability-threshold",
        str(threshold),
        "--confidence-level",
        str(confidence),
        "--deltas",
        deltas,
        "--claim-pairs",
        claim_pairs,
        "--backend-engine",
        _backend_engine(spec),
        "--spec",
        str(spec_path),
        "--out-dir",
        str(args.out_dir),
    ]

    if mode == "random_k" and sample_size is not None:
        cmd.extend(["--sample-size", str(sample_size)])
    if mode == "adaptive_ci":
        if sampling.get("target_ci_width") is not None:
            cmd.extend(["--target-ci-width", str(sampling["target_ci_width"])])
        if sampling.get("max_sample_size") is not None:
            cmd.extend(["--max-sample-size", str(sampling["max_sample_size"])])
        if sampling.get("min_sample_size") is not None:
            cmd.extend(["--min-sample-size", str(sampling["min_sample_size"])])
        if sampling.get("step_size") is not None:
            cmd.extend(["--step-size", str(sampling["step_size"])])

    return cmd


def _to_csv_token_list(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return ""


def _build_multidevice_command(spec_path: Path, spec: dict[str, Any], args: argparse.Namespace) -> list[str]:
    sampling = _extract_sampling(spec)
    mode = str(sampling["mode"])
    sample_size = sampling["sample_size"]
    sample_seed = int(sampling["seed"])
    if args.seed is not None:
        sample_seed = args.seed
    threshold, confidence = _extract_decision(spec)
    deltas = _extract_deltas(spec)

    pert = spec.get("perturbations", {})
    transpile_space = "compilation_only"
    noisy_space = "sampling_only"
    if isinstance(pert, dict):
        transpile_space = str(pert.get("transpile_space", transpile_space))
        noisy_space = str(pert.get("noisy_space", noisy_space))

    multi = spec.get("multidevice", {})
    if not isinstance(multi, dict):
        multi = {}

    run_mode = str(multi.get("run", "all"))
    if args.mode:
        run_mode = args.mode

    transpile_devices = _to_csv_token_list(multi.get("transpile_devices"))
    noisy_devices = _to_csv_token_list(multi.get("noisy_devices"))
    transpile_pairs = _to_csv_token_list(multi.get("transpile_claim_pairs"))
    noisy_pairs = _to_csv_token_list(multi.get("noisy_claim_pairs"))

    if args.device:
        transpile_devices = args.device
        noisy_devices = args.device

    cmd = [
        sys.executable,
        "examples/multidevice_demo.py",
        "--run",
        run_mode,
        "--suite",
        _suite_name(spec),
        "--sampling-mode",
        mode,
        "--sample-seed",
        str(sample_seed),
        "--stability-threshold",
        str(threshold),
        "--confidence-level",
        str(confidence),
        "--deltas",
        deltas,
        "--backend-engine",
        _backend_engine(spec),
        "--transpile-space",
        transpile_space,
        "--noisy-space",
        noisy_space,
        "--spec",
        str(spec_path),
        "--out-dir",
        str(args.out_dir),
    ]

    if mode == "random_k" and sample_size is not None:
        cmd.extend(["--sample-size", str(sample_size)])
    if transpile_devices:
        cmd.extend(["--transpile-devices", transpile_devices])
    if noisy_devices:
        cmd.extend(["--noisy-devices", noisy_devices])
    if transpile_pairs:
        cmd.extend(["--transpile-claim-pairs", transpile_pairs])
    if noisy_pairs:
        cmd.extend(["--noisy-claim-pairs", noisy_pairs])

    return cmd


def _run_subprocess(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    return int(proc.returncode)


def cmd_run(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    spec = load_spec(spec_path, validate=args.validate)
    effective_spec_path = spec_path
    temp_spec_path: Path | None = None

    pipeline = _infer_pipeline(spec)
    if pipeline == "main" and (args.device or args.mode in {"transpile_only", "noisy_sim"}):
        override = deepcopy(spec)
        dp = override.setdefault("device_profile", {})
        if isinstance(dp, dict):
            dp["enabled"] = True
            dp["provider"] = "ibm_fake"
            if args.device:
                dp["name"] = args.device
            if args.mode in {"transpile_only", "noisy_sim"}:
                dp["mode"] = args.mode
        backend = override.setdefault("backend", {})
        if isinstance(backend, dict):
            backend.setdefault("engine", "basic")
            if args.mode == "noisy_sim":
                backend["noise_model"] = "from_device_profile"
            elif args.mode == "transpile_only":
                backend["noise_model"] = "none"

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(override, tmp)
            temp_spec_path = Path(tmp.name)
            effective_spec_path = temp_spec_path

    if pipeline == "multidevice":
        cmd = _build_multidevice_command(effective_spec_path, spec, args)
    else:
        cmd = _build_main_command(effective_spec_path, spec, args)

    if args.dry_run:
        print("Dry-run command:")
        print(" ".join(cmd))
        return 0

    try:
        rc = _run_subprocess(cmd)
        if rc != 0:
            return rc

        if args.report:
            json_path = Path(args.out_dir) / "claim_stability.json"
            if not json_path.exists():
                print(
                    f"Skip report generation: {json_path} not found. "
                    "(This is expected for some multidevice-only runs.)"
                )
                return 0
            report_out = Path(args.out_dir) / "stability_report.html"
            rep_cmd = [
                sys.executable,
                "-m",
                "claimstab.scripts.generate_stability_report",
                "--json",
                str(json_path),
                "--out",
                str(report_out),
            ]
            if args.with_plots:
                rep_cmd.append("--with-plots")
            return _run_subprocess(rep_cmd)

        return 0
    finally:
        if temp_spec_path and temp_spec_path.exists():
            temp_spec_path.unlink(missing_ok=True)


def cmd_report(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        "-m",
        "claimstab.scripts.generate_stability_report",
        "--json",
        args.json,
        "--out",
        args.out,
    ]
    if args.with_plots:
        cmd.append("--with-plots")
    return _run_subprocess(cmd)


def cmd_validate_spec(args: argparse.Namespace) -> int:
    try:
        spec = load_spec(args.spec, validate=False)
        validate_spec(spec)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Spec valid: {args.spec}")
    return 0


def cmd_examples(_: argparse.Namespace) -> int:
    print("Ready-to-run examples:")
    print("  claimstab run --spec specs/paper_main.yml --out-dir output/paper_main --report")
    print("  claimstab run --spec specs/paper_device.yml --out-dir output/paper_device")
    print("  claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy")
    print("  claimstab report --json output/paper_main/claim_stability.json --out output/paper_main/stability_report.html")
    print("  claimstab validate-spec --spec specs/paper_main.yml")
    print("  claimstab export-definitions --out docs/generated/definitions.md")
    print("  claimstab validate-ecosystem --root ecosystem")
    return 0


def cmd_export_definitions(args: argparse.Namespace) -> int:
    src = Path("docs/concepts/formal_definitions.md")
    out = Path(args.out)
    if not src.exists():
        print(f"Definitions template not found: {src}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    print(f"Exported definitions to: {out}")
    return 0


def cmd_validate_ecosystem(args: argparse.Namespace) -> int:
    try:
        result = validate_ecosystem(args.root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Ecosystem valid: {result.root}")
    print(f"Counts: {result.counts}")
    if result.warnings:
        print("Warnings:")
        for line in result.warnings:
            print(f"- {line}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="claimstab", description="ClaimStab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run an experiment from a spec file")
    run_p.add_argument("--spec", required=True, help="Path to YAML/JSON experiment spec")
    run_p.add_argument("--out-dir", required=True, help="Output directory")
    run_p.add_argument("--seed", type=int, default=None, help="Override sampling seed")
    run_p.add_argument("--device", default=None, help="Optional single-device override (e.g., FakeManilaV2)")
    run_p.add_argument("--mode", choices=["all", "transpile_only", "noisy_sim"], default=None)
    run_p.add_argument("--report", action="store_true", help="Generate stability_report.html when claim_stability.json exists")
    run_p.add_argument("--with-plots", action="store_true", help="Use --with-plots for report generation")
    run_p.add_argument("--validate", action="store_true", help="Validate spec against v1 schema before running")
    run_p.add_argument("--dry-run", action="store_true", help="Print resolved command without executing")
    run_p.set_defaults(func=cmd_run)

    report_p = sub.add_parser("report", help="Generate an HTML report from JSON output")
    report_p.add_argument("--json", required=True, help="Path to claim_stability.json")
    report_p.add_argument("--out", required=True, help="Output HTML path")
    report_p.add_argument("--with-plots", action="store_true")
    report_p.set_defaults(func=cmd_report)

    validate_p = sub.add_parser("validate-spec", help="Validate a spec file against schema v1")
    validate_p.add_argument("--spec", required=True, help="Path to YAML/JSON spec")
    validate_p.set_defaults(func=cmd_validate_spec)

    ex_p = sub.add_parser("examples", help="Print ready-to-run example commands")
    ex_p.set_defaults(func=cmd_examples)

    export_p = sub.add_parser("export-definitions", help="Export formal definitions scaffold markdown")
    export_p.add_argument("--out", required=True, help="Output markdown path")
    export_p.set_defaults(func=cmd_export_definitions)

    eco_p = sub.add_parser("validate-ecosystem", help="Validate ecosystem contribution metadata and references")
    eco_p.add_argument("--root", default="ecosystem", help="Ecosystem root directory")
    eco_p.set_defaults(func=cmd_validate_ecosystem)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
