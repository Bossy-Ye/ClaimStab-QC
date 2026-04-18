from __future__ import annotations

import argparse
import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from claimstab.pipelines.claim_stability_app import (
    _as_bool,
    canonical_space_name,
    canonical_suite_name,
    has_explicit_claims,
    parse_claim_pairs,
    parse_csv_tokens,
    parse_decision_claims_from_spec,
    parse_deltas,
    parse_distribution_claims_from_spec,
    parse_ranking_claims_from_spec,
    try_load_spec,
)
from claimstab.pipelines.main_aggregate_emit import build_main_outputs, write_main_outputs
from claimstab.pipelines.main_execution import execute_main_plan
from claimstab.pipelines.planning import resolve_main_plan
from claimstab.runners.qiskit_iqm import QiskitIQMRunner


def _build_namespace(args: argparse.Namespace, spec_payload: dict) -> Namespace:
    sampling = spec_payload.get("sampling", {}) if isinstance(spec_payload, dict) else {}
    decision_rule = spec_payload.get("decision_rule", {}) if isinstance(spec_payload, dict) else {}
    perturbations = spec_payload.get("perturbations", {}) if isinstance(spec_payload, dict) else {}
    presets = perturbations.get("presets", []) if isinstance(perturbations, dict) else []
    if isinstance(presets, str):
        presets = [presets]
    if not presets:
        presets = ["compilation_only_exact"]

    return Namespace(
        suite=str(spec_payload.get("suite", "core")),
        task=None,
        space_preset=str(presets[0]),
        space_presets=",".join(str(p) for p in presets),
        sampling_mode=str(sampling.get("mode", "full_factorial")),
        sample_size=int(sampling.get("sample_size", 40) or 40),
        sample_seed=int(sampling.get("seed", 0) or 0),
        target_ci_width=float(sampling.get("target_ci_width", 0.02) or 0.02),
        max_sample_size=int(sampling.get("max_sample_size", 96) or 96),
        min_sample_size=int(sampling.get("min_sample_size", 16) or 16),
        step_size=int(sampling.get("step_size", 8) or 8),
        stability_threshold=float(decision_rule.get("threshold", 0.95) or 0.95),
        confidence_level=float(decision_rule.get("confidence_level", 0.95) or 0.95),
        deltas="0.0,0.01,0.05",
        ranking_metric="objective",
        lower_is_better=False,
        method_a="QAOA_p2",
        method_b="RandomBaseline",
        claim_pairs="",
        top_k_unstable=5,
        backend_engine="iqm_hardware",
        spot_check_noise=False,
        one_qubit_error=0.001,
        two_qubit_error=0.01,
        out_dir=str(args.out_dir),
        spec=str(args.spec),
        cache_db=None,
        events_out=None,
        trace_out=None,
        replay_trace=None,
        use_operator_shim=False,
        debug_attribution=bool(args.debug_attribution),
    )


def _mutate_payload_for_hardware(bundle, runner: QiskitIQMRunner, args: argparse.Namespace) -> None:
    payload = bundle.claim_stability_payload
    payload["device_profile"] = {
        "enabled": True,
        "provider": "iqm",
        "name": runner.backend_name or runner.quantum_computer,
        "mode": runner.device_mode,
        "snapshot_fingerprint": runner.snapshot_fingerprint,
        "snapshot": runner.snapshot,
    }
    payload["hardware_execution"] = {
        "provider": "iqm",
        "server_url": runner.server_url,
        "quantum_computer": runner.quantum_computer,
        "backend_name": runner.backend_name,
        "calibration_set_id": runner.calibration_set_id,
        "execution_mode": runner.device_mode,
        "script": "paper/experiments/scripts/run_hardware_slice_iqm.py",
        "spec": str(args.spec),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Run a minimal ClaimStab hardware slice on IQM/VTT hardware or facade backends."
    )
    ap.add_argument("--spec", help="Path to a hardware-slice spec YAML.")
    ap.add_argument("--out-dir", help="Output directory for the hardware run.")
    ap.add_argument("--server-url", default=None, help="IQM server URL. Falls back to CLAIMSTAB_IQM_SERVER_URL.")
    ap.add_argument(
        "--quantum-computer",
        default=None,
        help="IQM quantum computer name. Falls back to CLAIMSTAB_IQM_QUANTUM_COMPUTER.",
    )
    ap.add_argument(
        "--backend-name",
        default=None,
        help="Optional IQM backend name, e.g. facade_aphrodite. Falls back to CLAIMSTAB_IQM_BACKEND.",
    )
    ap.add_argument("--token", default=None, help="Optional explicit IQM token. Prefer env instead.")
    ap.add_argument("--token-env", default="IQM_TOKEN", help="Environment variable to read the token from.")
    ap.add_argument("--calibration-set-id", default=None, help="Optional calibration set id.")
    ap.add_argument("--list-backends", action="store_true", help="List the default backend and facade options.")
    ap.add_argument(
        "--include-facades",
        action="store_true",
        help="Include known facade backends such as facade_aphrodite in --list-backends.",
    )
    ap.add_argument("--debug-attribution", action="store_true")
    return ap


def main() -> int:
    args = build_parser().parse_args()

    if args.list_backends:
        rows = QiskitIQMRunner.available_backends(
            server_url=args.server_url,
            quantum_computer=args.quantum_computer,
            token=args.token,
            token_env=args.token_env,
            calibration_set_id=args.calibration_set_id,
            include_facades=args.include_facades,
        )
        print(json.dumps(rows, indent=2))
        return 0

    if not args.spec or not args.out_dir:
        raise SystemExit("--spec and --out-dir are required unless --list-backends is used.")

    spec_path = Path(args.spec)
    spec_payload = try_load_spec(str(spec_path))
    run_args = _build_namespace(args, spec_payload)

    plan = resolve_main_plan(
        run_args,
        parse_deltas_fn=parse_deltas,
        parse_csv_tokens_fn=parse_csv_tokens,
        canonical_space_name_fn=canonical_space_name,
        canonical_suite_name_fn=canonical_suite_name,
        try_load_spec_fn=try_load_spec,
        parse_claim_pairs_fn=parse_claim_pairs,
        parse_ranking_claims_from_spec_fn=parse_ranking_claims_from_spec,
        parse_decision_claims_from_spec_fn=parse_decision_claims_from_spec,
        parse_distribution_claims_from_spec_fn=parse_distribution_claims_from_spec,
        has_explicit_claims_fn=has_explicit_claims,
        as_bool_fn=_as_bool,
    )

    runner_kwargs = {
        "server_url": args.server_url,
        "quantum_computer": args.quantum_computer,
        "backend_name": args.backend_name,
        "token": args.token,
        "token_env": args.token_env,
        "calibration_set_id": args.calibration_set_id,
    }

    runner_instance: QiskitIQMRunner | None = None

    def _runner_factory(*_args, **_kwargs):
        nonlocal runner_instance
        if runner_instance is None:
            runner_instance = QiskitIQMRunner(**runner_kwargs)
        return runner_instance

    # Reuse the main ClaimStab path unchanged; only the execution backend is swapped.
    with patch("claimstab.pipelines.main_execution.QiskitAerRunner", new=_runner_factory):
        execution_result = execute_main_plan(plan)
    bundle = build_main_outputs(plan, execution_result)
    if runner_instance is None:
        runner_instance = QiskitIQMRunner(**runner_kwargs)
    runner = runner_instance
    _mutate_payload_for_hardware(bundle, runner, args)
    write_main_outputs(bundle, plan, execution_result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
