# Output Directory Map

This page is the single source of truth for where commands write artifacts.

## Canonical Output Roots

- `output/paper_artifact/`: one-command full paper reproduction package.
- `output/presentation/`: curated core package for presentation and quick inspection.
- `output/presentation_large/`: curated extended package (large runs + adaptive add-ons).
- `output/paper_pack/`: lightweight paper-facing export (tables + figures + reproducibility manifest).
- `output/examples/`: community onboarding runs and demos.

Legacy ad-hoc paths (`output/exp_*`) are still supported, but not preferred for submission packaging.

## Script/Spec -> Output Mapping

| Entry point | Recommended command | Output directory |
|---|---|---|
| Full paper reproduction | `make reproduce-paper` | `output/paper_artifact/` |
| Paper pack export (Task 0) | `python -m claimstab.scripts.export_paper_pack --input-root output/presentation_large --which large --out output/paper_pack` | `output/paper_pack/{tables,figures,paper_pack_manifest.json}` |
| Local workspace cleanup | `make clean-local` | Removes local cache/scratch outputs (no canonical source files) |
| Calibration batch | `paper/experiments/scripts/exp_comprehensive_calibration.py --out-dir output/presentation_large/calibration` | `output/presentation_large/calibration/{maxcut_ranking,bv_decision,ghz_structural}` |
| Large batch | `paper/experiments/scripts/exp_comprehensive_large.py --out-dir output/presentation_large/large` | `output/presentation_large/large/{maxcut_ranking,bv_decision,ghz_structural}` |
| Structural benchmark only | `paper/experiments/scripts/exp_structural_compilation.py --out-dir output/paper_artifact/structural` | `output/paper_artifact/structural/` |
| Main spec run | `python -m claimstab.cli run --spec paper/experiments/specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report` | `output/presentation_large/large/maxcut_ranking/` |
| Structural spec run | `python -m claimstab.cli run --spec paper/experiments/specs/paper_structural.yml --out-dir output/paper_artifact/structural --report` | `output/paper_artifact/structural/` |
| Decision spec run | `python -m claimstab.cli run --spec paper/experiments/specs/paper_decision.yml --out-dir output/presentation_large/large/bv_decision --report` | `output/presentation_large/large/bv_decision/` |
| Distribution spec run | `python -m claimstab.cli run --spec paper/experiments/specs/paper_distribution.yml --out-dir output/presentation_large/large/grover_distribution --report` | `output/presentation_large/large/grover_distribution/` |
| Boundary challenge run | `python paper/experiments/scripts/exp_boundary_challenge.py --out output/presentation_large/boundary` | `output/presentation_large/boundary/{run,boundary_summary.json}` |
| Device spec run | `python -m claimstab.cli run --spec paper/experiments/specs/paper_device.yml --out-dir output/multidevice_full` | `output/multidevice_full/` |
| BV + Atlas demo | `python -m claimstab.cli run --spec examples/community/specs/atlas_bv_demo.yml --out-dir output/examples/atlas_bv_demo --report` | `output/examples/atlas_bv_demo/` |
| External task demo | `python -m claimstab.cli run --spec examples/community/custom_task_demo/spec_toy.yml --out-dir output/examples/toy --report` | `output/examples/toy/` |

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

Practicality/performance fields:
- `claim_stability.json -> meta.practicality` includes `num_workers`, `total_wall_time`, `throughput_runs_per_sec`.
- `scores.csv` includes per-row runner timing columns: `transpile_time_ms`, `execute_time_ms`, `wall_time_ms`.

## Atlas Dataset Paths

- Publish command:
```bash
python -m claimstab.cli publish-result --run-dir <run_dir> --atlas-root atlas --contributor <name>
```
- Dataset index:
  - `atlas/index.json`
- Submission package:
  - `atlas/submissions/<submission_id>/`
