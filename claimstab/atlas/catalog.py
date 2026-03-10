from __future__ import annotations

import html
import json
import re
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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "entry"


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _render_pills(values: list[str]) -> str:
    if not values:
        return '<span class="csr-pill">N/A</span>'
    return " ".join(f'<span class="csr-pill">{_escape(v)}</span>' for v in values)


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
    snapshots = sorted(snapshots, key=lambda item: item.created_at_utc, reverse=True)

    task_values = sorted({s.task for s in snapshots if s.task})
    claim_type_values = sorted({c for s in snapshots for c in s.claim_types if c})
    unique_spaces = sorted({sp for s in snapshots for sp in s.spaces if sp})

    lines: list[str] = []
    lines.append("# Dataset Registry")
    lines.append("")
    lines.append("Human-readable view of ClaimAtlas submissions.")
    lines.append("")
    lines.append("Source of truth:")
    lines.append("- `atlas/index.json` (canonical index)")
    lines.append("- `atlas/submissions/*` (canonical artifacts)")
    lines.append("")
    lines.append("This page is generated from the canonical index; do not edit this file manually.")
    lines.append("To refresh: `python -m claimstab.cli export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md`")
    lines.append("")
    lines.append(
        f"_Generated at {datetime.now(timezone.utc).replace(microsecond=0).isoformat()} from `atlas/index.json`._"
    )
    lines.append("")
    lines.append('<div id="dataset-registry-overview" class="csr-hero">')
    lines.append('  <p class="csr-eyebrow">ClaimAtlas Browser</p>')
    lines.append("  <h2>Dataset Registry Overview</h2>")
    lines.append("  <p>Click any row to jump to a dataset profile. Use filters to quickly narrow by task or claim type.</p>")
    lines.append('  <div class="csr-metrics">')
    lines.append(
        f'    <div><span>Total submissions</span><strong>{len(snapshots)}</strong></div>'
    )
    lines.append(
        f'    <div><span>Tasks</span><strong>{len(task_values)}</strong></div>'
    )
    lines.append(
        f'    <div><span>Claim types</span><strong>{len(claim_type_values)}</strong></div>'
    )
    lines.append(
        f'    <div><span>Spaces covered</span><strong>{len(unique_spaces)}</strong></div>'
    )
    lines.append("  </div>")
    lines.append("</div>")
    lines.append("")
    lines.append('<div class="csr-controls">')
    lines.append('  <label class="csr-filter-group" for="csr-filter">Search</label>')
    lines.append(
        '  <input id="csr-filter" type="search" placeholder="Try maxcut, adaptive, bv, ranking..." aria-label="Filter datasets" />'
    )
    lines.append('  <label class="csr-filter-group" for="csr-filter-task">Task</label>')
    lines.append('  <select id="csr-filter-task" aria-label="Filter by task">')
    lines.append('    <option value="">All tasks</option>')
    for task in task_values:
        lines.append(f'    <option value="{_escape(task)}">{_escape(task)}</option>')
    lines.append("  </select>")
    lines.append('  <label class="csr-filter-group" for="csr-filter-claim">Claim type</label>')
    lines.append('  <select id="csr-filter-claim" aria-label="Filter by claim type">')
    lines.append('    <option value="">All claim types</option>')
    for claim_type in claim_type_values:
        lines.append(f'    <option value="{_escape(claim_type)}">{_escape(claim_type)}</option>')
    lines.append("  </select>")
    lines.append(
        f'  <p class="csr-filter-count"><strong id="csr-visible-count">{len(snapshots)}</strong> / {len(snapshots)} shown</p>'
    )
    lines.append("</div>")
    lines.append("")
    lines.append('<div class="csr-table-wrap">')
    lines.append('<table class="csr-table">')
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append("<th>Submission</th><th>Task</th><th>Suite</th><th>Claim Types</th><th>Spaces</th><th>Contributor</th><th>Open</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")
    for s in snapshots:
        anchor = f"submission-{_slugify(s.submission_id)}"
        claim_json_rel = s.artifact_paths.get("claim_stability.json")
        claim_json_url = (
            _github_blob_url(repo_url, str(Path("atlas") / claim_json_rel))
            if claim_json_rel
            else f"#{anchor}"
        )
        search_blob = " ".join(
            [
                s.submission_id,
                s.title,
                s.task,
                s.suite,
                s.contributor,
                " ".join(s.claim_types),
                " ".join(s.spaces),
                " ".join(s.methods),
            ]
        ).lower()
        lines.append(
            f'<tr class="csr-row" tabindex="0" data-href="#{_escape(anchor)}" data-task="{_escape(s.task)}" '
            f'data-claims="{_escape(",".join(s.claim_types))}" data-search="{_escape(search_blob)}">'
        )
        lines.append(f'<td><a href="#{_escape(anchor)}"><code>{_escape(s.submission_id)}</code></a></td>')
        lines.append(f"<td>{_escape(s.task)}</td>")
        lines.append(f"<td>{_escape(s.suite)}</td>")
        lines.append(f"<td>{_render_pills(s.claim_types)}</td>")
        lines.append(f"<td>{_render_pills(s.spaces)}</td>")
        lines.append(f"<td>{_escape(s.contributor)}</td>")
        lines.append(
            f'<td><a class="csr-link-btn" href="{_escape(claim_json_url)}" target="_blank" rel="noopener">claim_stability.json</a></td>'
        )
        lines.append("</tr>")
    lines.append("</tbody>")
    lines.append("</table>")
    lines.append("</div>")

    for s in snapshots:
        anchor = f"submission-{_slugify(s.submission_id)}"
        lines.append("")
        lines.append(f'<section id="{_escape(anchor)}" class="csr-entry">')
        lines.append(
            f'<h2>Submission <code>{_escape(s.submission_id)}</code></h2>'
        )
        lines.append(
            f'<p class="csr-entry-meta"><strong>{_escape(s.title)}</strong> · {_escape(s.task)} / {_escape(s.suite)} · by {_escape(s.contributor)} · {_escape(s.created_at_utc)}</p>'
        )
        lines.append('<div class="csr-pill-row">')
        lines.append(_render_pills(s.claim_types))
        lines.append(_render_pills(s.spaces))
        lines.append("</div>")
        lines.append("")
        lines.append("Methods:")
        lines.append("")
        lines.append(f"- `{', '.join(s.methods) if s.methods else 'N/A'}`")
        lines.append("")
        rendered_claims = s.claim_summaries or s.claims
        lines.append('<details class="csr-fold" open>')
        lines.append(f"<summary>Claims ({len(rendered_claims) if rendered_claims else 0})</summary>")
        if rendered_claims:
            lines.append("<ul>")
            for c in rendered_claims:
                lines.append(f"<li><code>{_escape(c)}</code></li>")
            lines.append("</ul>")
        else:
            lines.append("<p><code>N/A</code></p>")
        lines.append("</details>")

        lines.append("")
        lines.append('<details class="csr-fold" open>')
        lines.append("<summary>Perturbation / Sampling settings</summary>")
        lines.append('<div class="csr-mini-table-wrap">')
        lines.append('<table class="csr-mini-table">')
        lines.append("<thead>")
        lines.append("<tr>")
        lines.append("<th>space_preset</th><th>mode</th><th>sample_size</th><th>seed</th><th>sampled_with_baseline</th><th>perturbation_space_size</th>")
        lines.append("</tr>")
        lines.append("</thead>")
        lines.append("<tbody>")
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
                    "<tr>"
                    f"<td><code>{_escape(row.get('space_preset'))}</code></td>"
                    f"<td><code>{_escape(row.get('mode'))}</code></td>"
                    f"<td><code>{_escape(row.get('sample_size'))}</code></td>"
                    f"<td><code>{_escape(row.get('seed'))}</code></td>"
                    f"<td><code>{_escape(row.get('sampled_with_baseline'))}</code></td>"
                    f"<td><code>{_escape(row.get('space_size'))}</code></td>"
                    "</tr>"
                )
        else:
            lines.append('<tr><td colspan="6"><code>N/A</code></td></tr>')
        lines.append("</tbody>")
        lines.append("</table>")
        lines.append("</div>")
        lines.append("</details>")

        if s.baseline:
            lines.append("")
            lines.append('<details class="csr-fold">')
            lines.append("<summary>Reference baseline configuration</summary>")
            lines.append('<pre class="csr-codeblock"><code class="language-json">')
            lines.append(_escape(json.dumps(s.baseline, indent=2)))
            lines.append("</code></pre>")
            lines.append("</details>")

        lines.append("")
        lines.append("Artifacts:")
        lines.append("")
        lines.append('<div class="csr-artifact-grid">')
        for name, rel_path in sorted(s.artifact_paths.items()):
            public_rel = str(Path("atlas") / rel_path)
            url = _github_blob_url(repo_url, public_rel)
            lines.append(
                f'<a class="csr-artifact-link" href="{_escape(url)}" target="_blank" rel="noopener"><span>{_escape(name)}</span><small>{_escape(public_rel)}</small></a>'
            )
        lines.append("</div>")

        if s.reproduce_command:
            lines.append("")
            lines.append('<details class="csr-fold">')
            lines.append("<summary>Reproduce command</summary>")
            lines.append('<pre class="csr-codeblock"><code class="language-bash">')
            lines.append(_escape(s.reproduce_command))
            lines.append("</code></pre>")
            lines.append("</details>")
        if s.how_to_cite:
            lines.append("")
            lines.append(f"Citation: [{s.how_to_cite}]({s.how_to_cite})")
        lines.append("")
        lines.append('<p class="csr-backtop"><a href="#dataset-registry-overview">Back to overview</a></p>')
        lines.append("</section>")

    lines.append("")
    lines.append("## How To Add New Dataset Rows")
    lines.append("")
    lines.append("1. `python -m claimstab.cli run --spec <your_spec.yml> --out-dir output/<run_name> --report`")
    lines.append("2. `python -m claimstab.cli publish-result --run-dir output/<run_name> --atlas-root atlas --contributor <you>`")
    lines.append("3. Rebuild docs after regenerating this page.")
    lines.append("")
    return "\n".join(lines) + "\n"
