# Paper Figures

The current paper figures are split between:

- the `evaluation_v2` core bundle under `output/paper/evaluation_v2/pack/figures/`
- the `evaluation_v3` strengthening bundle under `output/paper/evaluation_v3/pack/figures/`

## Active Figure Roots

- core main-paper figures: `output/paper/evaluation_v2/pack/figures/main/`
- strengthening figures: `output/paper/evaluation_v3/pack/figures/main/`
- appendix/supporting figures: `output/paper/evaluation_v2/pack/figures/appendix/`
- generated-figure manifest: `output/paper/evaluation_v2/pack/figures/manifest.json`
- figure index: `output/paper/evaluation_v2/pack/figures/README.md`

## Canonical Regeneration Steps

Run the active evaluation bundle:

```bash
python paper/experiments/scripts/reproduce_evaluation_v2.py
python paper/experiments/scripts/exp_rq4_evaluation_v2.py --out output/paper/evaluation_v2/runs/E5_policy_comparison
```

Derive the paper-facing summaries:

```bash
python paper/experiments/scripts/derive_paper_evaluation.py --root output/paper/evaluation_v2
```

Regenerate the publication-focused figure set:

```bash
python paper/experiments/scripts/generate_eval_v2_focus_figures.py --root output/paper/evaluation_v2
python -m claimstab.figures.plot_rq4_adaptive \
  --input output/paper/evaluation_v2/runs/E5_policy_comparison/rq4_policy_summary.json \
  --out output/paper/evaluation_v2/runs/E5_policy_comparison/figures
```

## Main-Paper Figure Set

The current ICSE-style main figure set is:

- `fig1_stability_profile`
- `fig2_robustness_cells_by_delta`
- `fig3_claim_distribution`
- `fig4_e1_prevalence_by_scope`
- `fig5_claim_metric_mismatch`
- `fig6_claim_family_verdicts`
- `fig_rq4_ci_width_vs_cost`

The publication-ready PNG/PDF copies live in:

- `output/paper/evaluation_v2/pack/figures/main/`

The strengthening bundle adds:

- `fig_w1_second_family_verdicts`
- `fig_w3_metric_baseline_sensitivity`
- `fig_w5_near_boundary_tradeoff`

These live in:

- `output/paper/evaluation_v3/pack/figures/main/`

## Figure Roles

- `fig4_e1_prevalence_by_scope`: RQ1 prevalence in the main E1 battleground.
- `fig5_claim_metric_mismatch`: icon figure showing that a supportive metric summary does not imply a stable claim.
- `fig6_claim_family_verdicts`: RQ2 semantic discrimination across ranking, decision, and distribution claims.
- `fig_rq4_ci_width_vs_cost`: RQ4 cost-agreement tradeoff, highlighting `adaptive_ci_tuned`.

## Supporting / Appendix Figures

Supporting figures remain staged under:

- `output/paper/evaluation_v2/pack/figures/appendix/`

These cover:

- E2 GHZ structural calibration
- E3 BV decision calibration
- E4 Grover fragile distribution case
- S2 boundary stress
- QEC portability illustration
- per-experiment heatmaps and robustness/supporting diagnostics

## Scope Note

Legacy figure roots such as `output/paper/artifact/figures/` and `output/paper/pack/figures/` are retired from the active workflow.
The current website and paper narrative should refer to the `evaluation_v2` core bundle plus the `evaluation_v3` strengthening bundle.
