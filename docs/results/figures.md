# Paper Figures

ClaimStab includes a reproducible paper-figure pipeline that reads experiment artifacts and emits both PDF and PNG files.

## Generate Figures

```bash
make figures
```

For full paper artifact regeneration (experiments + reports + figures):

```bash
make reproduce-paper
```

Equivalent command:

```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.make_paper_figures \
  --input-dir output/paper_artifact/large/maxcut_ranking \
  --also-calibration output/paper_artifact/calibration/maxcut_ranking \
  --output-dir output/paper_artifact/figures/main
```

This is the same target used by `make figures`.

## Figure Set

- Flip-rate heatmaps (per perturbation space).
- Perturbation-attribution bar chart.
- Robustness-map cell-decision chart (RQ5).
- Stratified-decision count chart (RQ6).
- Main-effect ranking chart (RQ7).
- Stability-vs-shots curve (CI-aware).
- CI-width shrink curve (adaptive sampling, when available).
- Naive baseline vs ClaimStab comparison plot.

Generated files are indexed in `output/paper_artifact/figures/main/manifest.json`.

`output/exp_*` figure inputs are still supported for ad-hoc experiments, but canonical paper figures should come from `output/paper_artifact/`.
