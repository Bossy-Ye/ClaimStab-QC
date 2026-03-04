from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _resolve_claim_json(path: str | Path) -> Path:
    src = Path(path)
    if src.is_dir():
        candidate = src / "claim_stability.json"
        if not candidate.exists():
            raise ValueError(f"Directory does not contain claim_stability.json: {src}")
        return candidate
    if src.suffix.lower() == ".json" and src.exists():
        return src
    raise ValueError(f"Expected a run directory or JSON file path, got: {src}")


def _load_payload(path: str | Path) -> tuple[Path, dict[str, Any]]:
    json_path = _resolve_claim_json(path)
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to load JSON from {json_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid payload (not object): {json_path}")
    return json_path, payload


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("claim_type", "ranking")),
        str(row.get("space_preset", "")),
        str(row.get("claim_pair", "")),
        str(row.get("metric_name", "objective")),
        str(row.get("delta")),
    )


def _rows_by_key(payload: dict[str, Any]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    comparative = payload.get("comparative", {})
    if not isinstance(comparative, dict):
        return {}
    rows = comparative.get("space_claim_delta", [])
    if not isinstance(rows, list):
        return {}
    out: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        out[_row_key(row)] = row
    return out


def compare_claim_outputs(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_path, left_payload = _load_payload(left)
    right_path, right_payload = _load_payload(right)

    left_rows = _rows_by_key(left_payload)
    right_rows = _rows_by_key(right_payload)
    left_keys = set(left_rows.keys())
    right_keys = set(right_rows.keys())
    paired_keys = sorted(left_keys & right_keys)

    per_row: list[dict[str, Any]] = []
    decision_changed_count = 0
    naive_changed_count = 0
    flip_deltas: list[float] = []
    stability_deltas: list[float] = []

    for key in paired_keys:
        left_row = left_rows[key]
        right_row = right_rows[key]
        left_decision = str(left_row.get("decision"))
        right_decision = str(right_row.get("decision"))
        decision_changed = left_decision != right_decision
        if decision_changed:
            decision_changed_count += 1

        left_naive = left_row.get("naive_baseline", {})
        right_naive = right_row.get("naive_baseline", {})
        left_naive_cmp = str(left_naive.get("comparison")) if isinstance(left_naive, dict) else None
        right_naive_cmp = str(right_naive.get("comparison")) if isinstance(right_naive, dict) else None
        naive_changed = left_naive_cmp != right_naive_cmp
        if naive_changed:
            naive_changed_count += 1

        left_flip = _as_float(left_row.get("flip_rate_mean"))
        right_flip = _as_float(right_row.get("flip_rate_mean"))
        flip_delta = None
        if left_flip is not None and right_flip is not None:
            flip_delta = right_flip - left_flip
            flip_deltas.append(flip_delta)

        left_stability = _as_float(left_row.get("stability_hat"))
        right_stability = _as_float(right_row.get("stability_hat"))
        stability_delta = None
        if left_stability is not None and right_stability is not None:
            stability_delta = right_stability - left_stability
            stability_deltas.append(stability_delta)

        per_row.append(
            {
                "claim_type": key[0],
                "space_preset": key[1],
                "claim_pair": key[2],
                "metric_name": key[3],
                "delta": key[4],
                "left_decision": left_decision,
                "right_decision": right_decision,
                "decision_changed": decision_changed,
                "left_naive_comparison": left_naive_cmp,
                "right_naive_comparison": right_naive_cmp,
                "naive_comparison_changed": naive_changed,
                "flip_rate_mean_delta": flip_delta,
                "stability_hat_delta": stability_delta,
            }
        )

    left_meta = left_payload.get("meta", {}) if isinstance(left_payload.get("meta"), dict) else {}
    right_meta = right_payload.get("meta", {}) if isinstance(right_payload.get("meta"), dict) else {}

    def _avg(vals: list[float]) -> float | None:
        if not vals:
            return None
        return sum(vals) / len(vals)

    return {
        "left_source": str(left_path),
        "right_source": str(right_path),
        "left_task": left_meta.get("task"),
        "right_task": right_meta.get("task"),
        "left_suite": left_meta.get("suite"),
        "right_suite": right_meta.get("suite"),
        "paired_rows": len(paired_keys),
        "left_only_keys": [list(k) for k in sorted(left_keys - right_keys)],
        "right_only_keys": [list(k) for k in sorted(right_keys - left_keys)],
        "decision_changed_count": decision_changed_count,
        "naive_comparison_changed_count": naive_changed_count,
        "mean_flip_rate_delta": _avg(flip_deltas),
        "mean_stability_hat_delta": _avg(stability_deltas),
        "rows": per_row,
    }
