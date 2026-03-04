from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SubmissionSnapshot:
    submission_id: str
    title: str
    contributor: str
    task: str
    suite: str
    claim_types: list[str]
    methods: list[str]
    claims: list[str]
    claim_summaries: list[str]
    spaces: list[str]
    sampling_rows: list[dict[str, Any]]
    baseline: dict[str, Any] | None
    reproduce_command: str | None
    how_to_cite: str | None
    artifact_paths: dict[str, str]
    created_at_utc: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _format_claim(claim: dict[str, Any]) -> str:
    claim_type = str(claim.get("type", "ranking"))
    if claim_type == "ranking":
        a = str(claim.get("method_a", "A"))
        b = str(claim.get("method_b", "B"))
        deltas = claim.get("deltas", [])
        return f"ranking: {a} > {b}, deltas={deltas}"
    if claim_type == "decision":
        method = str(claim.get("method", "method"))
        top_k = claim.get("top_k", 1)
        label_key = claim.get("label_meta_key", "target_label")
        return f"decision: {method}, top_k={top_k}, label_key={label_key}"
    if claim_type == "distribution":
        method = str(claim.get("method", "method"))
        metric = claim.get("metric_name", "distance")
        return f"distribution: {method}, metric={metric}"
    return f"{claim_type}: {claim}"


def _github_blob_url(repo_url: str, rel_path: str) -> str:
    base = repo_url.rstrip("/")
    return f"{base}/blob/main/{rel_path}"


def _snapshot_from_entry(atlas_root: Path, entry: dict[str, Any]) -> SubmissionSnapshot:
    sid = str(entry.get("submission_id", "unknown"))
    title = str(entry.get("title", sid))
    contributor = str(entry.get("contributor", "unknown"))
    task = str(entry.get("task", "unknown"))
    suite = str(entry.get("suite", "unknown"))
    claim_types = _normalize_list(entry.get("claim_types"))
    claim_summaries = _normalize_list(entry.get("claim_summaries"))
    created_at = str(entry.get("created_at_utc", "unknown"))
    reproduce_command = entry.get("reproduce_command")
    how_to_cite = entry.get("how_to_cite")
    artifact_paths = {
        str(k): str(v) for k, v in (entry.get("artifacts", {}) or {}).items() if isinstance(v, str)
    }

    claim_json_rel = artifact_paths.get("claim_stability.json")
    methods: list[str] = []
    claims: list[str] = []
    spaces: list[str] = []
    sampling_rows: list[dict[str, Any]] = []
    baseline: dict[str, Any] | None = None

    if claim_json_rel:
        claim_json_path = atlas_root / claim_json_rel
        if claim_json_path.exists():
            payload = _load_json(claim_json_path)
            meta = payload.get("meta", {})
            if isinstance(meta, dict):
                methods = _normalize_list(meta.get("methods_available"))

            experiments = payload.get("experiments", [])
            if isinstance(experiments, list):
                for exp in experiments:
                    if not isinstance(exp, dict):
                        continue
                    claim = exp.get("claim")
                    if isinstance(claim, dict):
                        claims.append(_format_claim(claim))
                    sampling = exp.get("sampling")
                    if isinstance(sampling, dict):
                        space = str(sampling.get("space_preset", ""))
                        if space:
                            spaces.append(space)
                        sampling_rows.append(
                            {
                                "space_preset": space,
                                "mode": sampling.get("mode"),
                                "sample_size": sampling.get("sample_size"),
                                "seed": sampling.get("seed"),
                                "sampled_with_baseline": sampling.get("sampled_configurations_with_baseline"),
                                "space_size": sampling.get("perturbation_space_size"),
                            }
                        )
                    if baseline is None:
                        b = exp.get("baseline")
                        if isinstance(b, dict):
                            baseline = b

    # De-duplicate while preserving order.
    methods = list(dict.fromkeys(methods))
    claims = list(dict.fromkeys(claims))
    spaces = list(dict.fromkeys(spaces))

    return SubmissionSnapshot(
        submission_id=sid,
        title=title,
        contributor=contributor,
        task=task,
        suite=suite,
        claim_types=claim_types,
        methods=methods,
        claims=claims,
        claim_summaries=claim_summaries,
        spaces=spaces,
        sampling_rows=sampling_rows,
        baseline=baseline,
        reproduce_command=str(reproduce_command) if isinstance(reproduce_command, str) else None,
        how_to_cite=str(how_to_cite) if isinstance(how_to_cite, str) else None,
        artifact_paths=artifact_paths,
        created_at_utc=created_at,
    )


def build_dataset_registry_markdown(
    atlas_root: str | Path = "atlas",
    *,
    repo_url: str = "https://github.com/Bossy-Ye/ClaimStab-QC",
) -> str:
    root = Path(atlas_root)
    index_path = root / "index.json"
    if not index_path.exists():
        raise ValueError(f"Atlas index not found: {index_path}")
    payload = _load_json(index_path)
    submissions_raw = payload.get("submissions", [])
    if not isinstance(submissions_raw, list):
        raise ValueError(f"Invalid atlas index format: {index_path}")

    snapshots = [
        _snapshot_from_entry(root, entry)
        for entry in submissions_raw
        if isinstance(entry, dict)
    ]

    lines: list[str] = []
    lines.append("# Dataset Registry")
    lines.append("")
    lines.append(
        "This page lists current ClaimAtlas submissions with problem/task, algorithms, claims, and perturbation settings."
    )
    lines.append("")
    lines.append(
        f"_Generated at {datetime.now(timezone.utc).replace(microsecond=0).isoformat()} from `atlas/index.json`._"
    )
    lines.append("")
    lines.append("## Submission Overview")
    lines.append("")
    lines.append("| Submission | Task | Suite | Claim Types | Spaces | Contributor |")
    lines.append("|---|---|---|---|---|---|")
    for s in snapshots:
        lines.append(
            f"| `{s.submission_id}` | `{s.task}` | `{s.suite}` | `{', '.join(s.claim_types)}` | `{', '.join(s.spaces)}` | `{s.contributor}` |"
        )

    for s in snapshots:
        lines.append("")
        lines.append(f"## Submission `{s.submission_id}`")
        lines.append("")
        lines.append(f"- Title: {s.title}")
        lines.append(f"- Created (UTC): {s.created_at_utc}")
        lines.append(f"- Task: `{s.task}`")
        lines.append(f"- Suite: `{s.suite}`")
        lines.append(f"- Claim types: `{', '.join(s.claim_types)}`")
        lines.append(f"- Algorithms (methods): `{', '.join(s.methods) if s.methods else 'N/A'}`")
        lines.append("")
        lines.append("Claims:")
        rendered_claims = s.claim_summaries or s.claims
        if rendered_claims:
            for c in rendered_claims:
                lines.append(f"- `{c}`")
        else:
            lines.append("- `N/A`")

        lines.append("")
        lines.append("Perturbation / Sampling settings:")
        lines.append("")
        lines.append("| space_preset | mode | sample_size | seed | sampled_with_baseline | perturbation_space_size |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        if s.sampling_rows:
            seen_rows = set()
            for row in s.sampling_rows:
                row_key = (
                    str(row.get("space_preset")),
                    str(row.get("mode")),
                    str(row.get("sample_size")),
                    str(row.get("seed")),
                    str(row.get("sampled_with_baseline")),
                    str(row.get("space_size")),
                )
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)
                lines.append(
                    f"| `{row.get('space_preset')}` | `{row.get('mode')}` | `{row.get('sample_size')}` | `{row.get('seed')}` | `{row.get('sampled_with_baseline')}` | `{row.get('space_size')}` |"
                )
        else:
            lines.append("| `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` |")

        if s.baseline:
            lines.append("")
            lines.append("Reference baseline configuration:")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(s.baseline, indent=2))
            lines.append("```")

        lines.append("")
        lines.append("Artifacts:")
        for name, rel_path in sorted(s.artifact_paths.items()):
            public_rel = str(Path("atlas") / rel_path)
            url = _github_blob_url(repo_url, public_rel)
            lines.append(f"- `{name}`: [{public_rel}]({url})")

        if s.reproduce_command:
            lines.append("")
            lines.append("Reproduce command:")
            lines.append("")
            lines.append("```bash")
            lines.append(s.reproduce_command)
            lines.append("```")
        if s.how_to_cite:
            lines.append("")
            lines.append(f"Citation: [{s.how_to_cite}]({s.how_to_cite})")

    lines.append("")
    lines.append("## How To Add New Dataset Rows")
    lines.append("")
    lines.append("1. `claimstab run --spec <your_spec.yml> --out-dir output/<run_name> --report`")
    lines.append("2. `claimstab publish-result --run-dir output/<run_name> --atlas-root atlas --contributor <you>`")
    lines.append("3. Rebuild docs after regenerating this page.")
    lines.append("")
    return "\n".join(lines) + "\n"
