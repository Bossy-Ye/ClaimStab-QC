# ClaimStab-QC

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-research%20framework-orange.svg)](#)

ClaimStab-QC is a claim-centric framework for checking whether paper conclusions remain valid under software-visible perturbations in quantum software pipelines.

Repository scope note: this repository surface is broader than the accompanying paper scope. The paper intentionally focuses on the fully validated methodological core; broader infrastructure is kept for reproducibility and future community adoption. See [paper/PAPER_SCOPE.md](./paper/PAPER_SCOPE.md).

## What Problem It Solves

Most quantum-software papers report conclusions from one or a few configurations. ClaimStab-QC tests those conclusions across controlled perturbation spaces, quantifies uncertainty with confidence intervals, and returns conservative decisions:

- `stable`: CI lower bound >= threshold
- `unstable`: CI upper bound < threshold
- `inconclusive`: otherwise

## Who It Is For

- Researchers validating paper claims (research-artifact reproducibility)
- Contributors adding new tasks/methods with a fixed spec contract
- Advanced users comparing datasets through ClaimAtlas

## Supported Claim Types (Current)

Claim taxonomy is fixed by spec schema v1:

- `ranking`: compare method A vs method B with margin `delta`
- `decision`: check whether target label remains in top-k
- `distribution`: check distance-to-reference within `epsilon` (JS/TVD)

Canonical schema: [claimstab/spec/schema_v1.json](./claimstab/spec/schema_v1.json)

## Stable vs Experimental

Stable interfaces (backward-compatible contract):

- Canonical CLI path:
  - `python -m claimstab.cli ...`
- Core artifact names in run directories:
  - `claim_stability.json`, `rq_summary.json`, `robustness_map.json`, `scores.csv`
- Report artifact:
  - `stability_report.html`
- Evidence compatibility:
  - CEP fields under `experiments[*].evidence.cep`

Advanced/experimental surface (kept, but not primary onboarding path):

- Live Claim Explorer (advanced exploration surface): [GitHub Pages](https://bossy-ye.github.io/ClaimStab-QC/explorer/)
- Dataset Registry / ClaimAtlas browsing (community-facing infrastructure surface): [GitHub Pages](https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/)
- Optional multidevice/noisy simulation extensions

Full contract: [docs/compatibility_contract.md](./docs/compatibility_contract.md)

## 5-Minute Quickstart (Canonical Path)

1. Install:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

2. Validate and run the active evaluation rerun scaffold:

```bash
python -m claimstab.cli validate-spec --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml
python -m claimstab.cli run --spec paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml --out-dir output/paper/evaluation_v2/runs/E1_maxcut_main --report
```

3. Validate evidence links:

```bash
python -m claimstab.cli validate-evidence --json output/paper/evaluation_v2/runs/E1_maxcut_main/claim_stability.json
```

Only this CLI path is recommended for first-time onboarding. Pipeline module entrypoints are available for advanced/internal workflows (see below).

## Minimal Input Spec

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

## Key Outputs and How To Interpret Them

Main outputs under `--out-dir`:

- `claim_stability.json`: per-experiment claim outcomes, CI, decision, CEP trace links
- `rq_summary.json`: aggregate research-question summaries and diagnostics
- `robustness_map.json`: conditional stability cells, robust core, frontier, lockdown hints
- `scores.csv`: raw per-evaluation rows and runner timing fields
- `stability_report.html`: human-readable report

Decision semantics (same everywhere):

- `stable`: evidence supports claim preservation at configured confidence
- `unstable`: evidence rejects claim preservation at configured confidence
- `inconclusive`: current budget/evidence cannot decide conservatively

## Start Here Links

- Docs home: [ClaimStab-QC website](https://bossy-ye.github.io/ClaimStab-QC/)
- Quickstart: [docs/quickstart.md](./docs/quickstart.md)
- Experiment matrix (locked): [docs/experiment_matrix.md](./docs/experiment_matrix.md)
- Output map: [docs/output_map.md](./docs/output_map.md)
- Reproduction commands: [docs/reproduce.md](./docs/reproduce.md)

## Community Examples

Use these first for onboarding and external contributions:

- [examples/community](./examples/community)
- [examples/community/README.md](./examples/community/README.md)
- [examples/community/specs/atlas_bv_demo.yml](./examples/community/specs/atlas_bv_demo.yml)
- [examples/community/custom_task_demo/spec_toy.yml](./examples/community/custom_task_demo/spec_toy.yml)

Community runs should write under `output/examples/...` (for example `output/examples/quickstart`).

## Paper Experiments

Paper-only evaluation assets are isolated under:

- [paper/experiments](./paper/experiments)
- [paper/experiments/README.md](./paper/experiments/README.md)
- [paper/experiments/specs](./paper/experiments/specs)
- [paper/experiments/scripts](./paper/experiments/scripts)

Paper reruns should write under `output/paper/evaluation_v2/...`.
Legacy paper output roots such as `output/presentations/large`, `output/paper/artifact`, and `output/paper/pack` have been retired from the active workflow.

Recommended `output/` layout:
- `output/examples/` for onboarding/community runs
- `output/paper/evaluation_v2/` for the active paper evaluation bundle
- `output/demos/` for local exploratory checks

## Advanced / Community-Facing Capabilities

- Live Claim Explorer: [GitHub Pages](https://bossy-ye.github.io/ClaimStab-QC/explorer/)
- Dataset Registry: [GitHub Pages](https://bossy-ye.github.io/ClaimStab-QC/dataset_registry/)
- ClaimAtlas guide (advanced dataset/publication workflow): [GitHub Pages](https://bossy-ye.github.io/ClaimStab-QC/atlas/)

Advanced secondary entrypoints (not the canonical onboarding path):

- `python -m claimstab.pipelines.claim_stability_app ...`
- `python -m claimstab.pipelines.multidevice_app ...`

## Active Paper Specs

- [paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml](./paper/experiments/specs/evaluation_v2/e1_maxcut_main.yml)
- [paper/experiments/specs/evaluation_v2/e2_ghz_structural.yml](./paper/experiments/specs/evaluation_v2/e2_ghz_structural.yml)
- [paper/experiments/specs/evaluation_v2/e3_bv_decision.yml](./paper/experiments/specs/evaluation_v2/e3_bv_decision.yml)
- [paper/experiments/specs/evaluation_v2/e4_grover_distribution.yml](./paper/experiments/specs/evaluation_v2/e4_grover_distribution.yml)
- [paper/experiments/specs/evaluation_v2/s2_boundary.yml](./paper/experiments/specs/evaluation_v2/s2_boundary.yml)
- [paper/experiments/specs/evaluation_v2/qec_portability.yml](./paper/experiments/specs/evaluation_v2/qec_portability.yml)
- [paper/experiments/specs/paper_distribution.yml](./paper/experiments/specs/paper_distribution.yml)
- [paper/experiments/specs/paper_device.yml](./paper/experiments/specs/paper_device.yml)
- [paper/experiments/specs/paper_boundary.yml](./paper/experiments/specs/paper_boundary.yml)

Community demo spec:
- [examples/community/specs/atlas_bv_demo.yml](./examples/community/specs/atlas_bv_demo.yml)

## Contribute a Dataset (Minimal Flow)

```bash
python -m claimstab.cli validate-spec --spec examples/community/specs/atlas_bv_demo.yml
python -m claimstab.cli run --spec examples/community/specs/atlas_bv_demo.yml --out-dir output/examples/atlas_bv_demo --report
python -m claimstab.cli publish-result --run-dir output/examples/atlas_bv_demo --atlas-root atlas --contributor your_name
python -m claimstab.cli validate-atlas --atlas-root atlas
python -m claimstab.cli export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

## Validation and Development

Run tests:

```bash
./.venv/bin/python -m pytest -q
```

Compatibility check:

```bash
./.venv/bin/python -m claimstab.scripts.check_refactor_compat --mode all
```

Build docs:

```bash
./.venv/bin/python -m mkdocs build --strict
```

## Current Validated Stack

- `qiskit==2.2.3`
- `qiskit-aer==0.17.2`
- `qiskit-ibm-runtime==0.45.1`

## Project Policies and Scope

- Paper scope lock: [paper/PAPER_SCOPE.md](./paper/PAPER_SCOPE.md)
- Contributing: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Compatibility contract: [docs/compatibility_contract.md](./docs/compatibility_contract.md)
