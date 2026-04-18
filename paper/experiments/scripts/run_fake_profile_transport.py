from __future__ import annotations

import argparse
import csv
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from claimstab import cli
from claimstab.spec import load_yaml


REPO_ROOT = Path("/Users/mac/Documents/GitHub/ClaimStab-QC")
BASE_SPEC = REPO_ROOT / "paper/experiments/specs/evaluation_v4/d0_bv_iqm_fake_rehearsal.yml"
DEFAULT_RUN_ROOT = REPO_ROOT / "output/paper/evaluation_v4/runs/D0B_profile_transport"
DEFAULT_DATASET_OUT = REPO_ROOT / "output/paper/icse_pack/derived/HW/profile_transport_dataset.csv"
DEFAULT_TABLE_OUT = REPO_ROOT / "output/paper/icse_pack/tables/tab_profile_transport_summary.csv"
DEFAULT_NOTE_OUT = REPO_ROOT / "output/paper/icse_pack/derived/HW/profile_transport_interpretation.md"
DEFAULT_FIGURE_OUT = REPO_ROOT / "output/paper/icse_pack/figures/appendix/fig_profile_transport_map.png"

IQM_PROFILES = (
    ("iqm", "iqm_fake", "IQMFakeAdonis"),
    ("iqm", "iqm_fake", "IQMFakeAphrodite"),
    ("iqm", "iqm_fake", "IQMFakeApollo"),
)
IBM_PROFILES = (
    ("ibm", "ibm_fake", "FakeBrisbane"),
    ("ibm", "ibm_fake", "FakePrague"),
)


@dataclass(frozen=True)
class Profile:
    provider_family: str
    provider: str
    name: str


def _slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def _build_profile_spec(base_spec: dict[str, Any], profile: Profile) -> dict[str, Any]:
    spec = deepcopy(base_spec)
    meta = dict(spec.get("meta", {}))
    meta["name"] = f"evaluation_v4_d0b_bv_profile_transport_{profile.provider_family}_{_slug(profile.name)}"
    meta["description"] = (
        "BV profile-transport run on a fake backend profile before facade and real-hardware execution."
    )
    spec["meta"] = meta
    spec["device_profile"] = {
        "enabled": True,
        "provider": profile.provider,
        "name": profile.name,
        "mode": "noisy_sim",
    }
    spec["backend"] = {"engine": "aer", "noise_model": "from_device_profile"}
    return spec


def _run_profile(base_spec: dict[str, Any], profile: Profile, run_root: Path, *, force: bool) -> Path:
    out_dir = run_root / f"{profile.provider_family}__{_slug(profile.name)}"
    claim_json = out_dir / "claim_stability.json"
    if claim_json.exists() and not force:
        print(f"[skip] {profile.name}: existing run package found at {out_dir}")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="claimstab_profile_") as td:
        spec_path = Path(td) / f"{_slug(profile.name)}.json"
        spec_path.write_text(json.dumps(_build_profile_spec(base_spec, profile), indent=2), encoding="utf-8")
        rc = cli.main(
            [
                "run",
                "--spec",
                str(spec_path),
                "--out-dir",
                str(out_dir),
                "--report",
            ]
        )
    if rc != 0:
        raise RuntimeError(f"Profile run failed for {profile.name} with exit code {rc}.")
    return out_dir


def _extract_rows(profile: Profile, run_dir: Path) -> list[dict[str, Any]]:
    payload = json.loads((run_dir / "claim_stability.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for exp in payload.get("experiments", []):
        claim = exp.get("claim", {})
        sampling = exp.get("sampling", {})
        overall = exp.get("overall", {})
        for delta_row in overall.get("delta_sweep", []):
            if not isinstance(delta_row, dict):
                continue
            decision = delta_row.get("decision")
            if decision is None:
                continue
            top_k = claim.get("top_k")
            claim_id = f"{claim.get('method')}|top_k={top_k}|space={sampling.get('space_preset')}"
            rows.append(
                {
                    "provider_family": profile.provider_family,
                    "provider": profile.provider,
                    "profile_name": profile.name,
                    "run_dir": str(run_dir),
                    "claim_id": claim_id,
                    "claim_label": f"{claim.get('method')} top-{top_k}",
                    "space": sampling.get("space_preset"),
                    "decision": decision,
                    "stability_hat": delta_row.get("stability_hat"),
                    "stability_ci_low": delta_row.get("stability_ci_low"),
                    "stability_ci_high": delta_row.get("stability_ci_high"),
                    "n_claim_evals": delta_row.get("n_claim_evals"),
                    "holds_rate_mean": delta_row.get("holds_rate_mean"),
                    "naive_realistic_comparison": (
                        (delta_row.get("naive_baseline_realistic") or {}).get("comparison")
                    ),
                }
            )
    if not rows:
        raise RuntimeError(f"No decision rows were extracted from {run_dir / 'claim_stability.json'}.")
    return rows


def _classify(decisions: set[str]) -> str:
    clean = {str(d) for d in decisions if d}
    if not clean:
        return "profile_inconclusive"
    if len(clean) == 1 and "inconclusive" not in clean:
        return "profile_robust"
    if len(clean) == 1 and clean == {"inconclusive"}:
        return "profile_inconclusive"
    return "profile_sensitive"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _make_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overall_classes: dict[str, str] = {}
    by_claim: dict[str, set[str]] = {}
    by_claim_family: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        by_claim.setdefault(str(row["claim_id"]), set()).add(str(row["decision"]))
        by_claim_family.setdefault((str(row["provider_family"]), str(row["claim_id"])), set()).add(str(row["decision"]))
    for claim_id, decisions in by_claim.items():
        overall_classes[claim_id] = _classify(decisions)

    table_rows: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: (str(r["claim_id"]), str(r["provider_family"]), str(r["profile_name"]))):
        family_key = (str(row["provider_family"]), str(row["claim_id"]))
        table_rows.append(
            {
                **row,
                "transport_class": overall_classes[str(row["claim_id"])],
                "transport_class_within_family": _classify(by_claim_family[family_key]),
            }
        )
    return table_rows


def _decision_to_int(decision: str) -> int:
    mapping = {"stable": 2, "inconclusive": 1, "unstable": 0}
    return mapping.get(str(decision), 1)


def _render_heatmap(table_rows: list[dict[str, Any]], figure_out: Path) -> None:
    claims = sorted({str(row["claim_label"]) for row in table_rows})
    profiles = sorted(table_rows, key=lambda r: (str(r["provider_family"]), str(r["profile_name"])))
    profile_labels: list[str] = []
    seen: set[tuple[str, str]] = set()
    for row in profiles:
        key = (str(row["provider_family"]), str(row["profile_name"]))
        if key in seen:
            continue
        seen.add(key)
        profile_labels.append(f"{row['provider_family'].upper()}: {row['profile_name']}")

    matrix = []
    for claim in claims:
        row_vals: list[int] = []
        for label in profile_labels:
            family, profile_name = label.split(": ", 1)
            match = next(
                (
                    r
                    for r in table_rows
                    if str(r["claim_label"]) == claim
                    and str(r["provider_family"]).upper() == family
                    and str(r["profile_name"]) == profile_name
                ),
                None,
            )
            row_vals.append(_decision_to_int(str(match["decision"])) if match else 1)
        matrix.append(row_vals)

    figure_out.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = "Times New Roman"
    fig, ax = plt.subplots(figsize=(8.2, 2.8), constrained_layout=True)
    cmap = matplotlib.colors.ListedColormap(["#d9d9d9", "#9e9e9e", "#303030"])
    ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=2)
    ax.set_title("Profile Transport Across Fake Backend Families", fontsize=12)
    ax.set_xlabel("Fake backend profile", fontsize=10)
    ax.set_ylabel("BV decision claim", fontsize=10)
    ax.set_xticks(range(len(profile_labels)))
    ax.set_xticklabels(profile_labels, rotation=20, ha="right", fontsize=9)
    ax.set_yticks(range(len(claims)))
    ax.set_yticklabels(claims, fontsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)

    from matplotlib.patches import Patch

    legend = [
        Patch(facecolor="#303030", edgecolor="none", label="Stable"),
        Patch(facecolor="#d9d9d9", edgecolor="none", label="Unstable"),
        Patch(facecolor="#9e9e9e", edgecolor="none", label="Inconclusive"),
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=9)
    fig.savefig(figure_out, dpi=300, facecolor="white", bbox_inches="tight")
    pdf_out = figure_out.with_suffix(".pdf")
    fig.savefig(pdf_out, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def _recommend_real_iqm(table_rows: list[dict[str, Any]]) -> tuple[bool, str]:
    iqm_rows = [row for row in table_rows if row["provider_family"] == "iqm"]
    if not iqm_rows:
        return False, "No IQM fake rows were produced."
    iqm_decisions = {str(row["decision"]) for row in iqm_rows}
    iqm_classes = {str(row["transport_class_within_family"]) for row in iqm_rows}
    if iqm_classes == {"profile_robust"} and iqm_decisions == {"stable"}:
        return True, (
            "All frozen IQM fake profiles returned stable verdicts for both BV decision claims. "
            "A minimal real-IQM BV slice is low-risk and worth attempting as an appendix-level reality check."
        )
    if "profile_sensitive" in iqm_classes:
        return False, (
            "The IQM fake profiles already show verdict disagreement. "
            "Do not spend real-hardware effort before shrinking the claim set or clarifying the profile-sensitive case."
        )
    return True, (
        "The IQM fake profiles do not show a hard blocker, but the result is not uniformly stable. "
        "A real-IQM slice is still plausible, but it should remain BV-only and appendix-scoped."
    )


def _write_note(note_out: Path, table_rows: list[dict[str, Any]]) -> None:
    note_out.parent.mkdir(parents=True, exist_ok=True)
    by_claim: dict[str, dict[str, Any]] = {}
    for row in table_rows:
        claim_id = str(row["claim_id"])
        item = by_claim.setdefault(
            claim_id,
            {
                "claim_label": row["claim_label"],
                "decisions": [],
                "transport_class": row["transport_class"],
                "iqm_within_family": None,
            },
        )
        item["decisions"].append(f"{row['provider_family']}:{row['profile_name']}={row['decision']}")
        if row["provider_family"] == "iqm":
            item["iqm_within_family"] = row["transport_class_within_family"]

    worth_real, rationale = _recommend_real_iqm(table_rows)
    lines = [
        "# Profile Transport Interpretation",
        "",
        "This study treats fake backend profiles as execution-context substitutions, not as ordinary perturbation knobs.",
        "It does not rank providers and does not substitute for real-hardware validation.",
        "",
        "## Claim-level summary",
        "",
    ]
    for claim_id, item in sorted(by_claim.items()):
        lines.append(f"- `{item['claim_label']}`: `{item['transport_class']}`")
        if item.get("iqm_within_family"):
            lines.append(f"  IQM-family view: `{item['iqm_within_family']}`")
        lines.append(f"  Decisions: {', '.join(item['decisions'])}")
    lines.extend(
        [
            "",
            "## Real-IQM recommendation",
            "",
            f"- `worth_real_iqm = {'yes' if worth_real else 'no'}`",
            f"- {rationale}",
        ]
    )
    note_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run and summarize BV profile transport across fake backend families.")
    parser.add_argument("--base-spec", default=str(BASE_SPEC))
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--dataset-out", default=str(DEFAULT_DATASET_OUT))
    parser.add_argument("--table-out", default=str(DEFAULT_TABLE_OUT))
    parser.add_argument("--note-out", default=str(DEFAULT_NOTE_OUT))
    parser.add_argument("--figure-out", default=str(DEFAULT_FIGURE_OUT))
    parser.add_argument("--force", action="store_true", help="Re-run profile executions even if outputs exist.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    base_spec = load_yaml(args.base_spec)
    run_root = Path(args.run_root)
    profiles = [Profile(*triple) for triple in (*IQM_PROFILES, *IBM_PROFILES)]

    for profile in profiles:
        _run_profile(base_spec, profile, run_root, force=bool(args.force))

    raw_rows: list[dict[str, Any]] = []
    for profile in profiles:
        run_dir = run_root / f"{profile.provider_family}__{_slug(profile.name)}"
        raw_rows.extend(_extract_rows(profile, run_dir))

    dataset_fields = [
        "provider_family",
        "provider",
        "profile_name",
        "run_dir",
        "claim_id",
        "claim_label",
        "space",
        "decision",
        "stability_hat",
        "stability_ci_low",
        "stability_ci_high",
        "n_claim_evals",
        "holds_rate_mean",
        "naive_realistic_comparison",
    ]
    _write_csv(Path(args.dataset_out), raw_rows, dataset_fields)

    table_rows = _make_table_rows(raw_rows)
    table_fields = [
        "provider_family",
        "profile_name",
        "claim_id",
        "claim_label",
        "decision",
        "stability_hat",
        "n_claim_evals",
        "transport_class",
        "transport_class_within_family",
    ]
    _write_csv(Path(args.table_out), table_rows, table_fields)
    _write_note(Path(args.note_out), table_rows)
    _render_heatmap(table_rows, Path(args.figure_out))

    worth_real, rationale = _recommend_real_iqm(table_rows)
    print("Wrote:")
    print(" ", Path(args.dataset_out).resolve())
    print(" ", Path(args.table_out).resolve())
    print(" ", Path(args.note_out).resolve())
    print(" ", Path(args.figure_out).resolve())
    print(json.dumps({"worth_real_iqm": worth_real, "rationale": rationale}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
