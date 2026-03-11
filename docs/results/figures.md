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
PYTHONPATH=. ./.venv/bin/python -m claimstab.scripts.make_paper_figures \
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

## Main-Paper vs Appendix Mapping

Main paper figures (primary evaluation narrative):

- `space_profile_composite_maxcut_ranking`
- `fig_rq5_robustness_map_maxcut_ranking`
- attribution + main-effects composite (`fig_attribution_top_maxcut_ranking` + `fig_rq7_main_effects_maxcut_ranking`)
- `rq4_adaptive/fig_rq4_ci_width_vs_cost` (includes `adaptive_ci_tuned`)

Appendix/default-supplement figures (completeness, controls, or degenerate profiles):

- constant-control GHZ/BV panels
- multidevice heatmaps
- Grover near-constant strips
- remaining per-space heatmaps and auxiliary diagnostics

The paper-pack exporter stages this split automatically into:

- `output/paper_pack/figures/main_paper/`
- `output/paper_pack/figures/appendix/`
- `output/paper_pack/figures/paper_figure_map.json`

`output/exp_*` figure inputs are still supported for ad-hoc experiments, but canonical paper figures should come from `output/paper_artifact/`.

## Figure Quality Audit

For paper-pack outputs, the latest full redesign audit is written to:

- `output/paper_pack/figures/FIGURE_AUDIT_REDESIGN.md`
- before-vs-after examples in `output/paper_pack/figures/redesign_examples/`

Chart-type selection rules are documented in:

- [Figure Policy](figure_policy.md)
