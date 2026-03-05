from __future__ import annotations

import argparse
import json
from pathlib import Path

from claimstab.results.report_builder import build_report_html
from claimstab.results.report_sections import available_sections_text, parse_sections_arg


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate an HTML claim-stability report from JSON output")
    ap.add_argument("--json", required=True, help="Path to rankflip JSON artifact")
    ap.add_argument("--out", default=None, help="Output HTML path; default: <json_dir>/stability_report.html")
    ap.add_argument("--assets-dir", default=None, help="Directory for generated plot assets")
    ap.add_argument("--with-plots", action="store_true", help="Attempt to render plot images (requires matplotlib/font support)")
    ap.add_argument(
        "--sections",
        default="",
        help=(
            "Optional comma-separated section ids. If empty, default layout is unchanged. "
            f"Available ids: {available_sections_text()}."
        ),
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    selected_sections = parse_sections_arg(args.sections)

    json_path = Path(args.json)
    out_path = Path(args.out) if args.out else (json_path.parent / "stability_report.html")
    assets_dir = Path(args.assets_dir) if args.assets_dir else (json_path.parent / "report_assets")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    report_html = build_report_html(
        payload=payload,
        out_path=out_path,
        assets_dir=assets_dir,
        with_plots=args.with_plots,
        selected_sections=selected_sections,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_html, encoding="utf-8")

    print("Wrote:")
    print(" ", out_path.resolve())


if __name__ == "__main__":
    main()
