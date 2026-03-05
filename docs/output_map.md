# Output Directory Map

This page is the single source of truth for where commands write artifacts.

## Canonical Output Roots

- `output/paper_artifact/`: one-command full paper reproduction package.
- `output/presentation/`: curated core package for presentation and quick inspection.
- `output/presentation_large/`: curated extended package (large runs + adaptive add-ons).

Legacy ad-hoc paths (`output/exp_*`) are still supported, but not preferred for submission packaging.

## Script/Spec -> Output Mapping

| Entry point | Recommended command | Output directory |
|---|---|---|
| Full paper reproduction | `make reproduce-paper` | `output/paper_artifact/` |
| Calibration batch | `examples/exp_comprehensive_calibration.py --out-dir output/presentation_large/calibration` | `output/presentation_large/calibration/{maxcut_ranking,bv_decision,ghz_structural}` |
| Large batch | `examples/exp_comprehensive_large.py --out-dir output/presentation_large/large` | `output/presentation_large/large/{maxcut_ranking,bv_decision,ghz_structural}` |
| Structural benchmark only | `examples/exp_structural_compilation.py --out-dir output/paper_artifact/structural` | `output/paper_artifact/structural/` |
| Main spec run | `claimstab run --spec specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report` | `output/presentation_large/large/maxcut_ranking/` |
| Structural spec run | `claimstab run --spec specs/paper_structural.yml --out-dir output/paper_artifact/structural --report` | `output/paper_artifact/structural/` |
| Device spec run | `claimstab run --spec specs/paper_device.yml --out-dir output/presentation/device_extension` | `output/presentation/device_extension/` |
| BV + Atlas demo | `claimstab run --spec specs/atlas_bv_demo.yml --out-dir output/atlas_bv_demo --report` | `output/atlas_bv_demo/` |
| External task demo | `claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/sample_problem_demo_run --report` | `output/sample_problem_demo_run/` |

## Figure Generation Targets

| Entry point | Output |
|---|---|
| `make figures` | `output/paper_artifact/figures/main/` |
| `python -m claimstab.scripts.make_paper_figures ... --output-dir output/presentation/figures` | `output/presentation/figures/` |
| `python -m claimstab.scripts.make_paper_figures ... --output-dir output/presentation_large/figures` | `output/presentation_large/figures/` |

## Report Files (per run directory)

Each run directory typically contains:
- `scores.csv`
- `claim_stability.json`
- `rq_summary.json`
- `stability_report.html`
- optional `report_assets/*.png`
- optional reproducibility artifacts: `trace.jsonl`, `events.jsonl`, `cache.sqlite`

## Atlas Dataset Paths

- Publish command:
```bash
claimstab publish-result --run-dir <run_dir> --atlas-root atlas --contributor <name>
```
- Dataset index:
  - `atlas/index.json`
- Submission package:
  - `atlas/submissions/<submission_id>/`
