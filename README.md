# ClaimStab-QC

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-research%20framework-orange.svg)](#)

ClaimStab-QC is a claim-centric validation framework for checking whether paper-level conclusions remain true under software-visible perturbations in quantum toolchains.

## Start Here
- Project website: [ClaimStab-QC](https://bossy-ye.github.io/ClaimStab-QC/)
- Docs quickstart: [Quickstart](https://bossy-ye.github.io/ClaimStab-QC/quickstart/)
- Interactive page: [Playground](https://bossy-ye.github.io/ClaimStab-QC/playground/)
- Public dataset registry: [Dataset Registry](https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/)
- Output directory map: [Output Map](https://bossy-ye.github.io/ClaimStab-QC/output_map/)

## Why ClaimStab
Most papers report point estimates. ClaimStab evaluates the claim itself and returns:
1. Stability estimate.
2. Confidence interval.
3. Conservative decision (`stable`, `unstable`, `inconclusive`).

Conservative rule:
- `stable` iff `CI_low >= threshold`
- `unstable` iff `CI_high < threshold`
- otherwise `inconclusive`

## What You Need (Input) vs What You Get (Output)

### Input (from user)
1. A task plugin (`task.kind` built-in or `task.entrypoint` external `module:Class`).
2. A spec YAML (methods, claims, perturbations, sampling, decision rule).

### Output (from ClaimStab)
1. `scores.csv` (raw method-by-config outcomes).
2. `claim_stability.json` (stability stats, CI, decisions, diagnostics).
3. `stability_report.html` (human-readable report).
4. Optional reproducibility artifacts:
- `trace.jsonl`
- `events.jsonl`
- `cache.sqlite`

## 5-Minute Quick Run

Install:
```bash
python -m pip install -e .
```

Optional extras:
```bash
python -m pip install -e ".[aer,ibm,docs,dev]"
```

Validate a paper spec:
```bash
claimstab validate-spec --spec specs/paper_main.yml
```

Run and build report:
```bash
claimstab run --spec specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report
```

Publish run to Atlas dataset:
```bash
claimstab publish-result --run-dir output/presentation_large/large/maxcut_ranking --atlas-root atlas --contributor your_name
```

## Choose Your Path

### A) Paper Reproduction
One command for experiments + reports + figures + manifest:
```bash
make reproduce-paper
```

### B) Custom Task (not MaxCut)
Generate skeleton, run, and report:
```bash
claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo
claimstab run --spec examples/my_problem_demo/spec_my_problem.yml --out-dir output/my_problem --report
```

### C) Multi-Device Extension
```bash
PYTHONPATH=. ./venv/bin/python examples/multidevice_demo.py \
  --run all \
  --suite standard \
  --out-dir output/multidevice
```

## Core Capabilities
- Claim evaluation: ranking + decision + distribution pathways.
- Perturbation controls: transpiler seed, optimization level, layout, shots, simulator seed.
- Sampling policies: full-factorial, random-k, adaptive CI-width stopping.
- CI-based conservative inference (Wilson default, clustered stability support, pluggable inference policy).
- Diagnostics: factor attribution, top unstable configs, lock-down recommendations.
- Stability-vs-cost analysis (shots/CI-aware decision view).
- Device-aware workflows:
  - `transpile_only` structural metrics across device profiles.
  - `noisy_sim` with IBM fake backends + Aer (optional extras).
- Atlas dataset workflow: publish, validate, compare, and export website registry.

## Repository Structure

```text
claimstab/                  # framework source code
  claims/                   # claim semantics, stability, diagnostics
  inference/                # inference policies (Wilson, Bayesian, etc.)
  perturbations/            # spaces, sampling, operator shim
  tasks/                    # built-in tasks + plugin base/registry/factory
  runners/                  # execution backends
  devices/                  # device profile resolution
  atlas/                    # atlas helpers (publish, compare, export)
  scripts/                  # report and figure generators
  tests/                    # test suites
examples/                   # runnable experiment scripts
specs/                      # ready-to-run spec files
atlas/                      # public dataset index + submissions
output/                     # generated experiment outputs
  presentation/             # frozen submission package (core)
  presentation_large/       # frozen submission package (extended)
  paper_artifact/           # one-command full reproduction package
docs/                       # MkDocs website source
```

## Output Convention

Preferred artifact roots:
- `output/paper_artifact/` from `make reproduce-paper`
- `output/presentation/` for core curated presentation results
- `output/presentation_large/` for extended curated presentation results

`output/exp_*` paths are still supported for ad-hoc local runs, but are considered legacy for paper packaging.

## Main Scripts and Their Roles
- `examples/claim_stability_demo.py`: general claim-stability runner (main local entry).
- `examples/exp_comprehensive_calibration.py`: paper calibration batch.
- `examples/exp_comprehensive_large.py`: paper large-scale batch.
- `examples/exp_structural_compilation.py`: structural/compilation track.
- `examples/multidevice_demo.py`: device-aware transpile/noisy extension.

## Specs You Can Run Immediately
- [`specs/paper_main.yml`](./specs/paper_main.yml): main paper track.
- [`specs/paper_structural.yml`](./specs/paper_structural.yml): structural compilation track.
- [`specs/paper_device.yml`](./specs/paper_device.yml): multi-device extension.
- [`specs/atlas_bv_demo.yml`](./specs/atlas_bv_demo.yml): BV dataset workflow demo.

## Report and Figures
Generate HTML report from JSON:
```bash
PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/presentation_large/large/maxcut_ranking/claim_stability.json \
  --out output/presentation_large/large/maxcut_ranking/stability_report.html
```

Generate report with plots:
```bash
MPLBACKEND=Agg PYTHONPATH=. ./venv/bin/python -m claimstab.scripts.generate_stability_report \
  --json output/presentation_large/large/maxcut_ranking/claim_stability.json \
  --out output/presentation_large/large/maxcut_ranking/stability_report_plots.html \
  --with-plots
```

## Trace, Cache, Replay
Use trace/cache for reproducible incremental runs:
- Docs page: [Trace Cache Replay](https://bossy-ye.github.io/ClaimStab-QC/trace_cache_replay/)
- Local source: [`docs/trace_cache_replay.md`](./docs/trace_cache_replay.md)

## ClaimAtlas (Public Dataset)
- Atlas docs: [`docs/atlas.md`](./docs/atlas.md)
- Atlas index: [`atlas/index.json`](./atlas/index.json)
- Submission packages: [`atlas/submissions/`](./atlas/submissions)

Export website dataset registry page:
```bash
claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

Validate dataset integrity:
```bash
claimstab validate-atlas --atlas-root atlas
```

## Community and Contribution
- Contributing: [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Extension guide: [`docs/concepts/extending.md`](./docs/concepts/extending.md)
- Architecture: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- Experiment playbook: [`docs/EXPERIMENT_PLAYBOOK.md`](./docs/EXPERIMENT_PLAYBOOK.md)
- Threats to validity: [`docs/concepts/threats_to_validity.md`](./docs/concepts/threats_to_validity.md)
- Changelog: [`CHANGELOG.md`](./CHANGELOG.md)
- Citation metadata: [`CITATION.cff`](./CITATION.cff)

## Development
Run tests:
```bash
PYTHONPATH=. ./venv/bin/python -m pytest -q
```

Build docs:
```bash
make docs-build
```

## Current validated stack
- `qiskit==2.2.3`
- `qiskit-aer==0.17.2`
- `qiskit-ibm-runtime==0.45.1`
