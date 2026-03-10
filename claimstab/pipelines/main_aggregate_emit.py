from __future__ import annotations

import json
import shlex
import sys
from dataclasses import dataclass
from typing import Any

from claimstab.analysis.rq import build_rq_summary
from claimstab.evidence import build_cep_protocol_meta, build_experiment_cep_record
from claimstab.pipelines.aggregate import build_robustness_map_artifact
from claimstab.pipelines.emit import write_scores_csv
from claimstab.pipelines.main_execution import EVIDENCE_LOOKUP_FIELDS, MainExecutionResult
from claimstab.pipelines.planning import MainPlan


@dataclass
class MainOutputBundle:
    claim_stability_payload: dict[str, Any]
    rq_summary_payload: dict[str, Any]
    robustness_map_payload: dict[str, Any]


def build_main_outputs(plan: MainPlan, exec_result: MainExecutionResult) -> MainOutputBundle:
    args = plan.args
    spec_payload = plan.spec_payload
    ranking_jobs = plan.ranking_jobs
    deltas = plan.deltas
    method_names = plan.method_names
    decision_claims = plan.decision_claims
    metrics_needed = plan.metrics_needed
    resolved_device = plan.resolved_device
    noise_model_mode = plan.noise_model_mode
    runtime_meta = exec_result.runtime_meta
    practicality = exec_result.practicality
    suite_name = exec_result.suite_name
    selected_spaces = exec_result.selected_spaces
    experiments = exec_result.experiments
    comparative_rows = exec_result.comparative_rows
    artifact_manifest = exec_result.artifact_manifest

    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        evidence = exp.get("evidence")
        if not isinstance(evidence, dict):
            continue
        evidence["cep"] = build_experiment_cep_record(
            experiment=exp,
            runtime_meta=runtime_meta,
            evidence=evidence,
        )

    meta_deltas = (
        sorted({float(delta) for job in ranking_jobs for delta in job.get("deltas", [])})
        if ranking_jobs
        else list(deltas)
    )
    robustness_map_artifact = build_robustness_map_artifact(experiments)
    payload = {
        "meta": {
            "suite": suite_name,
            "task": plan.task_kind,
            "deltas": meta_deltas,
            "methods_available": sorted(method_names),
            "generated_by": "claimstab/pipelines/claim_stability_app.py",
            "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
            "runtime": runtime_meta,
            "practicality": practicality,
            "artifacts": {
                "trace_jsonl": artifact_manifest.trace_jsonl,
                "events_jsonl": artifact_manifest.events_jsonl,
                "cache_db": artifact_manifest.cache_db,
                "replay_trace": str(args.replay_trace) if args.replay_trace else None,
                "robustness_map_json": str(plan.out_paths.robustness_json.resolve()),
            },
            "evidence_chain": {
                **build_cep_protocol_meta(
                    lookup_fields=EVIDENCE_LOOKUP_FIELDS,
                    decision_provenance=(
                        "each experiment includes evidence.trace_query + evidence.cep blocks "
                        "that can be matched against trace records for reproducible decision provenance"
                    ),
                ),
            },
        },
        "device_profile": {
            "enabled": resolved_device.profile.enabled,
            "provider": resolved_device.profile.provider,
            "name": resolved_device.profile.name,
            "mode": resolved_device.profile.mode,
            "snapshot_fingerprint": resolved_device.snapshot_fingerprint,
            "snapshot": resolved_device.snapshot,
        },
        "batch": {
            "space_presets": selected_spaces,
            "claim_pairs": [
                f"{job['method_a']}>{job['method_b']}[{job['metric_name']}]"
                for job in ranking_jobs
            ],
            "ranking_claims": ranking_jobs,
            "metrics_evaluated": metrics_needed or ["objective"],
            "decision_claims": decision_claims,
            "num_experiments": len(experiments),
        },
        "experiments": experiments,
        "comparative": {
            "space_claim_delta": comparative_rows,
        },
    }
    if isinstance(spec_payload, dict):
        meta_block = spec_payload.get("meta")
        if isinstance(meta_block, dict) and isinstance(meta_block.get("deprecated_field_used"), list):
            payload["meta"]["deprecated_field_used"] = [str(x) for x in meta_block.get("deprecated_field_used", [])]

    rq_summary = build_rq_summary(payload, debug_attribution=args.debug_attribution)
    payload["rq_summary"] = rq_summary

    if len(experiments) == 1:
        exp = experiments[0]
        payload["claim"] = exp["claim"]
        payload["baseline"] = exp["baseline"]
        payload["stability_rule"] = exp["stability_rule"]
        payload["sampling"] = exp["sampling"]
        payload["backend_engine"] = exp["backend"]["engine"]
        payload["perturbation_space_size"] = exp["sampling"]["perturbation_space_size"]
        payload["per_graph"] = exp["per_graph"]
        payload["overall"] = exp["overall"]

    return MainOutputBundle(
        claim_stability_payload=payload,
        rq_summary_payload=rq_summary,
        robustness_map_payload=robustness_map_artifact,
    )


def write_main_outputs(bundle: MainOutputBundle, plan: MainPlan, exec_result: MainExecutionResult) -> None:
    out_dir = plan.out_paths.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_scores_csv(exec_result.all_rows, plan.out_paths.out_csv)
    plan.out_paths.out_json.write_text(json.dumps(bundle.claim_stability_payload, indent=2), encoding="utf-8")
    plan.out_paths.robustness_json.write_text(json.dumps(bundle.robustness_map_payload, indent=2), encoding="utf-8")
    plan.out_paths.rq_json.write_text(json.dumps(bundle.rq_summary_payload, indent=2), encoding="utf-8")

    print("Wrote:")
    print(" ", plan.out_paths.out_csv.resolve())
    print(" ", plan.out_paths.out_json.resolve())
    print(" ", plan.out_paths.robustness_json.resolve())
    print("Batch:", bundle.claim_stability_payload["batch"])


def maybe_render_report(plan: MainPlan) -> None:
    # Keep compatibility with CLI flag surface; report generation remains in command layer.
    _ = plan
