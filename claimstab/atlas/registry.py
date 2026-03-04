from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class AtlasValidationResult:
    root: Path
    submission_count: int
    warnings: list[str]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    chars = []
    for ch in value.strip().lower():
        if ch.isalnum():
            chars.append(ch)
        elif ch in {"-", "_"}:
            chars.append(ch)
        elif ch.isspace() or ch in {".", "/", ":"}:
            chars.append("-")
    slug = "".join(chars).strip("-")
    return slug or "result"


def _infer_claim_types(payload: dict[str, Any]) -> list[str]:
    claim_types: set[str] = set()
    experiments = payload.get("experiments")
    if isinstance(experiments, list):
        for exp in experiments:
            if not isinstance(exp, dict):
                continue
            claim = exp.get("claim")
            if isinstance(claim, dict):
                claim_type = claim.get("type", "ranking")
                if isinstance(claim_type, str):
                    claim_types.add(claim_type)
    if not claim_types:
        claim_types.add("ranking")
    return sorted(claim_types)


def _extract_claim_summaries(payload: dict[str, Any]) -> list[str]:
    out: list[str] = []
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        return out
    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        claim = exp.get("claim")
        if not isinstance(claim, dict):
            continue
        ctype = str(claim.get("type", "ranking"))
        if ctype == "ranking":
            method_a = str(claim.get("method_a", "A"))
            method_b = str(claim.get("method_b", "B"))
            metric_name = str(claim.get("metric_name", "objective"))
            deltas = claim.get("deltas", [])
            out.append(f"ranking:{method_a}>{method_b};metric={metric_name};deltas={deltas}")
        elif ctype == "decision":
            method = str(claim.get("method", "method"))
            top_k = claim.get("top_k", 1)
            out.append(f"decision:{method};top_k={top_k}")
        elif ctype == "distribution":
            method = str(claim.get("method", "method"))
            out.append(f"distribution:{method}")
        else:
            out.append(f"{ctype}:{claim}")
    # preserve order, dedupe
    return list(dict.fromkeys(out))


def _extract_sampling_summary(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        return rows
    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        sampling = exp.get("sampling")
        if not isinstance(sampling, dict):
            continue
        rows.append(
            {
                "space_preset": sampling.get("space_preset"),
                "mode": sampling.get("mode"),
                "sample_size": sampling.get("sample_size"),
                "seed": sampling.get("seed"),
                "sampled_configurations_with_baseline": sampling.get("sampled_configurations_with_baseline"),
                "perturbation_space_size": sampling.get("perturbation_space_size"),
            }
        )
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _default_submission_id(payload: dict[str, Any], contributor: str, run_dir: Path) -> str:
    meta = payload.get("meta", {})
    task = str(meta.get("task", "task"))
    suite = str(meta.get("suite", "suite"))
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    basis = f"{run_dir.resolve()}::{task}::{suite}::{contributor}::{ts}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8]
    return f"{ts}-{_slug(task)}-{_slug(suite)}-{digest}"


def _load_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "submissions": []}
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid atlas index JSON: {path}")
    payload.setdefault("version", 1)
    payload.setdefault("submissions", [])
    if not isinstance(payload.get("submissions"), list):
        raise ValueError(f"Invalid atlas index format (submissions not list): {path}")
    return payload


def publish_result(
    run_dir: str | Path,
    *,
    atlas_root: str | Path = "atlas",
    contributor: str = "anonymous",
    title: str | None = None,
    submission_id: str | None = None,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    if not run_path.exists():
        raise ValueError(f"Run directory does not exist: {run_path}")

    claim_json = run_path / "claim_stability.json"
    if not claim_json.exists():
        raise ValueError(f"Missing required artifact: {claim_json}")

    payload = _load_json(claim_json)
    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    atlas_path = Path(atlas_root)
    submissions_dir = atlas_path / "submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)
    index_path = atlas_path / "index.json"
    index_payload = _load_index(index_path)

    sid = _slug(submission_id) if submission_id else _default_submission_id(payload, contributor, run_path)
    target_dir = submissions_dir / sid
    if target_dir.exists():
        raise ValueError(f"Submission id already exists: {sid}")
    target_dir.mkdir(parents=True, exist_ok=False)

    artifacts: dict[str, str] = {}
    for name in ["claim_stability.json", "scores.csv", "rq_summary.json", "stability_report.html"]:
        src = run_path / name
        if src.exists():
            shutil.copy2(src, target_dir / name)
            artifacts[name] = str(Path("submissions") / sid / name)

    record: dict[str, Any] = {
        "submission_id": sid,
        "title": title or sid,
        "contributor": contributor,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "task": str(meta.get("task", "unknown")),
        "suite": str(meta.get("suite", "unknown")),
        "claim_types": _infer_claim_types(payload),
        "claim_summaries": _extract_claim_summaries(payload),
        "sampling_summary": _extract_sampling_summary(payload),
        "reproduce_command": meta.get("reproduce_command"),
        "how_to_cite": "https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/CITATION.cff",
        "source_run_dir": str(run_path.resolve()),
        "artifacts": artifacts,
    }

    (target_dir / "metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    artifacts["metadata.json"] = str(Path("submissions") / sid / "metadata.json")

    index_payload.setdefault("submissions", [])
    submissions = index_payload["submissions"]
    assert isinstance(submissions, list)
    submissions.append(record)
    index_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
    return record


def validate_atlas(atlas_root: str | Path = "atlas") -> AtlasValidationResult:
    root = Path(atlas_root)
    warnings: list[str] = []
    if not root.exists():
        raise ValueError(f"Atlas root does not exist: {root}")

    index_path = root / "index.json"
    index_payload = _load_index(index_path)
    submissions = index_payload.get("submissions", [])
    if not isinstance(submissions, list):
        raise ValueError(f"Invalid atlas index: {index_path}")

    for entry in submissions:
        if not isinstance(entry, dict):
            warnings.append("Found non-dictionary submission entry in atlas index.")
            continue
        sid = str(entry.get("submission_id", ""))
        if not sid:
            warnings.append("Submission without submission_id.")
            continue
        md = root / "submissions" / sid / "metadata.json"
        if not md.exists():
            warnings.append(f"Missing metadata file for submission: {sid}")
        artifacts = entry.get("artifacts", {})
        if isinstance(artifacts, dict):
            for _, rel_path in artifacts.items():
                if not isinstance(rel_path, str):
                    continue
                artifact = root / rel_path
                if not artifact.exists():
                    warnings.append(f"Missing artifact for submission {sid}: {rel_path}")

    return AtlasValidationResult(root=root, submission_count=len(submissions), warnings=warnings)
