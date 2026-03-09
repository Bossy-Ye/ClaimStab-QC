from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from claimstab.pipelines.multidevice_execution import MultideviceExecutionResult
from claimstab.pipelines.multidevice_planning import MultidevicePlan


def build_and_write_multidevice_outputs(
    plan: MultidevicePlan,
    execution_result: MultideviceExecutionResult,
    *,
    evidence_chain_meta_fn,
    generated_by: str = "claimstab/pipelines/multidevice_app.py",
) -> None:
    if execution_result.global_trace_index is not None:
        execution_result.global_trace_index.save_jsonl(execution_result.trace_path)

    if execution_result.global_device_summary:
        final_summary = {
            "meta": {
                "suite": execution_result.suite_name,
                "generated_by": generated_by,
                "reproduce_command": "PYTHONPATH=. ./venv/bin/python " + " ".join(shlex.quote(a) for a in sys.argv),
                "runtime": plan.runtime_meta,
                "artifacts": {
                    "trace_jsonl": execution_result.artifact_manifest.trace_jsonl,
                    "events_jsonl": execution_result.artifact_manifest.events_jsonl,
                    "cache_db": execution_result.artifact_manifest.cache_db,
                    "replay_trace": str(plan.args.replay_trace) if plan.args.replay_trace else None,
                },
                "evidence_chain": evidence_chain_meta_fn(),
            },
            "device_summary": execution_result.global_device_summary,
            "comparative": {"space_claim_delta": execution_result.global_device_summary},
        }
        final_json = Path(plan.out_root) / "combined_summary.json"
        final_json.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")
        print(" ", final_json.resolve())
