from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claimstab.analysis.paper_claims import generate_paper_claims_outputs
from claimstab.figures.plot_multidevice_heatmap import plot_multidevice_heatmaps
from claimstab.figures.plot_rq4_adaptive import plot_rq4_adaptive


def _safe_git(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _pick_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _csv_safe(value: Any) -> Any:
    if _is_scalar(value):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _flatten_scalars(value: Any, *, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key in sorted(value.keys()):
            child_key = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten_scalars(value.get(key), prefix=child_key))
        return out
    if isinstance(value, list):
        if prefix:
            out[f"{prefix}.count"] = len(value)
        return out
    out[prefix or "value"] = value
    return out


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_safe(row.get(k)) for k in fieldnames})


def _resolve_input_dir(input_root: Path, which: str) -> Path:
    candidate = input_root / which
    if candidate.exists() and candidate.is_dir():
        return candidate
    return input_root


def _run_make_paper_figures(input_dir: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "claimstab.scripts.make_paper_figures",
        "--input-dir",
        str(input_dir),
        "--output-dir",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True)
    return {"command": " ".join(cmd), "manifest": str((out_dir / "manifest.json").resolve())}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Export paper-ready tables/figures + reproducibility manifest.")
    ap.add_argument("--input-root", default="output/presentation_large", help="Root directory holding large/calibration runs.")
    ap.add_argument("--out", default="output/paper_pack", help="Output paper pack directory.")
    ap.add_argument("--which", default="large", choices=["large", "calibration"], help="Which run family to package.")
    ap.add_argument(
        "--paper-claims",
        default="examples/specs/paper_claims.yaml",
        help="Optional paper claims YAML. If it exists, export paper_claims_outcomes.{csv,pdf,png}.",
    )
    ap.add_argument(
        "--paper-claims-input",
        default=None,
        help="Optional claim_stability.json path for paper claims mapping (default: primary selected run).",
    )
    ap.add_argument(
        "--rq4-summary",
        default=None,
        help="Optional path to rq4_adaptive_summary.json. If omitted, exporter auto-detects common locations.",
    )
    ap.add_argument(
        "--multidevice-json",
        default=None,
        help="Optional path to multidevice summary JSON. If omitted, exporter auto-detects common locations.",
    )
    ap.add_argument("--skip-figures", action="store_true", help="Skip figure generation and package only tables/manifest.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    input_root = Path(args.input_root)
    resolved_input_dir = _resolve_input_dir(input_root, args.which)
    out_root = Path(args.out)
    tables_dir = out_root / "tables"
    figures_dir = out_root / "figures"
    out_root.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    claim_paths = sorted(resolved_input_dir.glob("**/claim_stability.json"))
    if not claim_paths:
        raise FileNotFoundError(f"No claim_stability.json found under: {resolved_input_dir}")

    # Build space_claim_delta.csv from a primary run (prefer maxcut_ranking, else max rows).
    claim_payloads: list[tuple[Path, dict[str, Any]]] = [(path, _load_json(path)) for path in claim_paths]
    primary_path: Path | None = None
    primary_rows: list[dict[str, Any]] = []
    for path, payload in claim_payloads:
        rows = payload.get("comparative", {}).get("space_claim_delta", [])
        rows = rows if isinstance(rows, list) else []
        if path.parent.name == "maxcut_ranking" and rows:
            primary_path = path
            primary_rows = [row for row in rows if isinstance(row, dict)]
            break
        if len(rows) > len(primary_rows):
            primary_path = path
            primary_rows = [row for row in rows if isinstance(row, dict)]
    if primary_path is None:
        primary_path = claim_paths[0]

    space_rows: list[dict[str, Any]] = []
    for row in primary_rows:
        normalized = {str(k): _csv_safe(v) for k, v in row.items()}
        normalized["source_run"] = primary_path.parent.name
        normalized["source_claim_json"] = str(primary_path.resolve())
        space_rows.append(normalized)
    space_rows.sort(
        key=lambda r: (
            str(r.get("space_preset", "")),
            str(r.get("claim_pair", "")),
            _as_float(r.get("delta", 0.0)),
        )
    )
    space_csv_path = tables_dir / "space_claim_delta.csv"
    _write_csv(space_rows, space_csv_path)

    # Build rq_summary.csv from all runs in selected family.
    rq_rows: list[dict[str, Any]] = []
    for path, payload in claim_payloads:
        rq_json_path = path.parent / "rq_summary.json"
        if rq_json_path.exists():
            rq_payload = _load_json(rq_json_path)
        else:
            rq_payload = payload.get("rq_summary", {})
            rq_payload = rq_payload if isinstance(rq_payload, dict) else {}
        flat = _flatten_scalars(rq_payload)
        row: dict[str, Any] = {
            "source_run": path.parent.name,
            "source_claim_json": str(path.resolve()),
            "source_rq_json": str(rq_json_path.resolve()) if rq_json_path.exists() else None,
            "num_experiments": len(payload.get("experiments", [])) if isinstance(payload.get("experiments", []), list) else 0,
        }
        row.update({k: _csv_safe(v) for k, v in flat.items()})
        rq_rows.append(row)
    rq_rows.sort(key=lambda r: str(r.get("source_run", "")))
    rq_csv_path = tables_dir / "rq_summary.csv"
    _write_csv(rq_rows, rq_csv_path)

    figure_meta: dict[str, Any] = {"skipped": bool(args.skip_figures)}
    if not args.skip_figures:
        figure_meta = _run_make_paper_figures(resolved_input_dir, figures_dir)

    paper_claims_meta: dict[str, Any] | None = None
    claims_path = Path(args.paper_claims)
    if claims_path.exists():
        paper_claims_input = Path(args.paper_claims_input) if args.paper_claims_input else primary_path
        try:
            paper_claims_meta = generate_paper_claims_outputs(
                claims_path=claims_path,
                input_json=paper_claims_input,
                out_root=out_root,
            )
        except Exception as exc:
            paper_claims_meta = {
                "claims_file": str(claims_path.resolve()),
                "input_json": str(paper_claims_input.resolve()),
                "error": str(exc),
            }

    rq4_meta: dict[str, Any] | None = None
    rq4_summary_path = (
        Path(args.rq4_summary)
        if args.rq4_summary
        else _pick_existing_path(
            [
                input_root / "rq4_adaptive" / "rq4_adaptive_summary.json",
                resolved_input_dir.parent / "rq4_adaptive" / "rq4_adaptive_summary.json",
                Path("output/presentation_large/rq4_adaptive/rq4_adaptive_summary.json"),
            ]
        )
    )
    if rq4_summary_path is not None and rq4_summary_path.exists():
        rq4_payload = _load_json(rq4_summary_path)
        rq4_refs = plot_rq4_adaptive(rq4_payload, figures_dir / "rq4_adaptive")
        copied_summary = tables_dir / "rq4_adaptive_summary.json"
        shutil.copy2(rq4_summary_path, copied_summary)
        rq4_meta = {
            "summary_source": str(rq4_summary_path.resolve()),
            "summary_copy": str(copied_summary.resolve()),
            "figures": rq4_refs,
        }

    multidevice_meta: dict[str, Any] | None = None
    multidevice_json_path = (
        Path(args.multidevice_json)
        if args.multidevice_json
        else _pick_existing_path(
            [
                input_root / "multidevice_full" / "claim_stability.json",
                input_root / "multidevice_full" / "combined_summary.json",
                resolved_input_dir.parent / "multidevice_full" / "claim_stability.json",
                resolved_input_dir.parent / "multidevice_full" / "combined_summary.json",
                Path("output/multidevice_full/claim_stability.json"),
                Path("output/multidevice_full/combined_summary.json"),
                Path("output/multidevice/combined_summary.json"),
            ]
        )
    )
    if multidevice_json_path is not None and multidevice_json_path.exists():
        multidevice_payload = _load_json(multidevice_json_path)
        multidevice_refs = plot_multidevice_heatmaps(multidevice_payload, figures_dir / "multidevice")
        multidevice_meta = {
            "input_json": str(multidevice_json_path.resolve()),
            "figures": multidevice_refs,
        }

    input_files: list[dict[str, Any]] = []
    for path in claim_paths:
        input_files.append(
            {
                "kind": "claim_stability_json",
                "path": str(path.resolve()),
                "sha256": _sha256(path),
            }
        )
        rq_path = path.parent / "rq_summary.json"
        if rq_path.exists():
            input_files.append(
                {
                    "kind": "rq_summary_json",
                    "path": str(rq_path.resolve()),
                    "sha256": _sha256(rq_path),
                }
            )
    if rq4_summary_path is not None and rq4_summary_path.exists():
        input_files.append(
            {
                "kind": "rq4_adaptive_summary_json",
                "path": str(rq4_summary_path.resolve()),
                "sha256": _sha256(rq4_summary_path),
            }
        )
    if multidevice_json_path is not None and multidevice_json_path.exists():
        input_files.append(
            {
                "kind": "multidevice_summary_json",
                "path": str(multidevice_json_path.resolve()),
                "sha256": _sha256(multidevice_json_path),
            }
        )

    manifest = {
        "schema_version": "paper_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _safe_git(["git", "rev-parse", "HEAD"]),
        "source": {
            "input_root": str(input_root.resolve()),
            "which": args.which,
            "resolved_input_dir": str(resolved_input_dir.resolve()),
            "primary_space_claim_source": str(primary_path.resolve()) if primary_path is not None else None,
        },
        "reproduce_command": (
            f"{sys.executable} -m claimstab.scripts.export_paper_pack "
            f"--input-root {args.input_root} --out {args.out} --which {args.which}"
        ),
        "inputs": input_files,
        "outputs": {
            "tables": {
                "space_claim_delta_csv": str(space_csv_path.resolve()),
                "rq_summary_csv": str(rq_csv_path.resolve()),
                "space_claim_delta_rows": len(space_rows),
                "rq_summary_rows": len(rq_rows),
            },
            "figures": figure_meta,
            "paper_claims": paper_claims_meta,
            "rq4_adaptive": rq4_meta,
            "multidevice": multidevice_meta,
        },
    }
    manifest_path = out_root / "paper_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote tables: {tables_dir}")
    if not args.skip_figures:
        print(f"Wrote figures: {figures_dir}")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
