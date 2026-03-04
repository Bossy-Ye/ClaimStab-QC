from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

from claimstab.atlas import build_dataset_registry_markdown, compare_claim_outputs, publish_result, validate_atlas
from claimstab.spec import load_spec, validate_spec


def _slugify_name(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        raise ValueError("Name must include at least one alphanumeric character.")
    if not value[0].isalpha():
        value = f"task_{value}"
    return value


def _camel_from_slug(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("_") if part) + "Task"


def _module_path_for_python_file(path: Path) -> str:
    stem = path.with_suffix("")
    try:
        rel = stem.resolve().relative_to(Path.cwd().resolve())
        return ".".join(rel.parts)
    except Exception:
        return stem.name


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

    return ""


def _has_explicit_ranking_claims(spec: dict[str, Any]) -> bool:
    claims = spec.get("claims")
    if isinstance(claims, list):
        return any(isinstance(entry, dict) and str(entry.get("type", "ranking")).strip().lower() == "ranking" for entry in claims)
    if isinstance(claims, dict):
        return isinstance(claims.get("ranking"), dict)
    return False


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
    has_explicit_ranking = _has_explicit_ranking_claims(spec)
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
        "--backend-engine",
        _backend_engine(spec),
        "--spec",
        str(spec_path),
        "--out-dir",
        str(args.out_dir),
    ]
    if not has_explicit_ranking:
        cmd.extend(["--deltas", deltas])
    if claim_pairs and not has_explicit_ranking:
        cmd.extend(["--claim-pairs", claim_pairs])

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

    if args.cache_db:
        cmd.extend(["--cache-db", str(args.cache_db)])
    if args.events_out:
        cmd.extend(["--events-out", str(args.events_out)])
    if args.trace_out:
        cmd.extend(["--trace-out", str(args.trace_out)])
    if args.replay_trace:
        cmd.extend(["--replay-trace", str(args.replay_trace)])

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
    if args.cache_db:
        cmd.extend(["--cache-db", str(args.cache_db)])
    if args.events_out:
        cmd.extend(["--events-out", str(args.events_out)])
    if args.trace_out:
        cmd.extend(["--trace-out", str(args.trace_out)])
    if args.replay_trace:
        cmd.extend(["--replay-trace", str(args.replay_trace)])

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
    print("  claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo")
    print("  claimstab run --spec specs/paper_main.yml --out-dir output/paper_main --report")
    print("  claimstab run --spec specs/paper_structural.yml --out-dir output/paper_structural --report")
    print("  claimstab run --spec specs/paper_device.yml --out-dir output/paper_device")
    print("  claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy")
    print("  claimstab run --spec specs/atlas_bv_demo.yml --out-dir output/atlas_bv_demo --report")
    print("  PYTHONPATH=. ./venv/bin/python examples/atlas_bv_workflow.py --contributor your_name")
    print("  claimstab report --json output/paper_main/claim_stability.json --out output/paper_main/stability_report.html")
    print("  claimstab validate-spec --spec specs/paper_main.yml")
    print("  claimstab export-definitions --out docs/generated/definitions.md")
    print("  claimstab publish-result --run-dir output/paper_main --atlas-root atlas --contributor your_name")
    print("  claimstab validate-atlas --atlas-root atlas")
    print("  claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md")
    print("  make reproduce-paper")
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


def cmd_init_external_task(args: argparse.Namespace) -> int:
    try:
        slug = _slugify_name(args.name)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else Path("examples") / f"{slug}_demo"
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        print(
            f"Refusing to overwrite non-empty directory: {out_dir}. "
            "Use --force or choose a new --out-dir.",
            file=sys.stderr,
        )
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    class_name = args.class_name.strip() if isinstance(args.class_name, str) and args.class_name.strip() else _camel_from_slug(slug)
    task_file = out_dir / f"{slug}_task.py"
    spec_file = out_dir / f"spec_{slug}.yml"
    module_path = _module_path_for_python_file(task_file)

    task_source = f'''from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qiskit import QuantumCircuit

from claimstab.methods.spec import MethodSpec
from claimstab.tasks.base import BuiltWorkflow
from claimstab.tasks.instances import ProblemInstance


@dataclass(frozen=True)
class {class_name}Payload:
    num_qubits: int


class {class_name}:
    """External task plugin starter generated by ClaimStab."""

    name = "{slug}"

    def __init__(self, num_qubits: int = 6, num_instances: int = 3) -> None:
        self.num_qubits = int(num_qubits)
        self.num_instances = int(num_instances)

    def instances(self, suite: str) -> list[ProblemInstance]:
        return [
            ProblemInstance(
                instance_id=f"{slug}_{{suite}}_{{i}}",
                payload={class_name}Payload(num_qubits=self.num_qubits),
            )
            for i in range(self.num_instances)
        ]

    def build(self, instance: ProblemInstance, method: MethodSpec) -> BuiltWorkflow:
        payload = instance.payload
        n = int(getattr(payload, "num_qubits", self.num_qubits))
        qc = QuantumCircuit(n)

        if method.kind == "method_a":
            qc.h(range(n))
        elif method.kind == "method_b":
            pass
        else:
            raise ValueError(f"Unsupported method kind: {{method.kind}}")

        qc.measure_all()

        def metric_fn(counts: dict[str, int]) -> float:
            total = sum(counts.values())
            if total == 0:
                return 0.0
            ones = 0.0
            for bitstring, c in counts.items():
                ones += (c / total) * bitstring.count("1")
            return ones / n

        return BuiltWorkflow(circuit=qc, metric_fn=metric_fn)
'''

    spec_source = f'''spec_version: 1
pipeline: main
meta:
  name: {slug}_demo
  description: External task starter generated by claimstab init-external-task

task:
  kind: external
  entrypoint: {module_path}:{class_name}
  suite: toy
  params:
    num_qubits: 6
    num_instances: 3

methods:
  - name: MethodA
    kind: method_a
  - name: MethodB
    kind: method_b

claims:
  - type: ranking
    method_a: MethodA
    method_b: MethodB
    deltas: [0.0, 0.05]

perturbations:
  presets: [sampling_only]

sampling:
  mode: random_k
  sample_size: 12
  seed: 7
  include_baseline: true

decision_rule:
  threshold: 0.95
  confidence_level: 0.95

backend:
  engine: basic
  noise_model: none
'''

    task_file.write_text(task_source, encoding="utf-8")
    spec_file.write_text(spec_source, encoding="utf-8")

    print(f"Generated starter in: {out_dir}")
    print(f"- Task plugin: {task_file}")
    print(f"- Spec: {spec_file}")
    print("Next steps:")
    print(f"1) claimstab validate-spec --spec {spec_file}")
    print(f"2) claimstab run --spec {spec_file} --out-dir output/{slug} --report")
    print(f"3) claimstab publish-result --run-dir output/{slug} --atlas-root atlas --contributor your_name")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="claimstab", description="ClaimStab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init-external-task", help="Generate a runnable external task plugin starter")
    init_p.add_argument("--name", required=True, help="Task name (used for class/module/spec naming)")
    init_p.add_argument("--out-dir", default=None, help="Output directory (default: examples/<name>_demo)")
    init_p.add_argument("--class-name", default=None, help="Optional explicit class name")
    init_p.add_argument("--force", action="store_true", help="Allow writing into an existing non-empty directory")
    init_p.set_defaults(func=cmd_init_external_task)

    run_p = sub.add_parser("run", help="Run an experiment from a spec file")
    run_p.add_argument("--spec", required=True, help="Path to YAML/JSON experiment spec")
    run_p.add_argument("--out-dir", required=True, help="Output directory")
    run_p.add_argument("--seed", type=int, default=None, help="Override sampling seed")
    run_p.add_argument("--device", default=None, help="Optional single-device override (e.g., FakeManilaV2)")
    run_p.add_argument("--mode", choices=["all", "transpile_only", "noisy_sim"], default=None)
    run_p.add_argument("--report", action="store_true", help="Generate stability_report.html when claim_stability.json exists")
    run_p.add_argument("--with-plots", action="store_true", help="Use --with-plots for report generation")
    run_p.add_argument("--validate", action="store_true", help="Validate spec against v1 schema before running")
    run_p.add_argument("--cache-db", default=None, help="Optional sqlite cache path for matrix cell reuse")
    run_p.add_argument("--events-out", default=None, help="Optional JSONL output path for execution events")
    run_p.add_argument("--trace-out", default=None, help="Optional JSONL output path for trace records")
    run_p.add_argument("--replay-trace", default=None, help="Replay mode: reuse an existing trace JSONL instead of executing")
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

    publish_p = sub.add_parser("publish-result", help="Publish a run directory into the ClaimAtlas dataset")
    publish_p.add_argument("--run-dir", required=True, help="Directory containing claim_stability.json")
    publish_p.add_argument("--atlas-root", default="atlas", help="Atlas dataset root directory")
    publish_p.add_argument("--contributor", default="anonymous", help="Contributor identifier")
    publish_p.add_argument("--title", default=None, help="Optional submission title")
    publish_p.add_argument("--submission-id", default=None, help="Optional stable submission id")
    publish_p.set_defaults(func=cmd_publish_result)

    val_atlas_p = sub.add_parser("validate-atlas", help="Validate ClaimAtlas index and artifact references")
    val_atlas_p.add_argument("--atlas-root", default="atlas", help="Atlas dataset root directory")
    val_atlas_p.set_defaults(func=cmd_validate_atlas)

    exp_data_p = sub.add_parser("export-dataset-registry", help="Generate docs markdown page from atlas submissions")
    exp_data_p.add_argument("--atlas-root", default="atlas", help="Atlas dataset root directory")
    exp_data_p.add_argument("--out", default="docs/dataset_registry.md", help="Output markdown path")
    exp_data_p.add_argument(
        "--repo-url",
        default="https://github.com/Bossy-Ye/ClaimStab-QC",
        help="Repository URL used for artifact links",
    )
    exp_data_p.set_defaults(func=cmd_export_dataset_registry)

    compare_p = sub.add_parser("atlas-compare", help="Compare two claim_stability outputs or run directories")
    compare_p.add_argument("--left", required=True, help="Left run directory or claim_stability.json")
    compare_p.add_argument("--right", required=True, help="Right run directory or claim_stability.json")
    compare_p.add_argument("--out", default=None, help="Optional JSON output path for full diff payload")
    compare_p.set_defaults(func=cmd_atlas_compare)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
