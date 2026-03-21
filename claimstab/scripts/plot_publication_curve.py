from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from claimstab.figures.style import FIG_H_WIDE, FIG_W_WIDE, add_reference_lines, apply_style, plot_line_with_ci, save_fig


def _resolve_json_path(payload: Any, path_expr: str | None) -> Any:
    if not path_expr:
        return payload
    current: Any = payload
    for token in path_expr.split("."):
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(f"JSON path token not found: {token}")
            current = current[token]
            continue
        if isinstance(current, list):
            idx = int(token)
            current = current[idx]
            continue
        raise KeyError(f"Cannot descend into non-container at token: {token}")
    return current


def load_frame(input_path: Path, *, json_path: str | None) -> pd.DataFrame:
    suffix = input_path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(input_path)
    if suffix in {".json", ".jsonl"}:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        rows = _resolve_json_path(payload, json_path)
        if isinstance(rows, list):
            return pd.DataFrame(rows)
        if isinstance(rows, dict):
            return pd.DataFrame([rows])
        raise ValueError(f"Resolved JSON payload must be list/object, got {type(rows).__name__}")
    raise ValueError(f"Unsupported input format: {input_path.suffix}")


def plot_publication_curve(
    frame: pd.DataFrame,
    *,
    out_base: Path,
    x_col: str,
    y_col: str,
    ci_low_col: str,
    ci_high_col: str,
    x_label: str,
    y_label: str,
    title: str | None,
    event_x: float | None,
    zero_y: float | None,
    sort_by_x: bool,
) -> dict[str, str]:
    required = {x_col, y_col, ci_low_col, ci_high_col}
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise KeyError(f"Missing required columns: {', '.join(missing)}")

    data = frame[[x_col, y_col, ci_low_col, ci_high_col]].copy()
    data[x_col] = pd.to_numeric(data[x_col], errors="coerce")
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data[ci_low_col] = pd.to_numeric(data[ci_low_col], errors="coerce")
    data[ci_high_col] = pd.to_numeric(data[ci_high_col], errors="coerce")
    data = data.dropna(subset=[x_col, y_col, ci_low_col, ci_high_col])
    if sort_by_x:
        data = data.sort_values(x_col)
    if data.empty:
        raise ValueError("No valid rows to plot after numeric conversion/filtering.")

    x = data[x_col].astype(float).tolist()
    y = data[y_col].astype(float).tolist()
    ci_low = data[ci_low_col].astype(float).tolist()
    ci_high = data[ci_high_col].astype(float).tolist()

    apply_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(FIG_W_WIDE, FIG_H_WIDE), layout="constrained")
    plot_line_with_ci(
        ax,
        x=x,
        y=y,
        ci_low=ci_low,
        ci_high=ci_high,
        label=y_label,
        ci_label="confidence interval",
    )
    add_reference_lines(ax, event_x=event_x, zero_y=zero_y)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        ax.set_title(title)
    ax.legend(loc="best")
    return save_fig(fig, out_base)


def apply_filters(frame: pd.DataFrame, filters: list[str]) -> pd.DataFrame:
    out = frame
    for rule in filters:
        if "=" not in rule:
            raise ValueError(f"Invalid --filter rule (expected key=value): {rule}")
        key, value = rule.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in out.columns:
            raise KeyError(f"Filter column not found: {key}")
        out = out[out[key].astype(str) == value]
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create a publication-style line+CI figure from CSV/JSON result data.")
    ap.add_argument("--input", required=True, help="Input CSV/JSON data file.")
    ap.add_argument("--json-path", default=None, help="Optional dot path into JSON payload (e.g., experiments.0.rows).")
    ap.add_argument("--x-col", default="x", help="Column name for x axis.")
    ap.add_argument("--y-col", default="y", help="Column name for main curve values.")
    ap.add_argument("--ci-low-col", default="ci_low", help="Column name for lower CI bound.")
    ap.add_argument("--ci-high-col", default="ci_high", help="Column name for upper CI bound.")
    ap.add_argument("--x-label", default="x")
    ap.add_argument("--y-label", default="estimate")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", default="figure", help="Output base path (without extension).")
    ap.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Optional row filter key=value (repeatable), e.g. --filter space_preset=sampling_only",
    )
    ap.add_argument("--event-x", type=float, default=0.0, help="Vertical dashed event line x-position.")
    ap.add_argument("--zero-y", type=float, default=0.0, help="Horizontal zero-line y-position.")
    ap.add_argument("--no-event-line", action="store_true", help="Disable event line.")
    ap.add_argument("--no-zero-line", action="store_true", help="Disable horizontal zero line.")
    ap.add_argument("--no-sort-x", action="store_true", help="Keep row order instead of sorting by x.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    frame = load_frame(input_path, json_path=args.json_path)
    frame = apply_filters(frame, list(args.filter))
    refs = plot_publication_curve(
        frame,
        out_base=Path(args.out),
        x_col=args.x_col,
        y_col=args.y_col,
        ci_low_col=args.ci_low_col,
        ci_high_col=args.ci_high_col,
        x_label=args.x_label,
        y_label=args.y_label,
        title=args.title,
        event_x=None if args.no_event_line else float(args.event_x),
        zero_y=None if args.no_zero_line else float(args.zero_y),
        sort_by_x=not bool(args.no_sort_x),
    )
    print("Wrote figure files:")
    print(" ", refs["pdf"])
    print(" ", refs["png"])


if __name__ == "__main__":
    main()
