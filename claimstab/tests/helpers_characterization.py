from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal


def _run_command(cmd: list[str], *, cwd: Path) -> None:
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(cwd))
    subprocess.run(cmd, check=True, cwd=str(cwd), env=env)


def run_main_smoke(
    *,
    repo_root: Path,
    task: str,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / f"main_{task}"
        cmd = [
            sys.executable,
            "-m",
            "claimstab.pipelines.claim_stability_app",
            "--task",
            task,
            "--suite",
            "core",
            "--space-preset",
            "baseline",
            "--sampling-mode",
            "random_k",
            "--sample-size",
            "4",
            "--sample-seed",
            "1",
            "--backend-engine",
            "basic",
            "--out-dir",
            str(out_dir),
        ]
        if extra_args:
            cmd.extend(extra_args)
        _run_command(cmd, cwd=repo_root)
        return json.loads((out_dir / "claim_stability.json").read_text(encoding="utf-8"))


def run_multidevice_smoke(
    *,
    repo_root: Path,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / "multidevice"
        cmd = [
            sys.executable,
            "-m",
            "claimstab.pipelines.multidevice_app",
            "--run",
            "transpile_only",
            "--suite",
            "core",
            "--sampling-mode",
            "random_k",
            "--sample-size",
            "2",
            "--sample-seed",
            "1",
            "--backend-engine",
            "basic",
            "--transpile-devices",
            "FakeManilaV2",
            "--transpile-claim-pairs",
            "QAOA_p1>QAOA_p2",
            "--out-dir",
            str(out_dir),
        ]
        if extra_args:
            cmd.extend(extra_args)
        _run_command(cmd, cwd=repo_root)
        return json.loads((out_dir / "combined_summary.json").read_text(encoding="utf-8"))


def _normalize_path(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return text
    return Path(text).name


def _normalize_runtime(payload: dict[str, Any]) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return
    runtime = meta.get("runtime")
    if isinstance(runtime, dict):
        runtime["python_version"] = "<python>"
        runtime["git_commit"] = "<git_commit>"
        runtime["git_dirty"] = "<git_dirty>"
        runtime["dependencies"] = {}
        runtime["environment_flags"] = {}


def _normalize_artifacts(payload: dict[str, Any]) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return
    meta.pop("reproduce_command", None)
    # Additive practicality metrics are intentionally excluded from legacy fixtures.
    meta.pop("practicality", None)
    artifacts = meta.get("artifacts")
    if isinstance(artifacts, dict):
        for key in ("trace_jsonl", "events_jsonl", "cache_db", "replay_trace", "robustness_map_json"):
            if key in artifacts:
                artifacts[key] = _normalize_path(artifacts[key])


def _normalize_cep(payload: dict[str, Any]) -> None:
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        return
    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        evidence = exp.get("evidence")
        if not isinstance(evidence, dict):
            continue
        artifacts = evidence.get("artifacts")
        if isinstance(artifacts, dict):
            for key in ("trace_jsonl", "events_jsonl", "cache_db"):
                if key in artifacts:
                    artifacts[key] = _normalize_path(artifacts[key])
        cep = evidence.get("cep")
        if not isinstance(cep, dict):
            continue
        observation = cep.get("observation")
        if isinstance(observation, dict):
            obs_artifacts = observation.get("artifacts")
            if isinstance(obs_artifacts, dict):
                for key in ("trace_jsonl", "events_jsonl", "cache_db"):
                    if key in obs_artifacts:
                        obs_artifacts[key] = _normalize_path(obs_artifacts[key])
        fingerprint = cep.get("config_fingerprint")
        if isinstance(fingerprint, dict):
            fingerprint["hash"] = "<config_hash>"
            components = fingerprint.get("components")
            if isinstance(components, dict):
                components["git_commit"] = "<git_commit>"
                components["git_dirty"] = "<git_dirty>"
                components["dependencies"] = {}


def normalize_payload(payload: dict[str, Any], *, kind: Literal["main", "multidevice"]) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    _normalize_runtime(out)
    _normalize_artifacts(out)
    _normalize_cep(out)
    if kind == "main":
        comparative = out.get("comparative")
        if isinstance(comparative, dict):
            rows = comparative.get("space_claim_delta")
            if isinstance(rows, list):
                rows.sort(
                    key=lambda row: (
                        str(row.get("space_preset")),
                        str(row.get("claim_pair")),
                        str(row.get("metric_name")),
                        str(row.get("delta")),
                    )
                )
    elif kind == "multidevice":
        rows = out.get("device_summary")
        if isinstance(rows, list):
            rows.sort(
                key=lambda row: (
                    str(row.get("batch_mode")),
                    str(row.get("device_name")),
                    str(row.get("metric_name")),
                    str(row.get("claim_pair")),
                    str(row.get("delta")),
                )
            )
    return out
