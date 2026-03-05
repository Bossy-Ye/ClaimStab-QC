# ClaimAtlas Dataset

ClaimAtlas is the shared dataset for ClaimStab outcomes.

Direct access:
- [Dataset Registry](dataset_registry.md)
- [GitHub `atlas/index.json`](https://github.com/Bossy-Ye/ClaimStab-QC/blob/main/atlas/index.json)
- [GitHub `atlas/submissions`](https://github.com/Bossy-Ye/ClaimStab-QC/tree/main/atlas/submissions)

Core idea:
- contributors run experiments with their own task and method plugins,
- publish the resulting `claim_stability.json` package,
- aggregate all submissions into a public index for cross-paper analysis.

Submission contract (required for registry-quality entries):
- what claim(s) were tested,
- what perturbation policy was used,
- what decisions/results were obtained,
- how to reproduce and cite the submission.

## Input Contract (Strict)

`claimstab publish-result --run-dir <dir>` expects:
- Required: `<dir>/claim_stability.json`
- Optional: `<dir>/scores.csv`
- Optional: `<dir>/rq_summary.json`
- Optional: `<dir>/stability_report.html`

If `claim_stability.json` is missing, publish will fail.

Minimal spec example (dataset-friendly):

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

## Contributor Flow

1. Run experiment (built-in or custom task):

```bash
claimstab run --spec examples/custom_task_demo/spec_toy.yml --out-dir output/toy --report
```

2. Publish artifacts to dataset:

```bash
claimstab publish-result \
  --run-dir output/toy \
  --atlas-root atlas \
  --contributor your_name
```

3. Validate dataset index + file references:

```bash
claimstab validate-atlas --atlas-root atlas
```

Minimal external-user flow:
```bash
claimstab init-external-task --name my_problem --out-dir examples/my_problem_demo
claimstab run --spec examples/my_problem_demo/spec_my_problem.yml --out-dir output/my_problem --report
claimstab publish-result --run-dir output/my_problem --atlas-root atlas --contributor your_name
```

Regenerate the website dataset page after new submissions:
```bash
claimstab export-dataset-registry --atlas-root atlas --out docs/dataset_registry.md
```

Dataset PR checklist template:
- `.github/PULL_REQUEST_TEMPLATE/dataset_submission.md`

## Stored Artifacts

Each submission directory stores:
- `metadata.json` (task/suite/claim types + provenance)
- `claim_stability.json` (required)
- `scores.csv` (optional)
- `rq_summary.json` (optional)
- `stability_report.html` (optional)

This makes ClaimStab a continuously growing, task-agnostic claim-stability benchmark.

Browse current submissions in the website registry page: [Dataset Registry](dataset_registry.md).
