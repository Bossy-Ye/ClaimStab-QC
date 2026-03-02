from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from claimstab.claims.evaluation import collect_paired_scores
from claimstab.claims.ranking import HigherIsBetter, RankingClaim, compute_rank_flip_summary
from claimstab.claims.stability import conservative_stability_decision, estimate_binomial_rate
from claimstab.devices.registry import parse_device_profile, parse_noise_model_mode, resolve_device_profile
from claimstab.methods.spec import MethodSpec
from claimstab.perturbations.sampling import SamplingPolicy, ensure_config_included, sample_configs
from claimstab.perturbations.space import CompilationPerturbation, ExecutionPerturbation, PerturbationConfig, PerturbationSpace
from claimstab.runners.matrix_runner import MatrixRunner, ScoreRow
from claimstab.runners.qiskit_aer import QiskitAerRunner
from claimstab.tasks.graphs import core_suite, large_suite, standard_suite
from claimstab.tasks.maxcut import MaxCutTask


SUITE_ALIASES = {
    "core": "core",
    "standard": "standard",
    "large": "large",
    "day1": "core",
    "day2": "standard",
    "day2_large": "large",
}

SPACE_ALIASES = {
    "baseline": "baseline",
    "compilation_only": "compilation_only",
    "sampling_only": "sampling_only",
    "combined_light": "combined_light",
    "day1_default": "baseline",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ClaimStab multi-device demo (transpile-only + noisy simulation)")
    ap.add_argument("--run", choices=["all", "transpile_only", "noisy_sim"], default="all")
    ap.add_argument("--suite", default="standard", help="Suite preset: core | standard | large.")
    ap.add_argument("--out-dir", default="output")
    ap.add_argument("--sampling-mode", choices=["full_factorial", "random_k"], default="full_factorial")
    ap.add_argument("--sample-size", type=int, default=40)
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--stability-threshold", type=float, default=0.95)
    ap.add_argument("--confidence-level", type=float, default=0.95)
    ap.add_argument("--deltas", default="0.0,0.01,0.05")
    ap.add_argument("--backend-engine", choices=["auto", "aer", "basic"], default=os.getenv("CLAIMSTAB_SIMULATOR", "auto"))
    ap.add_argument("--transpile-space", default="compilation_only")
    ap.add_argument("--noisy-space", default="sampling_only")
    ap.add_argument(
        "--transpile-devices",
        default="FakeManilaV2,FakeBrisbane,FakePrague,FakeSherbrooke,FakeKyoto,FakeTorino",
        help="Comma-separated IBM fake backend names/classes for transpile-only runs.",
    )
    ap.add_argument(
        "--noisy-devices",
        default="FakeManilaV2,FakeBrisbane",
        help="Comma-separated IBM fake backend names/classes for noisy simulation runs.",
    )
    ap.add_argument(
        "--transpile-claim-pairs",
        default="QAOA_p1>QAOA_p2",
        help="Comma-separated pairs for structural claims (lower is better).",
    )
    ap.add_argument(
        "--noisy-claim-pairs",
        default="QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline",
        help="Comma-separated pairs for objective claims (higher is better).",
    )
    ap.add_argument(
        "--spec",
        default=None,
        help="Optional YAML/JSON file. Optional blocks: device_profile, backend.noise_model. Missing blocks keep defaults.",
    )
    return ap.parse_args()


def parse_csv_tokens(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(",") if token.strip()]


def parse_deltas(raw: str) -> list[float]:
    vals = [float(t) for t in parse_csv_tokens(raw)]
    if not vals:
        raise ValueError("At least one delta must be provided.")
    return vals


def parse_claim_pairs(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for token in parse_csv_tokens(raw):
        if ">" in token:
            left, right = token.split(">", 1)
        elif ":" in token:
            left, right = token.split(":", 1)
        else:
            raise ValueError(f"Invalid claim pair token '{token}'. Use MethodA>MethodB.")
        a = left.strip()
        b = right.strip()
        if not a or not b:
            raise ValueError(f"Invalid claim pair token '{token}'.")
        if a == b:
            raise ValueError("Claim pair must compare different methods.")
        pairs.append((a, b))
    if not pairs:
        raise ValueError("At least one claim pair is required.")
    return pairs


def canonical_suite_name(name: str) -> str:
    key = name.strip()
    canonical = SUITE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SUITE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown suite '{name}'. Use one of: {valid}.")
    return canonical


def canonical_space_name(name: str) -> str:
    key = name.strip()
    canonical = SPACE_ALIASES.get(key)
    if canonical is None:
        valid = ", ".join(sorted({k for k in SPACE_ALIASES if not k.startswith("day")}))
        raise ValueError(f"Unknown space '{name}'. Use one of: {valid}.")
    return canonical


def make_space(name: str) -> PerturbationSpace:
    if name == "baseline":
        return PerturbationSpace.conf_level_default()
    if name == "compilation_only":
        return PerturbationSpace.compilation_only()
    if name == "sampling_only":
        return PerturbationSpace.sampling_only()
    if name == "combined_light":
        return PerturbationSpace.combined_light()
    raise ValueError(f"Unknown space '{name}'")


def get_suite(name: str):
    if name == "core":
        return core_suite()
    if name == "standard":
        return standard_suite()
    if name == "large":
        return large_suite()
    raise ValueError(f"Unknown suite '{name}'")


def build_baseline(space: PerturbationSpace):
    first = next(space.iter_configs())
    baseline_pc = PerturbationConfig(
        compilation=CompilationPerturbation(
            seed_transpiler=first.compilation.seed_transpiler,
            optimization_level=first.compilation.optimization_level,
            layout_method=first.compilation.layout_method,
        ),
        execution=ExecutionPerturbation(
            shots=first.execution.shots,
            seed_simulator=first.execution.seed_simulator,
        ),
    )
    baseline_key = (
        first.compilation.seed_transpiler,
        first.compilation.optimization_level,
        first.compilation.layout_method,
        first.execution.shots,
        first.execution.seed_simulator,
    )
    baseline_dict = {
        "seed_transpiler": first.compilation.seed_transpiler,
        "optimization_level": first.compilation.optimization_level,
        "layout_method": first.compilation.layout_method,
        "shots": first.execution.shots,
        "seed_simulator": first.execution.seed_simulator,
    }
    return baseline_pc, baseline_key, baseline_dict


def evaluate_rows_for_claim(
    *,
    rows_by_graph: dict[str, list[ScoreRow]],
    method_a: str,
    method_b: str,
    deltas: list[float],
    baseline_key,
    direction: HigherIsBetter,
    stability_threshold: float,
    confidence_level: float,
) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    per_graph: dict[str, dict[str, object]] = {}
    agg_stability_successes: dict[float, int] = defaultdict(int)
    agg_stability_total: dict[float, int] = defaultdict(int)
    agg_holds_successes: dict[float, int] = defaultdict(int)
    agg_holds_total: dict[float, int] = defaultdict(int)
    decisions_per_delta: dict[float, list[str]] = defaultdict(list)
    flip_rates_per_delta: dict[float, list[float]] = defaultdict(list)

    for graph_id, rows in rows_by_graph.items():
        paired = collect_paired_scores(rows, method_a, method_b)
        if baseline_key not in paired:
            continue
        baseline_a, baseline_b = paired[baseline_key]
        perturbed = [v for k, v in paired.items() if k != baseline_key]

        graph_delta = []
        for delta in deltas:
            claim = RankingClaim(method_a=method_a, method_b=method_b, delta=delta, direction=direction)
            summary = compute_rank_flip_summary(
                claim=claim,
                baseline_score_a=baseline_a,
                baseline_score_b=baseline_b,
                perturbed_scores=perturbed,
            )
            stable_successes = summary.total - summary.flips
            stability_est = estimate_binomial_rate(stable_successes, summary.total, confidence=confidence_level)
            decision = conservative_stability_decision(stability_est, stability_threshold=stability_threshold).value
            holds_successes = sum(1 for pair in paired.values() if claim.holds(*pair))

            agg_stability_successes[delta] += stable_successes
            agg_stability_total[delta] += summary.total
            agg_holds_successes[delta] += holds_successes
            agg_holds_total[delta] += len(paired)
            decisions_per_delta[delta].append(decision)
            flip_rates_per_delta[delta].append(summary.flip_rate)

            graph_delta.append(
                {
                    "delta": delta,
                    "total": summary.total,
                    "flips": summary.flips,
                    "flip_rate": summary.flip_rate,
                    "stability_hat": stability_est.rate,
                    "stability_ci_low": stability_est.ci_low,
                    "stability_ci_high": stability_est.ci_high,
                    "decision": decision,
                    "claim_holds_count": holds_successes,
                    "claim_total_count": len(paired),
                    "claim_holds_rate": (holds_successes / len(paired)) if paired else 0.0,
                }
            )

        per_graph[graph_id] = {
            "sampled_configurations": len(paired),
            "delta_sweep": graph_delta,
        }

    overall = []
    for delta in deltas:
        stability_est = estimate_binomial_rate(
            agg_stability_successes[delta],
            agg_stability_total[delta],
            confidence=confidence_level,
        )
        holds_est = estimate_binomial_rate(
            agg_holds_successes[delta],
            agg_holds_total[delta],
            confidence=confidence_level,
        )
        overall.append(
            {
                "delta": delta,
                "n_instances": len(per_graph),
                "n_claim_evals": agg_stability_total[delta],
                "flip_rate_mean": (
                    sum(flip_rates_per_delta[delta]) / len(flip_rates_per_delta[delta])
                    if flip_rates_per_delta[delta]
                    else 0.0
                ),
                "flip_rate_max": max(flip_rates_per_delta[delta]) if flip_rates_per_delta[delta] else 0.0,
                "flip_rate_min": min(flip_rates_per_delta[delta]) if flip_rates_per_delta[delta] else 0.0,
                "holds_rate_mean": holds_est.rate,
                "holds_rate_ci_low": holds_est.ci_low,
                "holds_rate_ci_high": holds_est.ci_high,
                "stability_hat": stability_est.rate,
                "stability_ci_low": stability_est.ci_low,
                "stability_ci_high": stability_est.ci_high,
                "decision": conservative_stability_decision(
                    stability_est,
                    stability_threshold=stability_threshold,
                ).value,
                "decision_counts": {
                    "stable": sum(1 for d in decisions_per_delta[delta] if d == "stable"),
                    "unstable": sum(1 for d in decisions_per_delta[delta] if d == "unstable"),
                    "inconclusive": sum(1 for d in decisions_per_delta[delta] if d == "inconclusive"),
                },
            }
        )

    return per_graph, overall


def write_rows_csv(rows: Iterable[ScoreRow], out_csv: Path) -> None:
    fields = [
        "instance_id",
        "seed_transpiler",
        "optimization_level",
        "layout_method",
        "seed_simulator",
        "shots",
        "method",
        "score",
        "transpiled_depth",
        "transpiled_size",
        "device_provider",
        "device_name",
        "device_mode",
        "device_snapshot_fingerprint",
        "circuit_depth",
        "two_qubit_count",
        "swap_count",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            w.writerow(
                [
                    r.instance_id,
                    r.seed_transpiler,
                    r.optimization_level,
                    r.layout_method,
                    r.seed_simulator,
                    r.shots,
                    r.method,
                    r.score,
                    r.transpiled_depth,
                    r.transpiled_size,
                    r.device_provider,
                    r.device_name,
                    r.device_mode,
                    r.device_snapshot_fingerprint,
                    r.circuit_depth,
                    r.two_qubit_count,
                    r.swap_count,
                ]
            )


def try_load_spec(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("YAML spec parsing requires pyyaml. Install with: pip install pyyaml") from exc
    return yaml.safe_load(text) or {}


def main() -> None:
    args = parse_args()
    deltas = parse_deltas(args.deltas)
    suite_name = canonical_suite_name(args.suite)
    transpile_space = canonical_space_name(args.transpile_space)
    noisy_space = canonical_space_name(args.noisy_space)
    suite = get_suite(suite_name)
    spec_payload = try_load_spec(args.spec)

    methods = [
        MethodSpec(name="QAOA_p1", kind="qaoa", p=1),
        MethodSpec(name="QAOA_p2", kind="qaoa", p=2),
        MethodSpec(name="RandomBaseline", kind="random"),
    ]
    method_names = {m.name for m in methods}

    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    sampling_policy = SamplingPolicy(
        mode=args.sampling_mode,
        sample_size=args.sample_size if args.sampling_mode == "random_k" else None,
        seed=args.sample_seed,
    )

    global_device_summary: list[dict[str, object]] = []

    def write_skipped_batch_summary(*, batch_mode: str, requested_devices: list[str], reason: str) -> None:
        batch_dir = out_root / batch_mode
        batch_dir.mkdir(parents=True, exist_ok=True)
        summary_payload = {
            "meta": {
                "suite": suite_name,
                "batch_mode": batch_mode,
                "generated_by": "examples/multidevice_demo.py",
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
            },
            "batch": {
                "mode": batch_mode,
                "devices_requested": requested_devices,
                "devices_completed": [],
                "devices_skipped": [{"device_name": d, "reason": reason} for d in requested_devices],
            },
            "experiments": [],
            "device_summary": [],
            "comparative": {"space_claim_delta": []},
        }
        out_json = batch_dir / f"{batch_mode}_summary.json"
        out_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        out_csv = batch_dir / f"{batch_mode}_summary.csv"
        out_csv.write_text("", encoding="utf-8")
        print("[WARN]", reason)
        print("Wrote:")
        print(" ", out_json.resolve())
        print(" ", out_csv.resolve())

    def run_batch(*, batch_mode: str, device_names: list[str], space_name: str, metric_names: list[str], claim_pairs: list[tuple[str, str]], direction: HigherIsBetter, noise_model_mode: str):
        batch_dir = out_root / batch_mode
        batch_dir.mkdir(parents=True, exist_ok=True)
        batch_experiments: list[dict[str, object]] = []
        combined_rows: list[dict[str, object]] = []
        skipped: list[dict[str, str]] = []

        space = make_space(space_name)
        baseline_pc, baseline_key, baseline_dict = build_baseline(space)
        sampled_configs = ensure_config_included(sample_configs(space, sampling_policy), baseline_pc)

        for device_name in device_names:
            profile_dict = spec_payload.get("device_profile", {}) if isinstance(spec_payload, dict) else {}
            profile_dict = dict(profile_dict)
            profile_dict.update(
                {
                    "enabled": True,
                    "provider": profile_dict.get("provider", "ibm_fake"),
                    "name": device_name,
                    "mode": batch_mode,
                }
            )
            profile = parse_device_profile(profile_dict)
            try:
                resolved = resolve_device_profile(profile)
            except Exception as exc:
                skipped.append({"device_name": device_name, "reason": str(exc)})
                continue

            device_num_qubits_raw = getattr(resolved.backend, "num_qubits", None) if resolved.backend is not None else None
            device_num_qubits = int(device_num_qubits_raw) if device_num_qubits_raw is not None else None
            compatible_suite = []
            skipped_instances: list[dict[str, object]] = []
            for inst in suite:
                graph = getattr(inst, "payload", None)
                graph_qubits = getattr(graph, "num_nodes", None)
                if device_num_qubits is not None and graph_qubits is not None and int(graph_qubits) > device_num_qubits:
                    skipped_instances.append(
                        {
                            "instance_id": getattr(inst, "instance_id", "unknown"),
                            "required_qubits": int(graph_qubits),
                            "device_qubits": device_num_qubits,
                        }
                    )
                    continue
                compatible_suite.append(inst)

            if not compatible_suite:
                skipped.append(
                    {
                        "device_name": device_name,
                        "reason": (
                            f"No compatible instances for this device "
                            f"(device_qubits={device_num_qubits}, suite={suite_name})."
                        ),
                    }
                )
                continue

            runner = MatrixRunner(backend=QiskitAerRunner(engine=args.backend_engine))
            for metric_name in metric_names:
                rows_by_graph: dict[str, list[ScoreRow]] = {}
                all_rows: list[ScoreRow] = []
                for inst in compatible_suite:
                    task = MaxCutTask(instance=inst)
                    rows = runner.run(
                        task=task,
                        methods=methods,
                        space=space,
                        configs=sampled_configs,
                        coupling_map=None,
                        metric_name=metric_name,
                        device_profile=resolved.profile,
                        device_backend=resolved.backend,
                        noise_model_mode=noise_model_mode,
                        device_snapshot_fingerprint=resolved.snapshot_fingerprint,
                        device_snapshot_summary=resolved.snapshot,
                    )
                    rows_by_graph[task.graph.graph_id] = rows
                    all_rows.extend(rows)

                csv_name = f"{batch_mode}_{device_name}_{metric_name}.csv"
                write_rows_csv(all_rows, batch_dir / csv_name)

                for method_a, method_b in claim_pairs:
                    if method_a not in method_names or method_b not in method_names:
                        continue
                    per_graph, overall = evaluate_rows_for_claim(
                        rows_by_graph=rows_by_graph,
                        method_a=method_a,
                        method_b=method_b,
                        deltas=deltas,
                        baseline_key=baseline_key,
                        direction=direction,
                        stability_threshold=args.stability_threshold,
                        confidence_level=args.confidence_level,
                    )
                    exp = {
                        "experiment_id": f"{batch_mode}:{device_name}:{metric_name}:{method_a}>{method_b}",
                        "claim": {
                            "type": "ranking",
                            "metric_name": metric_name,
                            "direction": direction.value,
                            "method_a": method_a,
                            "method_b": method_b,
                            "deltas": deltas,
                        },
                        "baseline": baseline_dict,
                        "sampling": {
                            "suite": suite_name,
                            "space_preset": space_name,
                            "mode": sampling_policy.mode,
                            "sample_size": sampling_policy.sample_size,
                            "seed": sampling_policy.seed,
                            "sampled_configurations_with_baseline": len(sampled_configs),
                            "perturbation_space_size": space.size(),
                        },
                        "backend": {
                            "engine": args.backend_engine,
                            "noise_model": noise_model_mode,
                        },
                        "device_profile": {
                            "enabled": resolved.profile.enabled,
                            "provider": resolved.profile.provider,
                            "name": resolved.profile.name,
                            "mode": resolved.profile.mode,
                            "snapshot_fingerprint": resolved.snapshot_fingerprint,
                            "snapshot": resolved.snapshot,
                        },
                        "per_graph": per_graph,
                        "overall": {
                            "graphs": len(per_graph),
                            "delta_sweep": overall,
                        },
                    }
                    batch_experiments.append(exp)
                    for row in overall:
                        summary_row = {
                            "batch_mode": batch_mode,
                            "device_name": device_name,
                            "metric_name": metric_name,
                            "claim_pair": f"{method_a}>{method_b}",
                            **row,
                        }
                        combined_rows.append(summary_row)
                        global_device_summary.append(summary_row)

            device_json = batch_dir / f"{batch_mode}_{device_name}.json"
            device_payload = {
                "meta": {
                    "suite": suite_name,
                    "batch_mode": batch_mode,
                    "device_name": device_name,
                    "generated_by": "examples/multidevice_demo.py",
                    "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                },
                "device_compatibility": {
                    "device_qubits": device_num_qubits,
                    "included_instances": [getattr(inst, "instance_id", "unknown") for inst in compatible_suite],
                    "skipped_instances": skipped_instances,
                },
                "experiments": [e for e in batch_experiments if f":{device_name}:" in str(e["experiment_id"])],
            }
            device_json.write_text(json.dumps(device_payload, indent=2), encoding="utf-8")

        summary_payload = {
            "meta": {
                "suite": suite_name,
                "batch_mode": batch_mode,
                "generated_by": "examples/multidevice_demo.py",
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
            },
            "batch": {
                "mode": batch_mode,
                "devices_requested": device_names,
                "devices_completed": sorted({row["device_name"] for row in combined_rows}),
                "devices_skipped": skipped,
            },
            "experiments": batch_experiments,
            "device_summary": combined_rows,
            "comparative": {
                "space_claim_delta": combined_rows,
            },
        }
        out_json = batch_dir / f"{batch_mode}_summary.json"
        out_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        out_csv = batch_dir / f"{batch_mode}_summary.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            if combined_rows:
                cols = list(combined_rows[0].keys())
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for row in combined_rows:
                    w.writerow(row)

        print("Wrote:")
        print(" ", out_json.resolve())
        print(" ", out_csv.resolve())

    run_transpile = args.run in {"all", "transpile_only"}
    run_noisy = args.run in {"all", "noisy_sim"}

    if run_transpile:
        run_batch(
            batch_mode="transpile_only",
            device_names=parse_csv_tokens(args.transpile_devices),
            space_name=transpile_space,
            metric_names=["circuit_depth", "two_qubit_count"],
            claim_pairs=parse_claim_pairs(args.transpile_claim_pairs),
            direction=HigherIsBetter.NO,
            noise_model_mode="none",
        )

    if run_noisy:
        noisy_devices = parse_csv_tokens(args.noisy_devices)
        if sys.version_info >= (3, 13):
            write_skipped_batch_summary(
                batch_mode="noisy_sim",
                requested_devices=noisy_devices,
                reason="noisy_sim skipped on Python 3.13 due known native qiskit-aer runtime instability in this environment.",
            )
        else:
            backend_cfg = spec_payload.get("backend", {}) if isinstance(spec_payload, dict) else {}
            noise_model_mode = parse_noise_model_mode(backend_cfg)
            run_batch(
                batch_mode="noisy_sim",
                device_names=noisy_devices,
                space_name=noisy_space,
                metric_names=["objective"],
                claim_pairs=parse_claim_pairs(args.noisy_claim_pairs),
                direction=HigherIsBetter.YES,
                noise_model_mode=noise_model_mode,
            )

    if global_device_summary:
        final_summary = {
            "meta": {
                "suite": suite_name,
                "generated_by": "examples/multidevice_demo.py",
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
            },
            "device_summary": global_device_summary,
            "comparative": {"space_claim_delta": global_device_summary},
        }
        final_json = out_root / "combined_summary.json"
        final_json.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")
        print(" ", final_json.resolve())


if __name__ == "__main__":
    main()
