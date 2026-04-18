from __future__ import annotations

import json
from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Any

from claimstab.perturbations.sampling import normalize_repeats_to_seed_simulator

ALLOWED_SAMPLING_MODES = {"full_factorial", "random_k", "adaptive_ci"}
ALLOWED_BACKEND_ENGINES = {"auto", "basic", "aer"}
ALLOWED_NOISE_MODES = {"none", "from_device_profile"}
ALLOWED_PROVIDERS = {"none", "ibm_fake", "iqm_fake", "generic"}
ALLOWED_DEVICE_MODES = {"transpile_only", "noisy_sim"}
ALLOWED_SPACE_PRESETS = {
    "baseline",
    "compilation_only",
    "compilation_only_exact",
    "sampling_only",
    "sampling_only_exact",
    "combined_light",
    "combined_light_exact",
    "compilation_stress",
    "sampling_stress",
    "sampling_policy_eval",
    "combined_stress",
    "day1_default",
}


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a JSON/YAML spec file into a dictionary."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")

    if p.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("YAML spec parsing requires pyyaml. Install with: pip install pyyaml") from exc
        payload = yaml.safe_load(text) or {}

    if not isinstance(payload, dict):
        raise ValueError(f"Spec at '{p}' must parse to a mapping/object.")
    return payload


def apply_spec_defaults(spec: dict[str, Any]) -> dict[str, Any]:
    """Apply backward-compatible defaults without changing existing behavior."""
    out = deepcopy(spec)

    if "spec_version" not in out:
        legacy_version = out.get("version")
        if isinstance(legacy_version, int):
            out["spec_version"] = legacy_version
        else:
            out["spec_version"] = 1

    backend = out.get("backend")
    if backend is None:
        backend = {}
    if isinstance(backend, dict):
        backend.setdefault("noise_model", "none")
        backend.setdefault("engine", "basic")
        out["backend"] = backend

    device_profile = out.get("device_profile")
    if device_profile is None:
        device_profile = {}
    if isinstance(device_profile, dict):
        device_profile.setdefault("enabled", False)
        device_profile.setdefault("provider", "none")
        device_profile.setdefault("mode", "transpile_only")
        if "name" not in device_profile:
            device_profile["name"] = None
        out["device_profile"] = device_profile

    sampling = out.get("sampling")
    if sampling is None:
        sampling = {}
    if isinstance(sampling, dict):
        sampling.setdefault("mode", "full_factorial")
        sampling.setdefault("seed", 0)
        sampling.setdefault("include_baseline", True)
        out["sampling"] = sampling

    deprecated_used: list[str] = []
    perturbation_space = out.get("perturbation_space")
    if isinstance(perturbation_space, dict):
        normalized_ps, deprecated = normalize_repeats_to_seed_simulator(perturbation_space)
        out["perturbation_space"] = normalized_ps
        deprecated_used.extend(deprecated)

    baseline = out.get("baseline")
    if isinstance(baseline, dict):
        normalized_baseline, deprecated = normalize_repeats_to_seed_simulator(baseline)
        out["baseline"] = normalized_baseline
        deprecated_used.extend(deprecated)

    if deprecated_used:
        meta = out.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        prev = meta.get("deprecated_field_used")
        existing = []
        if isinstance(prev, list):
            existing = [str(x) for x in prev]
        meta["deprecated_field_used"] = sorted(set(existing + deprecated_used))
        out["meta"] = meta

    return out


def _load_schema_v1() -> dict[str, Any]:
    schema_text = resources.files("claimstab.spec").joinpath("schema_v1.json").read_text(encoding="utf-8")
    return json.loads(schema_text)


def _validate_fallback(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    suite = spec.get("suite")
    if isinstance(suite, str):
        if not suite.strip():
            errors.append("suite: must be non-empty when string")
    elif isinstance(suite, dict):
        if not suite.get("id") and not suite.get("name"):
            errors.append("suite: when object, must include id or name")

    sampling = spec.get("sampling")
    if isinstance(sampling, dict):
        mode = sampling.get("mode")
        if mode is not None and mode not in ALLOWED_SAMPLING_MODES:
            errors.append(f"sampling.mode: unsupported value '{mode}'")
        unknown = set(sampling.keys()) - {
            "mode",
            "sample_size",
            "seed",
            "include_baseline",
            "target_ci_width",
            "max_sample_size",
            "min_sample_size",
            "step_size",
        }
        if unknown:
            errors.append(f"sampling: unknown keys {sorted(unknown)}")

    decision_rule = spec.get("decision_rule")
    if isinstance(decision_rule, dict):
        unknown = set(decision_rule.keys()) - {"threshold", "confidence_level"}
        if unknown:
            errors.append(f"decision_rule: unknown keys {sorted(unknown)}")

    backend = spec.get("backend")
    if isinstance(backend, dict):
        engine = backend.get("engine")
        if engine is not None and engine not in ALLOWED_BACKEND_ENGINES:
            errors.append(f"backend.engine: unsupported value '{engine}'")
        noise_model = backend.get("noise_model")
        if noise_model is not None and noise_model not in ALLOWED_NOISE_MODES:
            errors.append(f"backend.noise_model: unsupported value '{noise_model}'")
        unknown = set(backend.keys()) - {"engine", "noise_model"}
        if unknown:
            errors.append(f"backend: unknown keys {sorted(unknown)}")

    device = spec.get("device_profile")
    if isinstance(device, dict):
        provider = device.get("provider")
        if provider is not None and provider not in ALLOWED_PROVIDERS:
            errors.append(f"device_profile.provider: unsupported value '{provider}'")
        mode = device.get("mode")
        if mode is not None and mode not in ALLOWED_DEVICE_MODES:
            errors.append(f"device_profile.mode: unsupported value '{mode}'")
        unknown = set(device.keys()) - {"enabled", "provider", "name", "mode", "basis_gates", "coupling_map"}
        if unknown:
            errors.append(f"device_profile: unknown keys {sorted(unknown)}")

    perturbations = spec.get("perturbations")
    if isinstance(perturbations, dict):
        preset = perturbations.get("preset")
        if preset is not None and preset not in ALLOWED_SPACE_PRESETS:
            errors.append(f"perturbations.preset: unsupported value '{preset}'")
        presets = perturbations.get("presets")
        if isinstance(presets, list):
            for p in presets:
                if p not in ALLOWED_SPACE_PRESETS:
                    errors.append(f"perturbations.presets: unsupported value '{p}'")
        unknown = set(perturbations.keys()) - {"preset", "presets", "transpile_space", "noisy_space"}
        if unknown:
            errors.append(f"perturbations: unknown keys {sorted(unknown)}")

    claims = spec.get("claims")
    if isinstance(claims, list):
        for idx, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"claims[{idx}]: must be an object")
                continue
            ctype = claim.get("type", "ranking")
            if ctype not in {"ranking", "decision", "distribution"}:
                errors.append(f"claims[{idx}].type: unsupported value '{ctype}'")
            unknown = set(claim.keys()) - {
                "type",
                "method_a",
                "method_b",
                "method",
                "deltas",
                "top_k",
                "label",
                "label_meta_key",
                "metric_name",
                "higher_is_better",
                "epsilon",
                "primary_distance",
                "sanity_distance",
                "reference_shots",
            }
            if unknown:
                errors.append(f"claims[{idx}]: unknown keys {sorted(unknown)}")
            if ctype == "distribution":
                epsilon = claim.get("epsilon")
                if epsilon is not None:
                    try:
                        if float(epsilon) < 0.0:
                            errors.append(f"claims[{idx}].epsilon: must be >= 0")
                    except Exception:
                        errors.append(f"claims[{idx}].epsilon: must be numeric")
                primary_distance = claim.get("primary_distance")
                if primary_distance is not None and str(primary_distance).strip().lower() not in {"js", "tvd"}:
                    errors.append(f"claims[{idx}].primary_distance: unsupported value '{primary_distance}'")
                sanity_distance = claim.get("sanity_distance")
                if sanity_distance is not None and str(sanity_distance).strip().lower() not in {"js", "tvd"}:
                    errors.append(f"claims[{idx}].sanity_distance: unsupported value '{sanity_distance}'")
                reference_shots = claim.get("reference_shots")
                if reference_shots is not None and not isinstance(reference_shots, (int, str)):
                    errors.append(f"claims[{idx}].reference_shots: must be int|string|null")
                if isinstance(reference_shots, int) and reference_shots <= 0:
                    errors.append(f"claims[{idx}].reference_shots: must be >= 1 when integer")
    elif isinstance(claims, dict):
        ranking = claims.get("ranking")
        if ranking is not None and not isinstance(ranking, dict):
            errors.append("claims.ranking: must be an object")

    task = spec.get("task")
    if task is not None:
        if not isinstance(task, dict):
            errors.append("task: must be an object")
        else:
            unknown = set(task.keys()) - {"kind", "suite", "entrypoint", "params"}
            if unknown:
                errors.append(f"task: unknown keys {sorted(unknown)}")

    methods = spec.get("methods")
    if methods is not None:
        if not isinstance(methods, list) or not methods:
            errors.append("methods: must be a non-empty list")
        else:
            for idx, method in enumerate(methods):
                if not isinstance(method, dict):
                    errors.append(f"methods[{idx}]: must be an object")
                    continue
                if not isinstance(method.get("name"), str) or not str(method.get("name")).strip():
                    errors.append(f"methods[{idx}].name: must be a non-empty string")
                if not isinstance(method.get("kind"), str) or not str(method.get("kind")).strip():
                    errors.append(f"methods[{idx}].kind: must be a non-empty string")
                unknown = set(method.keys()) - {"name", "kind", "params", "p"}
                if unknown:
                    errors.append(f"methods[{idx}]: unknown keys {sorted(unknown)}")

    return errors


def validate_spec(spec: dict[str, Any]) -> None:
    """Validate a ClaimStab spec against schema v1 with readable errors."""
    normalized = apply_spec_defaults(spec)
    spec_version = normalized.get("spec_version", 1)

    if spec_version != 1:
        raise ValueError(f"Unsupported spec_version={spec_version}. Supported: 1")

    try:
        import jsonschema  # type: ignore
    except Exception:
        errors = _validate_fallback(normalized)
        if errors:
            raise ValueError("Spec validation failed:\n" + "\n".join(f"- {line}" for line in errors))
        return

    schema = _load_schema_v1()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(normalized), key=lambda err: list(err.path))
    if not errors:
        return

    lines = []
    for err in errors:
        path = ".".join(str(p) for p in err.path) if err.path else "<root>"
        lines.append(f"- {path}: {err.message}")
    raise ValueError("Spec validation failed:\n" + "\n".join(lines))


def load_spec(path: str | Path, *, validate: bool = False) -> dict[str, Any]:
    """Load a spec and optionally validate. Always applies compatibility defaults."""
    raw = load_yaml(path)
    normalized = apply_spec_defaults(raw)
    if validate:
        validate_spec(normalized)
    return normalized
