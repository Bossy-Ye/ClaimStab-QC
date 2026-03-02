# ClaimStab-QC

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange.svg)](#)

ClaimStab-QC is a claim-centric validation suite for testing whether paper-level conclusions remain true under software-visible perturbations in quantum toolchains.

Project website (GitHub Pages): [https://bossy-ye.github.io/ClaimStab-QC/](https://bossy-ye.github.io/ClaimStab-QC/)

## Why ClaimStab
Most experimental papers report point estimates. ClaimStab evaluates the paper claim itself under perturbation and returns:
1. Stability estimate.
2. Confidence interval.
3. Conservative decision (`stable`, `unstable`, `inconclusive`).

## Core Features
- Claim-level evaluation (`ranking`, plus auxiliary decision/distribution checks).
- Explicit perturbation controls (transpiler seed, optimization level, layout, shots, simulator seed).
- Sampling-aware execution (full-factorial and random-k).
- CI-based conservative decision rule (Wilson interval).
- Failure diagnostics (root-cause by dimension, top unstable configs, lock-down recommendations).
- Stability-vs-cost analysis.
- Task plugin support via spec (`task.kind` built-in or `task.entrypoint` external `module:Class`).
- Multi-device workflow:
  - Tier-1: transpile-only structural metrics.
  - Tier-2: IBM fake backend + Aer noisy simulation.

## Project Layout
```text
claimstab/
  claims/         # claim semantics + stability logic + diagnostics
  perturbations/  # perturbation space + sampling policies
  runners/        # execution backends (Aer/basic)
  devices/        # device profile resolution + IBM fake backend support
  tasks/          # benchmark/task adapters (MaxCut currently)
  scripts/        # report and plotting utilities
examples/
  claim_stability_demo.py
  exp_comprehensive_calibration.py
  exp_comprehensive_large.py
  multidevice_demo.py
  specs/
```

## Quick Start
```bash
python -m pip install -e .
```

Optional extras:
```bash
python -m pip install -e ".[aer,ibm,docs,dev]"
```

Validated Qiskit stack (current `venv`):
- `qiskit==2.2.3`
- `qiskit-aer==0.17.2`
- `qiskit-ibm-runtime==0.45.1`

CLI:
```bash
claimstab --help
claimstab validate-spec --spec specs/paper_main.yml
claimstab run --spec specs/paper_main.yml --out-dir output/paper_main --report
claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy
```

Ready specs:
- `specs/paper_main.yml` (main paper track)
- `specs/paper_device.yml` (multi-device extension)

Run a baseline experiment:
```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite core \
  --space-preset baseline \
  --out-dir output
```

Run the main paper tracks (recommended for submission artifacts):
```bash
PYTHONPATH=. ./venv/bin/python examples/exp_comprehensive_calibration.py
PYTHONPATH=. ./venv/bin/python examples/exp_comprehensive_large.py
```

Run a comprehensive large benchmark directly:
```bash
PYTHONPATH=. ./venv/bin/python examples/claim_stability_demo.py \
  --suite large \
  --space-presets compilation_only,sampling_only,combined_light \
  --claim-pairs "QAOA_p2>RandomBaseline,QAOA_p2>QAOA_p1,QAOA_p1>RandomBaseline" \
  --sampling-mode random_k \
  --sample-size 64 \
  --out-dir output/exp_large
```

Run multi-device experiment:
```bash
PYTHONPATH=. ./venv/bin/python examples/multidevice_demo.py \
  --run all \
  --suite standard \
  --out-dir output/multidevice
```

Evaluation tracks:
- Main paper evaluation: `examples/exp_comprehensive_calibration.py`, `examples/exp_comprehensive_large.py`
- Device-targeted extension: `examples/multidevice_demo.py`

## Outputs
- Main run:
  - `output/scores.csv`
  - `output/claim_stability.json`
- Report:
  - `output/stability_report.html`
  - `output/report_assets/*.png` (with `--with-plots`)
- Multi-device:
  - `output/multidevice/transpile_only/*.json|*.csv`
  - `output/multidevice/noisy_sim/*.json|*.csv`

## Reporting
Generate HTML report:
```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/claim_stability.json \
  --out output/stability_report.html
```

Generate report with plots (headless-safe):
```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcache XDG_CACHE_HOME=/tmp/cache \
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/claim_stability.json \
  --out output/stability_report_plots.html \
  --with-plots
```

## Project Website (MkDocs)
Serve locally:
```bash
make docs-serve
```

Build static site:
```bash
make docs-build
```

## Reproducibility Specs
Template specs:
- [`examples/specs/claim_spec.yaml`](./examples/specs/claim_spec.yaml)
- [`examples/specs/perturbation_spec.yaml`](./examples/specs/perturbation_spec.yaml)

## Community
- Architecture overview: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- Extension guide: [`docs/concepts/extending.md`](./docs/concepts/extending.md)
- Experiment playbook: [`docs/EXPERIMENT_PLAYBOOK.md`](./docs/EXPERIMENT_PLAYBOOK.md)
- Contributing guide: [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)
- Security policy: [`SECURITY.md`](./SECURITY.md)
- Governance: [`GOVERNANCE.md`](./GOVERNANCE.md)
- Changelog: [`CHANGELOG.md`](./CHANGELOG.md)
- Citation metadata: [`CITATION.cff`](./CITATION.cff)

## Development
Run tests:
```bash
PYTHONPATH=. ./venv/bin/python -m pytest -q
```
