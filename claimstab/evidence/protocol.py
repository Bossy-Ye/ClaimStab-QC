from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Mapping, Sequence

from claimstab.core.trace import TraceIndex


CEP_REQUIRED_COMPONENTS: tuple[str, ...] = (
    "config_fingerprint",
    "perturbation_space",
    "sampling_strategy",
    "observation",
    "inference",
)


@dataclass
class EvidenceValidationResult:
    json_path: Path
    schema_valid: bool
    trace_checked: bool
    experiments_checked: int
    experiments_with_trace_match: int
    errors: list[str]
    warnings: list[str]


def _stable_hash(payload: Mapping[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _load_schema_v1() -> dict[str, Any]:
    schema_text = resources.files("claimstab.evidence").joinpath("schema_cep_v1.json").read_text(encoding="utf-8")
    return json.loads(schema_text)


def _resolve_artifact_path(value: Any, *, base_dir: Path | None) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    out = Path(text)
    if out.is_absolute():
        return out
    if base_dir is None:
        return out
    return (base_dir / out).resolve()


def build_cep_protocol_meta(
    *,
    lookup_fields: Sequence[str],
    decision_provenance: str,
) -> dict[str, Any]:
    return {
        "protocol": "cep_v1",
        "schema_id": "claimstab/evidence/schema_cep_v1.json",
        "trace_source": "trace_jsonl",
        "events_source": "events_jsonl",
        "lookup_fields": [str(x) for x in lookup_fields],
        "decision_provenance": str(decision_provenance),
        "required_evidence_fields": list(CEP_REQUIRED_COMPONENTS),
    }


def build_experiment_cep_record(
    *,
    experiment: Mapping[str, Any],
    runtime_meta: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    sampling = experiment.get("sampling", {})
    if not isinstance(sampling, Mapping):
        sampling = {}
    backend = experiment.get("backend", {})
    if not isinstance(backend, Mapping):
        backend = {}
    device_profile = experiment.get("device_profile", {})
    if not isinstance(device_profile, Mapping):
        device_profile = {}
    claim = experiment.get("claim", {})
    if not isinstance(claim, Mapping):
        claim = {}
    stability_rule = experiment.get("stability_rule", {})
    if not isinstance(stability_rule, Mapping):
        stability_rule = {}

    fingerprint_components = {
        "git_commit": runtime_meta.get("git_commit"),
        "git_dirty": runtime_meta.get("git_dirty"),
        "dependencies": runtime_meta.get("dependencies", {}),
        "backend": dict(backend),
        "device_profile": dict(device_profile),
        "sampling": {
            "suite": sampling.get("suite"),
            "space_preset": sampling.get("space_preset"),
            "mode": sampling.get("mode"),
            "sample_size": sampling.get("sample_size"),
            "seed": sampling.get("seed"),
        },
    }

    return {
        "protocol_version": "cep_v1",
        "config_fingerprint": {
            "algorithm": "sha256",
            "hash": _stable_hash(fingerprint_components),
            "components": fingerprint_components,
        },
        "perturbation_space": {
            "suite": sampling.get("suite"),
            "space_preset": sampling.get("space_preset"),
            "perturbation_space_size": sampling.get("perturbation_space_size"),
            "baseline": experiment.get("baseline"),
        },
        "sampling_strategy": {
            "mode": sampling.get("mode"),
            "sample_size": sampling.get("sample_size"),
            "seed": sampling.get("seed"),
            "adaptive_stopping": sampling.get("adaptive_stopping"),
        },
        "observation": {
            "trace_query": evidence.get("trace_query", {}),
            "artifacts": evidence.get("artifacts", {}),
            "lookup_fields": evidence.get("lookup_fields", []),
        },
        "inference": {
            "claim": dict(claim),
            "stability_rule": dict(stability_rule),
        },
    }


def validate_evidence_payload(
    payload: dict[str, Any],
    *,
    json_path: str | Path = "<memory>",
    base_dir: str | Path | None = None,
    trace_jsonl: str | Path | None = None,
    check_trace: bool = True,
) -> EvidenceValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    target = Path(json_path)
    root_dir = Path(base_dir) if base_dir is not None else (target.parent if str(json_path) != "<memory>" else Path.cwd())

    schema_valid = True
    try:
        import jsonschema  # type: ignore

        schema = _load_schema_v1()
        validator = jsonschema.Draft202012Validator(schema)
        schema_errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
        if schema_errors:
            schema_valid = False
            for err in schema_errors:
                path = ".".join(str(p) for p in err.path) if err.path else "<root>"
                errors.append(f"schema:{path}: {err.message}")
    except Exception as exc:
        warnings.append(f"Schema validation skipped ({type(exc).__name__}: {exc}).")

    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    artifacts = meta.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    evidence_chain = meta.get("evidence_chain", {})
    if not isinstance(evidence_chain, dict):
        evidence_chain = {}

    protocol = str(evidence_chain.get("protocol", ""))
    if protocol != "cep_v1":
        warnings.append("meta.evidence_chain.protocol is missing or not 'cep_v1'.")

    lookup_fields = evidence_chain.get("lookup_fields")
    if not isinstance(lookup_fields, list) or not lookup_fields:
        errors.append("meta.evidence_chain.lookup_fields must be a non-empty list.")

    req_fields = evidence_chain.get("required_evidence_fields")
    if not isinstance(req_fields, list) or not req_fields:
        warnings.append("meta.evidence_chain.required_evidence_fields is missing.")

    resolved_meta_trace = _resolve_artifact_path(artifacts.get("trace_jsonl"), base_dir=root_dir)
    resolved_trace = Path(trace_jsonl) if trace_jsonl is not None else resolved_meta_trace
    if check_trace:
        if resolved_trace is None:
            errors.append("Trace check enabled but no trace_jsonl path is available in meta.artifacts or --trace-jsonl.")
        elif not resolved_trace.exists():
            errors.append(f"trace_jsonl not found: {resolved_trace}")

    for key in ("events_jsonl", "cache_db"):
        path = _resolve_artifact_path(artifacts.get(key), base_dir=root_dir)
        if path is not None and not path.exists():
            warnings.append(f"meta.artifacts.{key} not found on disk: {path}")

    trace_keys: set[tuple[str, str, str, str]] = set()
    trace_checked = False
    if check_trace and resolved_trace is not None and resolved_trace.exists():
        trace_checked = True
        try:
            trace_index = TraceIndex.load_jsonl(resolved_trace)
            for rec in trace_index.records:
                trace_keys.add((str(rec.suite), str(rec.space_preset), str(rec.metric_name), str(rec.method)))
            if not trace_keys:
                errors.append(f"Trace file is empty: {resolved_trace}")
        except Exception as exc:
            errors.append(f"Could not load trace_jsonl ({resolved_trace}): {type(exc).__name__}: {exc}")

    experiments = payload.get("experiments", [])
    if not isinstance(experiments, list):
        experiments = []

    experiments_checked = 0
    experiments_with_trace_match = 0
    for idx, exp in enumerate(experiments):
        if not isinstance(exp, dict):
            errors.append(f"experiments[{idx}] is not an object.")
            continue
        exp_id = str(exp.get("experiment_id", f"index:{idx}"))
        evidence = exp.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{exp_id}: missing evidence block.")
            continue
        experiments_checked += 1

        exp_artifacts = evidence.get("artifacts", {})
        if not isinstance(exp_artifacts, dict):
            exp_artifacts = {}
        exp_trace = _resolve_artifact_path(exp_artifacts.get("trace_jsonl"), base_dir=root_dir)
        if exp_trace is None:
            errors.append(f"{exp_id}: evidence.artifacts.trace_jsonl is missing.")
        elif check_trace and not exp_trace.exists():
            errors.append(f"{exp_id}: evidence trace_jsonl not found on disk: {exp_trace}")
        elif resolved_trace is not None and exp_trace != resolved_trace:
            warnings.append(f"{exp_id}: experiment trace_jsonl differs from meta trace_jsonl.")

        query = evidence.get("trace_query", {})
        if not isinstance(query, dict):
            errors.append(f"{exp_id}: evidence.trace_query must be an object.")
            query = {}
        methods = query.get("methods", [])
        if not isinstance(methods, list) or not methods:
            errors.append(f"{exp_id}: evidence.trace_query.methods must be a non-empty list.")
            methods = []
        suite = str(query.get("suite", ""))
        space_preset = str(query.get("space_preset", ""))
        metric_name = str(query.get("metric_name", ""))
        if not suite or not space_preset or not metric_name:
            errors.append(f"{exp_id}: trace_query requires suite, space_preset, and metric_name.")

        if trace_checked and suite and space_preset and metric_name and methods:
            matched = any(
                (suite, space_preset, metric_name, str(method_name)) in trace_keys
                for method_name in methods
            )
            if not matched:
                errors.append(
                    f"{exp_id}: no trace records match query "
                    f"(suite={suite}, space={space_preset}, metric={metric_name}, methods={methods})."
                )
            else:
                experiments_with_trace_match += 1

        exp_lookup = evidence.get("lookup_fields")
        if not isinstance(exp_lookup, list) or not exp_lookup:
            errors.append(f"{exp_id}: evidence.lookup_fields must be a non-empty list.")

        cep = evidence.get("cep")
        if not isinstance(cep, dict):
            errors.append(f"{exp_id}: evidence.cep block is missing.")
            continue
        for required_key in CEP_REQUIRED_COMPONENTS:
            if required_key not in cep:
                errors.append(f"{exp_id}: evidence.cep.{required_key} is missing.")
        cf = cep.get("config_fingerprint", {})
        if not isinstance(cf, dict):
            errors.append(f"{exp_id}: evidence.cep.config_fingerprint must be an object.")
        else:
            if str(cf.get("algorithm", "")) != "sha256":
                warnings.append(f"{exp_id}: config_fingerprint.algorithm is not 'sha256'.")
            digest = str(cf.get("hash", ""))
            if len(digest) < 32:
                errors.append(f"{exp_id}: config_fingerprint.hash looks invalid.")

    if not experiments and "device_summary" in payload:
        warnings.append("No experiments array found; payload appears to be a device-summary aggregate.")
    elif not experiments:
        errors.append("Payload has no experiments.")

    return EvidenceValidationResult(
        json_path=target,
        schema_valid=schema_valid,
        trace_checked=trace_checked,
        experiments_checked=experiments_checked,
        experiments_with_trace_match=experiments_with_trace_match,
        errors=errors,
        warnings=warnings,
    )


def validate_evidence_file(
    json_path: str | Path,
    *,
    base_dir: str | Path | None = None,
    trace_jsonl: str | Path | None = None,
    check_trace: bool = True,
) -> EvidenceValidationResult:
    src = Path(json_path)
    payload = json.loads(src.read_text(encoding="utf-8"))
    return validate_evidence_payload(
        payload,
        json_path=src,
        base_dir=base_dir,
        trace_jsonl=trace_jsonl,
        check_trace=check_trace,
    )
