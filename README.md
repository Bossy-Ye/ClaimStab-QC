# ClaimStab-QC

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-research%20framework-orange.svg)](#)

ClaimStab-QC is a claim-centric validation framework for checking whether paper-level conclusions remain true under software-visible perturbations in quantum toolchains.

## Quickstart (Paper-First)

Install:
```bash
python -m pip install -e .
```

1) Validate paper spec:
```bash
claimstab validate-spec --spec specs/paper_main.yml
```

2) Run paper preset + HTML report:
```bash
claimstab run --spec specs/paper_main.yml --out-dir output/presentation_large/large/maxcut_ranking --report
```

3) Export paper pack (tables/figures/manifest):
```bash
python -m claimstab.scripts.export_paper_pack --input-root output/presentation_large --out output/paper_pack --which large
```

Optional checks:
- `claimstab validate-evidence --json output/presentation_large/large/maxcut_ranking/claim_stability.json`
- `make reproduce-paper`

## Contribute Your Dataset (3-Minute Path)

Required input contract for `claimstab publish-result`:
- `--run-dir` must contain `claim_stability.json` (required).
- Optional but recommended files in the same directory:
  - `scores.csv`
  - `rq_summary.json`
  - `stability_report.html`

Minimal spec template (required fields):

```yaml
spec_version: 1
pipeline: main
task:
  kind: bv
  suite: core
methods:
  - name: BVOracle
    kind: bv
  - name: RandomBaseline
    kind: random_baseline
claims:
  - type: decision
    method: BVOracle
    top_k: 1
    label_meta_key: target_label
perturbations:
  preset: sampling_only
sampling:
  mode: random_k
  sample_size: 10
  seed: 7
decision_rule:
  threshold: 0.95
  confidence_level: 0.95
backend:
  engine: basic
```

Copy-paste contributor flow:

```bash
claimstab validate-spec --spec specs/atlas_bv_demo.yml
claimstab run --spec specs/atlas_bv_demo.yml --out-dir output/atlas_demo --report
claimstab publish-result --run-dir output/atlas_demo --atlas-root atlas --contributor your_name
claimstab validate-atlas --atlas-root atlas
claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

See full dataset documentation: [`docs/atlas.md`](./docs/atlas.md).

More docs:
- Project website: [ClaimStab-QC](https://bossy-ye.github.io/ClaimStab-QC/)
- Docs quickstart: [Quickstart](https://bossy-ye.github.io/ClaimStab-QC/quickstart/)
- Interactive page: [Playground](https://bossy-ye.github.io/ClaimStab-QC/playground/)
- Public dataset registry: [Dataset Registry](https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/)
- Output directory map: [Output Map](https://bossy-ye.github.io/ClaimStab-QC/output_map/)
- Auto-generated implementation catalog: [Implementation Catalog](https://bossy-ye.github.io/ClaimStab-QC/generated/implementation_catalog/)

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
- `claimstab/pipelines/claim_stability_app.py`: general claim-stability runner (main local entry).
- `examples/exp_comprehensive_calibration.py`: paper calibration batch.
- `examples/exp_comprehensive_large.py`: paper large-scale batch.
- `examples/exp_structural_compilation.py`: structural/compilation track.
- `claimstab/pipelines/multidevice_app.py`: device-aware transpile/noisy extension.
- `claimstab/scripts/export_paper_pack.py`: package an existing run family into paper tables/figures + hash manifest.

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
- Paper scope lock: [`PAPER_SCOPE.md`](./PAPER_SCOPE.md)
- Contributing: [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Extension guide: [`docs/concepts/extending.md`](./docs/concepts/extending.md)
- Naive baseline policies: [`docs/concepts/naive_baseline_policy.md`](./docs/concepts/naive_baseline_policy.md)
- Architecture: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- Implementation catalog: [`docs/generated/implementation_catalog.md`](./docs/generated/implementation_catalog.md)
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
