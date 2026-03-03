# Paper Figures

ClaimStab includes a reproducible paper-figure pipeline that reads experiment artifacts and emits both PDF and PNG files.

## Generate Figures

```bash
make figures
```

Equivalent command:

```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.make_paper_figures \
  --input-dir output/exp_comprehensive_large \
  --also-calibration output/exp_comprehensive_calibration \
  --output-dir figures
```

## Figure Set

- Flip-rate heatmaps (per perturbation space).
- Perturbation-attribution bar chart.
- Stability-vs-shots curve (CI-aware).
- CI-width shrink curve (adaptive sampling, when available).
- Naive baseline vs ClaimStab comparison plot.

Generated files are indexed in `figures/manifest.json`.
