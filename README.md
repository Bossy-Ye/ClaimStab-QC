# ClaimStab-QC

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-research%20framework-orange.svg)](#)

ClaimStab-QC is a claim-centric validation methodology for quantum software experiments.

Its central claim is that empirical evaluation often validates outcomes, but not conclusions.

It answers one question: does a formalized reported claim stay true across an admissible perturbation space?

Core verdicts:

- `stable`
- `unstable`
- `inconclusive`

## Start Here

Choose one entry point:

- community use: [docs/design_your_own_case.md](./docs/design_your_own_case.md)
- paper evidence and reruns: [paper/experiments/README.md](./paper/experiments/README.md)
- published docs site: [docs/index.md](./docs/index.md)

## What The Framework Already Provides

ClaimStab already provides:

- perturbation presets
- selection policies such as `full_factorial`, `random_k`, and `adaptive_ci`
- claim inference for `ranking`, `decision`, and `distribution`
- standard outputs:
  - `claim_stability.json`
  - `rq_summary.json`
  - `robustness_map.json`
  - `scores.csv`
  - `stability_report.html`
- evidence validation:
  - `python -m claimstab.cli validate-evidence --json <run_dir>/claim_stability.json`

Canonical schema:

- [claimstab/spec/schema_v1.json](./claimstab/spec/schema_v1.json)

## Minimal Workflow

```bash
python -m pip install -e ".[aer,docs]"
python -m claimstab.cli validate-spec --spec <your_spec.yml>
python -m claimstab.cli run --spec <your_spec.yml> --out-dir output/examples/<your_case> --report
python -m claimstab.cli validate-evidence --json output/examples/<your_case>/claim_stability.json
```

## For Community Users

Use ClaimStab if you want to:

- formalize a ranking, decision, or distribution claim
- evaluate that claim over a declared perturbation space
- generate conservative `stable`, `unstable`, or `inconclusive` verdicts

Active community-facing examples live under:

- [examples/community/README.md](./examples/community/README.md)
- [examples/community/claim_stability_demo.py](./examples/community/claim_stability_demo.py)
- [examples/community/custom_task_demo/spec_toy.yml](./examples/community/custom_task_demo/spec_toy.yml)
- [examples/community/qec_pilot_demo/spec_qec_decoder.yml](./examples/community/qec_pilot_demo/spec_qec_decoder.yml)
- [examples/community/vqe_pilot_demo/spec_vqe_h2.yml](./examples/community/vqe_pilot_demo/spec_vqe_h2.yml)
- [examples/community/max2sat_pilot_demo/spec_max2sat.yml](./examples/community/max2sat_pilot_demo/spec_max2sat.yml)

Community runs should write under:

- `output/examples/...`

## For Paper Readers And Reviewers

Paper-only assets are isolated under:

- [paper/experiments](./paper/experiments)

Active paper output roots:

- `output/paper/evaluation_v2/` for the core paper bundle
- `output/paper/evaluation_v3/` for strengthening studies
- `output/paper/evaluation_v4/` for ICSE-strengthening analyses and hardware slices

If you want the evidence index first, start with:

- [docs/results/main_results.md](./docs/results/main_results.md)
- [docs/results/figures.md](./docs/results/figures.md)
- [docs/experiment_matrix.md](./docs/experiment_matrix.md)

## ICSE 2027 Sprint Lock

For the current paper sprint, the contribution boundary is fixed to:

1. treating reported claims as first-class validation objects
2. making admissible perturbation scope explicit
3. using conservative tri-decision inference
4. emitting explanatory evidence rather than verdicts alone

This sprint does not expand ClaimStab-QC into:

- a full protocol compiler
- a full workflow validation layer
- CI / release-gate infrastructure
- a broad platform redesign

## Advanced Surface

These are kept, but they are not the first-run path:

- [ClaimAtlas guide](./docs/atlas.md)
- [Dataset Registry](https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/)
- [Live Claim Explorer](https://bossy-ye.github.io/ClaimStab-QC/explorer/)

## Scope Notes

- [paper/PAPER_SCOPE.md](./paper/PAPER_SCOPE.md)
- [docs/compatibility_contract.md](./docs/compatibility_contract.md)
