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
from claimstab.runners.qiskit_ibm_runtime import QiskitIBMRuntimeRunner


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
        backend_engine="ibm_runtime",
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


def _mutate_payload_for_hardware(bundle, runner: QiskitIBMRuntimeRunner, args: argparse.Namespace) -> None:
    payload = bundle.claim_stability_payload
    payload["device_profile"] = {
        "enabled": True,
        "provider": "ibm_runtime",
        "name": runner.backend_name,
        "mode": "hardware",
        "snapshot_fingerprint": runner.snapshot_fingerprint,
        "snapshot": runner.snapshot,
    }
    payload.setdefault("meta", {}).setdefault("hardware_execution", {})
    payload["meta"]["hardware_execution"] = {
        "provider": "ibm_runtime",
        "backend_name": runner.backend_name,
        "channel": runner.channel,
        "instance": runner.instance,
        "list_backends_command_ready": True,
        "script": "paper/experiments/scripts/run_real_hardware_slice_v1.py",
    }
    for exp in payload.get("experiments", []):
        if isinstance(exp, dict):
            exp.setdefault("backend", {})
            exp["backend"]["engine"] = "ibm_runtime"
            exp["backend"]["noise_model"] = "none"
            exp["backend"]["device_mode"] = "hardware"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run a small ClaimStab slice on real IBM hardware.")
    ap.add_argument("--spec", help="Path to a hardware-slice spec YAML.")
    ap.add_argument("--out-dir", help="Output directory for the hardware run.")
    ap.add_argument("--backend-name", default=None, help="IBM backend name. Falls back to CLAIMSTAB_IBM_BACKEND.")
    ap.add_argument("--channel", default=None, help="IBM Runtime channel. Default: CLAIMSTAB_IBM_CHANNEL or ibm_quantum_platform.")
    ap.add_argument("--instance", default=None, help="IBM Runtime instance / CRN.")
    ap.add_argument("--token", default=None, help="Optional explicit IBM token. Prefer env instead.")
    ap.add_argument("--token-env", default="IBM_QUANTUM_TOKEN", help="Environment variable to read the token from.")
    ap.add_argument("--account-name", default=None, help="Optional saved IBM account name.")
    ap.add_argument("--list-backends", action="store_true", help="List visible IBM backends and exit.")
    ap.add_argument("--min-num-qubits", type=int, default=None, help="Optional filter for --list-backends.")
    ap.add_argument("--debug-attribution", action="store_true")
    return ap


def main() -> int:
    args = build_parser().parse_args()

    if args.list_backends:
        rows = QiskitIBMRuntimeRunner.available_backends(
            channel=args.channel,
            instance=args.instance,
            token=args.token,
            token_env=args.token_env,
            account_name=args.account_name,
            min_num_qubits=args.min_num_qubits,
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
        "backend_name": args.backend_name,
        "channel": args.channel,
        "instance": args.instance,
        "token": args.token,
        "token_env": args.token_env,
        "account_name": args.account_name,
    }

    def _runner_factory(*_args, **_kwargs):
        return QiskitIBMRuntimeRunner(**runner_kwargs)

    with patch("claimstab.pipelines.main_execution.QiskitAerRunner", new=_runner_factory):
        execution_result = execute_main_plan(plan)
    bundle = build_main_outputs(plan, execution_result)
    runner = QiskitIBMRuntimeRunner(**runner_kwargs)
    _mutate_payload_for_hardware(bundle, runner, args)
    write_main_outputs(bundle, plan, execution_result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
