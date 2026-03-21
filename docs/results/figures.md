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
  --input-dir output/paper/artifact/large/maxcut_ranking \
  --also-calibration output/paper/artifact/calibration/maxcut_ranking \
  --output-dir output/paper/artifact/figures/main
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

Generated files are indexed in `output/paper/artifact/figures/main/manifest.json`.

## Main-Paper vs Appendix Mapping

Main paper figures (primary evaluation narrative; RQ1-RQ4):

- `fig1_stability_profile` (RQ1: prevalence + space dependence)
- `fig2_robustness_cells_by_delta` (RQ2-supporting robustness contrast used in the main figure set)
- `fig3_claim_distribution` (RQ3: robust vs fragile claim types across tasks)
- `fig4_cost_confidence_tradeoff` (RQ4: cost-confidence tradeoff with tuned adaptive run)

RQ2 appears in the mechanism figures as sub-analyses:

- attribution drivers (`fig_attribution_top_*`)
- interaction/main-effect diagnostics (`fig_rq7_main_effects_*`)
- robustness boundaries (`fig_rq5_robustness_map_*`)

Appendix/default-supplement figures (completeness, controls, or degenerate profiles):

- constant-control GHZ/BV panels
- multidevice heatmaps
- Grover near-constant strips
- remaining per-space heatmaps and auxiliary diagnostics

The paper-pack exporter stages this split automatically into:

- `output/paper/pack/figures/main/`
- `output/paper/pack/figures/appendix/`
- `output/paper/pack/figures/paper_figure_map.json`

`output/exp_*` figure inputs are still supported for ad-hoc experiments, but canonical paper figures should come from `output/paper/artifact/`.

## Figure Quality Audit

For paper-pack outputs, the legacy redesign audit material is archived at:

- `output/paper/pack/figures/_archive_legacy/root_files/FIGURE_AUDIT_REDESIGN.md`
- before-vs-after examples in `output/paper/pack/figures/_archive_legacy/dirs/redesign_examples/`

Chart-type selection rules are documented in the plotting code under `claimstab/figures/` and test coverage in `claimstab/tests/`.
