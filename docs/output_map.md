# Output Directory Map

This page is the single source of truth for where active commands write artifacts.

## Canonical Output Roots

- `output/paper/evaluation_v2/`: active paper-facing experiment bundle
- `output/examples/`: lightweight onboarding and community examples
- `output/demos/`: exploratory local demos
- `output/tmp_smoke/`: disposable validation runs

Retired from the active workflow:

- `output/presentations/`
- `output/paper/artifact/`
- `output/paper/pack/`
- `output/paper/multidevice/`

## Category Semantics

- `paper/evaluation_v2`: canonical runs, derived tables, and figure pack used in the current paper narrative
- `examples`: user-facing demos that do not depend on the full paper bundle
- `demos`: scratch or interactive local runs
- `tmp_smoke`: disposable validation outputs

## Script / Spec -> Output Mapping

| Entry point | Recommended command | Output directory |
|---|---|---|
| layout scaffold | `python paper/experiments/scripts/reproduce_evaluation_v2.py --layout-only` | `output/paper/evaluation_v2/{runs,derived_paper_evaluation,pack,manifests}` |
| E1 main run | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main --report` | `output/paper/evaluation_v2/runs/E1_maxcut_main/` |
| E2 GHZ run | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e2_ghz_structural.yml --out-dir output/paper/evaluation_v2/runs/E2_ghz_structural --report` | `output/paper/evaluation_v2/runs/E2_ghz_structural/` |
| E3 BV run | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e3_bv_decision.yml --out-dir output/paper/evaluation_v2/runs/E3_bv_decision --report` | `output/paper/evaluation_v2/runs/E3_bv_decision/` |
| E4 Grover run | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e4_grover_distribution.yml --out-dir output/paper/evaluation_v2/runs/E4_grover_distribution --report` | `output/paper/evaluation_v2/runs/E4_grover_distribution/` |
| S2 boundary run | `python paper/experiments/scripts/exp_boundary_challenge.py --spec paper/experiments/specs/evaluation_v2/s2_boundary.yml --out output/paper/evaluation_v2/runs/S2_boundary` | `output/paper/evaluation_v2/runs/S2_boundary/` |
| QEC portability run | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/qec_portability.yml --out-dir output/paper/evaluation_v2/runs/QEC_portability --report` | `output/paper/evaluation_v2/runs/QEC_portability/` |
| E5 policy comparison | `python paper/experiments/scripts/exp_rq4_evaluation_v2.py --out output/paper/evaluation_v2/runs/E5_policy_comparison` | `output/paper/evaluation_v2/runs/E5_policy_comparison/` |
| S1 structural portability | `python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/s1_multidevice_portability.yml --out-dir output/paper/evaluation_v2/runs/S1_multidevice_portability` | `output/paper/evaluation_v2/runs/S1_multidevice_portability/` |
| derive paper summaries | `python paper/experiments/scripts/derive_paper_evaluation.py --root output/paper/evaluation_v2` | `output/paper/evaluation_v2/derived_paper_evaluation/` |
| focus figures | `python paper/experiments/scripts/generate_eval_v2_focus_figures.py --root output/paper/evaluation_v2` | `output/paper/evaluation_v2/pack/figures/main/` |
| RQ4 figures | `python -m claimstab.figures.plot_rq4_adaptive --input output/paper/evaluation_v2/runs/E5_policy_comparison/rq4_policy_summary.json --out output/paper/evaluation_v2/runs/E5_policy_comparison/figures` | `output/paper/evaluation_v2/runs/E5_policy_comparison/figures/` |
| community demo | `python examples/community/claim_stability_demo.py ...` | `output/examples/claim_stability_demo/` |
| QEC demo | `python -m claimstab.cli run --spec examples/community/qec_pilot_demo/spec_qec_decoder.yml --out-dir output/examples/qec_pilot_demo --report` | `output/examples/qec_pilot_demo/` |

## Figure Targets

| Figure bundle | Output |
|---|---|
| main paper figures | `output/paper/evaluation_v2/pack/figures/main/` |
| appendix/supporting figures | `output/paper/evaluation_v2/pack/figures/appendix/` |
| figure manifest | `output/paper/evaluation_v2/pack/figures/manifest.json` |

## Per-Run Report Files

Each run directory typically contains:

- `scores.csv`
- `claim_stability.json`
- `rq_summary.json`
- `stability_report.html`
- optional figure/report assets

Additional bundle-level outputs:

- `derived_paper_evaluation/` for paper-facing tables and JSON summaries
- `pack/figures/` for the curated figure bundle
- `manifests/` for execution plan and completion status

## Practicality Metadata

- `claim_stability.json -> meta.practicality` includes bundle-level wall-clock information
- `scores.csv` includes per-row timing columns such as `transpile_time_ms`, `execute_time_ms`, and `wall_time_ms`
