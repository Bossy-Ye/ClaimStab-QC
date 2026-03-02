from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from claimstab.utils import _build_diff_matrix, _infer_two_methods, plot_heatmap, plot_scatter


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to scores CSV.")
    ap.add_argument("--out", default=None, help="Output heatmap path (.png/.pdf). Default: <csv_dir>/heatmap.png")
    ap.add_argument(
        "--methods",
        nargs=2,
        default=None,
        metavar=("A", "B"),
        help="Two method names to compare (A B). Default: infer first two sorted.",
    )
    ap.add_argument("--title", default=None, help="Custom heatmap title.")
    ap.add_argument("--dpi", type=int, default=220, help="Figure DPI for raster outputs.")
    ap.add_argument("--scatter", action="store_true", help="Also output a paired A-vs-B scatter plot.")
    ap.add_argument("--scatter_out", default=None, help="Scatter output path. Default: <csv_dir>/scatter.png")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)

    if args.methods is None:
        method_a, method_b = _infer_two_methods(df)
    else:
        method_a, method_b = args.methods[0], args.methods[1]

    diff, seeds, opts = _build_diff_matrix(df, method_a, method_b)

    out_path = Path(args.out) if args.out else (csv_path.parent / "heatmap.png")
    plot_heatmap(
        diff=diff,
        seeds=seeds,
        opts=opts,
        method_a=method_a,
        method_b=method_b,
        out_path=out_path,
        title=args.title,
        dpi=args.dpi,
    )
    print(f"[OK] Heatmap saved to: {out_path}")

    if args.scatter:
        scatter_out = Path(args.scatter_out) if args.scatter_out else (csv_path.parent / "scatter.png")
        plot_scatter(df, method_a, method_b, scatter_out, dpi=args.dpi)
        print(f"[OK] Scatter saved to: {scatter_out}")


if __name__ == "__main__":
    main()
