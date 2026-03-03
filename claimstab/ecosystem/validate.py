from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Ecosystem validation requires pyyaml.") from exc


@dataclass(frozen=True)
class EcosystemValidationResult:
    root: str
    counts: dict[str, int]
    warnings: list[str]


_COLLECTIONS = {
    "tasks": ("task.yaml", "task.schema.json"),
    "methods": ("method.yaml", "method.schema.json"),
    "suites": ("suite.yaml", "suite.schema.json"),
    "results": ("result.yaml", "result.schema.json"),
}


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected YAML object.")
    return payload


def _load_schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON schema object.")
    return payload


def _validate_with_fallback(payload: dict[str, Any], schema: dict[str, Any], meta_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        errors: list[str] = []
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                errors.append(f"{meta_path}: <root>: missing required key '{key}'")
        if schema.get("additionalProperties") is False:
            props = set((schema.get("properties") or {}).keys())
            unknown = set(payload.keys()) - props
            if unknown:
                errors.append(f"{meta_path}: <root>: unknown keys {sorted(unknown)}")
        return errors

    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(payload), key=lambda item: list(item.path)):
        field = ".".join(str(x) for x in err.path) if err.path else "<root>"
        out.append(f"{meta_path}: {field}: {err.message}")
    return out


def validate_ecosystem(root: str | Path = "ecosystem") -> EcosystemValidationResult:
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise ValueError(f"Ecosystem root does not exist: {root_path}")

    schemas_dir = root_path / "schemas"
    if not schemas_dir.exists():
        raise ValueError(f"Missing ecosystem schemas directory: {schemas_dir}")

    items: dict[str, list[dict[str, Any]]] = {name: [] for name in _COLLECTIONS}
    warnings: list[str] = []
    errors: list[str] = []

    for name, (filename, schema_name) in _COLLECTIONS.items():
        schema_path = schemas_dir / schema_name
        if not schema_path.exists():
            errors.append(f"Missing schema: {schema_path}")
            continue
        schema = _load_schema(schema_path)

        for meta_path in sorted((root_path / name).glob(f"*/{filename}")):
            try:
                payload = _load_yaml(meta_path)
            except Exception as exc:
                errors.append(f"{meta_path}: {exc}")
                continue

            row_errors = _validate_with_fallback(payload, schema, meta_path)
            if row_errors:
                errors.extend(row_errors)
                continue

            payload["_meta_path"] = str(meta_path)
            items[name].append(payload)

    # ID uniqueness per collection
    for name, rows in items.items():
        seen: set[str] = set()
        for row in rows:
            entry_id = str(row.get("id", "")).strip()
            if not entry_id:
                errors.append(f"{row.get('_meta_path')}: missing id")
                continue
            if entry_id in seen:
                errors.append(f"{row.get('_meta_path')}: duplicate id '{entry_id}' in {name}")
            seen.add(entry_id)

    task_ids = {str(r.get("id")) for r in items["tasks"]}
    suite_ids = {str(r.get("id")) for r in items["suites"]}

    # Cross references
    for row in items["methods"]:
        for task_id in row.get("task_ids", []):
            if str(task_id) not in task_ids:
                errors.append(f"{row.get('_meta_path')}: unknown task_id '{task_id}'")
    for row in items["suites"]:
        if str(row.get("task_id")) not in task_ids:
            errors.append(f"{row.get('_meta_path')}: unknown task_id '{row.get('task_id')}'")
    for row in items["results"]:
        if str(row.get("task_id")) not in task_ids:
            errors.append(f"{row.get('_meta_path')}: unknown task_id '{row.get('task_id')}'")
        if str(row.get("suite_id")) not in suite_ids:
            errors.append(f"{row.get('_meta_path')}: unknown suite_id '{row.get('suite_id')}'")
        artifacts = row.get("artifacts", {})
        if isinstance(artifacts, dict):
            for key, rel_path in artifacts.items():
                p = root_path.parent / str(rel_path)
                if not p.exists():
                    warnings.append(
                        f"{row.get('_meta_path')}: artifact '{key}' path not found now: {rel_path}"
                    )

    if errors:
        raise ValueError("Ecosystem validation failed:\n" + "\n".join(f"- {line}" for line in errors))

    return EcosystemValidationResult(
        root=str(root_path),
        counts={name: len(rows) for name, rows in items.items()},
        warnings=warnings,
    )
